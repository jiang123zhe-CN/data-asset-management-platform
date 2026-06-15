"""金融合规分类分级引擎 — 矩阵判定 + 就高从严 + 30%阈值检测

实现六部门《金融信息服务数据分类分级指南》§5 的分级判定逻辑。
替代原有关键词匹配方式，改为"影响对象 × 危害程度 → 数据级别"的矩阵判定。
"""

from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.field import Field
from app.models.finance_category import FinanceDataCategory, FinanceGradingRule


# ═══════════════════════════════════════════════════════════════════════════
# 1. 分级判定矩阵（来自指南 §5）
# ═══════════════════════════════════════════════════════════════════════════

# 矩阵: (impact_target, impact_level) → data_level
GRADING_MATRIX = {
    # 国家安全 — 任何危害都是核心或重要
    ("national_security", "extremely_serious"): "core",
    ("national_security", "serious"):          "core",
    ("national_security", "general"):          "important",

    # 经济运行
    ("economy",           "extremely_serious"): "core",
    ("economy",           "serious"):          "important",
    ("economy",           "general"):          "sensitive",

    # 社会秩序
    ("social_order",      "extremely_serious"): "core",
    ("social_order",      "serious"):          "important",
    ("social_order",      "general"):          "sensitive",

    # 公共利益
    ("public_interest",   "extremely_serious"): "core",
    ("public_interest",   "serious"):          "important",
    ("public_interest",   "general"):          "sensitive",

    # 组织权益
    ("org_rights",        "extremely_serious"): "sensitive",
    ("org_rights",        "serious"):          "sensitive",
    ("org_rights",        "general"):          "normal",

    # 个人权益
    ("personal_rights",   "extremely_serious"): "sensitive",
    ("personal_rights",   "serious"):          "sensitive",
    ("personal_rights",   "general"):          "normal",
}

# 影响对象 ← 数据特征映射
IMPACT_SIGNALS = {
    "national_security": {
        "keywords": ["密钥", "证书", "密码", "加密", "国防", "军工", "国家安全",
                     "核心网络", "关键基础设施", "核心系统"],
        "data_types": ["certificate", "encryption_key", "secret"],
    },
    "economy": {
        "keywords": ["利率", "汇率", "准备金", "货币供应", "GDP", "CPI", "PMI",
                     "基准", "清算", "结算", "人民币汇率", "中间价", "金融稳定"],
        "data_types": ["rate", "benchmark_index", "clearing"],
    },
    "social_order": {
        "keywords": ["欺诈", "洗钱", "反恐", "制裁", "黑名单", "恐怖融资"],
        "data_types": ["fraud", "aml"],
    },
    "public_interest": {
        "keywords": ["上市公司", "披露", "重大事项", "股东", "并购", "退市"],
        "data_types": ["market_disclosure"],
    },
    "org_rights": {
        "keywords": ["模型", "策略", "参数", "风控", "评分", "评级", "额度"],
        "data_types": ["model", "risk_param"],
    },
    "personal_rights": {
        "keywords": ["身份证", "手机号", "姓名", "地址", "生物特征", "指纹", "人脸",
                     "声纹", "账户", "卡号", "交易记录", "持仓"],
        "data_types": ["pii", "personal_info", "bio_feature"],
    },
}

# 关键词 → 危害程度升级
HAZARD_UPGRADE = {
    # 大量个人数据 → 升级到严重
    "mass_personal": {"threshold": 100000, "upgrade_to": "serious"},
    # 未公开市场信息 → 升级
    "non_public": {"upgrade_to": "serious"},
    # 系统安全类 → 升级
    "security_critical": {"upgrade_to": "extremely_serious"},
}


class ComplianceEngine:
    """金融合规分类分级引擎。

    使用方式：
        engine = ComplianceEngine(db)
        results = engine.classify_fields(field_ids)       # 批量分类
        report  = engine.check_threshold_changes()        # 30% 阈值检测
    """

    def __init__(self, db: Session):
        self.db = db
        # 按 level 分组加载所有活跃分类
        all_cats = (
            db.query(FinanceDataCategory)
            .filter(FinanceDataCategory.is_active == True)
            .order_by(FinanceDataCategory.level, FinanceDataCategory.sort_order)
            .all()
        )
        self._cat_by_code: dict[str, FinanceDataCategory] = {c.code: c for c in all_cats}
        self._l3_cats = [c for c in all_cats if c.level == 3]  # 67 个叶子分类

    # ═══════════════════════════════════════════════════════════════════════
    # 公开接口
    # ═══════════════════════════════════════════════════════════════════════

    def classify_fields(self, field_ids: list[int] | None = None) -> list[dict]:
        """对指定字段（或全部活跃字段）执行金融合规分类分级。

        Returns: list of {field_id, field_name, finance_category_code,
                          finance_category_name, finance_data_level,
                          ref_min_level, level_upgraded, upgrade_reason,
                          confidence, method}
        """
        if field_ids:
            fields = self.db.query(Field).filter(
                Field.id.in_(field_ids), Field.status == "active"
            ).all()
        else:
            fields = self.db.query(Field).filter(Field.status == "active").all()

        results = []
        for field in fields:
            result = self._classify_one(field)
            # 持久化到 field 记录
            matched_cat = self._cat_by_code.get(result.get("finance_category_code") or "")
            field.finance_category_id = matched_cat.id if matched_cat else None
            field.finance_data_level = result.get("finance_data_level")
            field.tagging_method = "compliance_matrix"
            field.tagging_confidence = result.get("confidence", 0.0)
            field.updated_at = datetime.now(timezone.utc)
            results.append(result)

        self.db.commit()
        return results

    def check_threshold(self) -> dict:
        """30% 变化阈值检测。

        统计 core + important 数据的条目数和存储量，
        与上次报送快照对比，超过 30% 则返回预警。
        """
        core_count = self.db.query(Field).filter(
            Field.finance_data_level == "core", Field.status == "active"
        ).count()
        important_count = self.db.query(Field).filter(
            Field.finance_data_level == "important", Field.status == "active"
        ).count()

        total_critical = core_count + important_count
        # 存储量简化为字段数（实际应结合数据源的总行数×平均字段大小）
        storage_estimate = total_critical

        return {
            "core_records": core_count,
            "important_records": important_count,
            "total_critical": total_critical,
            "storage_estimate": storage_estimate,
            "threshold_30pct": int(total_critical * 0.3),
            "message": (
                "重要数据目录需在变化超30%时重新报送" if total_critical > 0
                else "当前没有标记为核心/重要的数据字段"
            ),
        }

    def get_table_level(self, table_name: str) -> dict:
        """就高从严：计算整表的最高数据级别。"""
        fields = self.db.query(Field).filter(
            Field.table_name == table_name,
            Field.status == "active",
            Field.finance_data_level.isnot(None),
        ).all()

        if not fields:
            return {"table_name": table_name, "table_level": None, "field_count": 0}

        levels = [f.finance_data_level for f in fields if f.finance_data_level]
        LEVEL_ORDER = {"core": 4, "important": 3, "sensitive": 2, "normal": 1}
        max_level = max(levels, key=lambda x: LEVEL_ORDER.get(x, 0))
        max_field = next(f for f in fields if f.finance_data_level == max_level)

        return {
            "table_name": table_name,
            "table_level": max_level,
            "field_count": len(fields),
            "max_field_name": max_field.name,
            "max_field_code": max_field.field_code,
            "principle": "就高从严 — 表级 = MAX(所有字段级别)",
        }

    # ═══════════════════════════════════════════════════════════════════════
    # 私有方法
    # ═══════════════════════════════════════════════════════════════════════

    def _classify_one(self, field: Field) -> dict:
        field_text = self._field_text(field)

        # Step 1: 匹配 67 类三级分类（返回分类和匹配层）
        matched_cat, match_layer = self._match_category(field, field_text)
        cat_code = matched_cat.code if matched_cat else None
        cat_name = matched_cat.name if matched_cat else None
        ref_min = matched_cat.ref_min_level if matched_cat else "normal"

        # Step 2: 按矩阵判定数据级别（传入匹配质量参数）
        graded_level, confidence = self._matrix_grade(
            field, field_text, ref_min,
            cat_matched=matched_cat is not None,
            match_layer=match_layer,
        )

        # Step 3: 检查是否升级（相对参考最低级别）
        LEVEL_ORDER = {"core": 4, "important": 3, "sensitive": 2, "normal": 1}
        upgraded = LEVEL_ORDER.get(graded_level, 0) > LEVEL_ORDER.get(ref_min, 0)
        upgrade_reason = None
        if upgraded:
            upgrade_reason = self._upgrade_reason(field, field_text, ref_min, graded_level)

        return {
            "field_id": field.id,
            "field_name": field.name,
            "finance_category_code": cat_code,
            "finance_category_name": cat_name,
            "finance_data_level": graded_level,
            "ref_min_level": ref_min,
            "level_upgraded": upgraded,
            "upgrade_reason": upgrade_reason,
            "confidence": round(confidence, 2),
            "method": "compliance_matrix",
        }

    def _match_category(self, field: Field, field_text: str) -> tuple[FinanceDataCategory | None, int]:
        """匹配到最合适的三级分类。返回 (分类, 匹配层)。
        匹配层: 1=精确关键词 2=产品信号 3=业务域映射 4=兜底推断 5=遍历评分 0=未匹配
        """
        # ═══ 第1层：字段级精确映射（高频字段一一定向） ═══
        EXACT_MAP: dict[str, str] = {
            # 个人基本信息
            "姓名": "FIN_USER_PERSONAL_BASIC", "客户姓名": "FIN_USER_PERSONAL_BASIC",
            "身份证": "FIN_USER_PERSONAL_BASIC", "证件": "FIN_USER_PERSONAL_BASIC",
            "性别": "FIN_USER_PERSONAL_BASIC", "出生日期": "FIN_USER_PERSONAL_BASIC",
            "手机号": "FIN_USER_PERSONAL_BASIC", "手机": "FIN_USER_PERSONAL_BASIC",
            "电话": "FIN_USER_PERSONAL_BASIC", "邮箱": "FIN_USER_PERSONAL_BASIC",
            "地址": "FIN_USER_PERSONAL_BASIC", "住址": "FIN_USER_PERSONAL_BASIC",
            "银行卡": "FIN_USER_PERSONAL_TXN", "卡号": "FIN_USER_PERSONAL_TXN",
            "职业": "FIN_USER_PERSONAL_BASIC", "工作单位": "FIN_USER_PERSONAL_BASIC",
            "国籍": "FIN_USER_PERSONAL_BASIC", "民族": "FIN_USER_PERSONAL_BASIC",
            # 生物特征
            "指纹": "FIN_USER_PERSONAL_BIO", "人脸": "FIN_USER_PERSONAL_BIO",
            "声纹": "FIN_USER_PERSONAL_BIO", "虹膜": "FIN_USER_PERSONAL_BIO",
            "基因": "FIN_USER_PERSONAL_BIO", "生物特征": "FIN_USER_PERSONAL_BIO",
            "设备指纹": "FIN_USER_PERSONAL_BIO",
            # 系统安全
            # 金融产品
            "股票": "FIN_BIZ_MKT_STOCK", "股价": "FIN_BIZ_MKT_STOCK",
            "基金": "FIN_BIZ_MKT_FUND", "债券": "FIN_BIZ_MKT_BOND",
            "期货": "FIN_BIZ_MKT_FUT", "期权": "FIN_BIZ_MKT_FUT",
            # 系统运维
            "日志": "FIN_ENT_OPS_LOG", "操作日志": "FIN_ENT_OPS_LOG",
            "访问日志": "FIN_ENT_OPS_LOG", "错误日志": "FIN_ENT_OPS_LOG",
            "配置": "FIN_ENT_OPS_CONFIG",
            # 系统安全
            "密钥": "FIN_ENT_OPS_SECURITY", "证书": "FIN_ENT_OPS_SECURITY",
            "密码": "FIN_ENT_OPS_SECURITY", "私钥": "FIN_ENT_OPS_SECURITY",
            "Token": "FIN_ENT_OPS_SECURITY", "加密": "FIN_ENT_OPS_SECURITY",
        }
        for keyword, cat_code in EXACT_MAP.items():
            if keyword in field.name:
                cat = self._cat_by_code.get(cat_code)
                if cat:
                    return cat, 1

        # ═══ 第2层：金融产品信号 ═══
        PRODUCT_SIGNALS: list[tuple[str, list[str]]] = [
            ("stock", ["股票", "Stock", "equity", "股东", "K线", "股本"]),
            ("bond", ["债券", "Bond", "fixed_income", "久期", "凸性"]),
            ("fund", ["基金", "Fund", "净值"]),
            ("forex", ["外汇", "汇率", "FX", "Forex", "中间价"]),
            ("futures_option", ["期货", "期权", "Futures", "Option", "行权"]),
            ("rate", ["利率", "Shibor", "LPR", "互换", "收益率"]),
            ("credit", ["评级", "违约", "PD", "LGD", "信用"]),
            ("money_market", ["拆借", "回购", "存单", "货币市场"]),
        ]
        for product, signals in PRODUCT_SIGNALS:
            for sig in signals:
                if sig in field_text:
                    for cat in self._l3_cats:
                        if cat.finance_product == product:
                            return cat, 2

        # ═══ 第3层：业务域映射 ═══
        if field.business_domain:
            DOMAIN_MAP = {
                "风控": "FIN_ENT_MGMT_RISK", "风险": "FIN_ENT_MGMT_RISK",
                "财务": "FIN_ENT_MGMT_FIN",
                "人力": "FIN_ENT_MGMT_HR",
                "交易": "FIN_USER_PERSONAL_TXN", "支付": "FIN_USER_PERSONAL_TXN",
                "客户": "FIN_USER_PERSONAL_BASIC",
                "系统": "FIN_ENT_OPS_CONFIG", "安全": "FIN_ENT_OPS_SECURITY",
            }
            for domain_kw, cat_code in DOMAIN_MAP.items():
                if domain_kw in (field.business_domain or ""):
                    cat = self._cat_by_code.get(cat_code)
                    if cat:
                        return cat, 3

        # ═══ 第4层：兜底推断（业务域 + 表名 + 数据类型） ═══
        text_lower = field_text.lower()
        # 数据运维类
        if any(kw in text_lower for kw in ['日志', 'log', '配置', 'config', '审计', 'audit']):
            cat = self._cat_by_code.get('FIN_ENT_OPS_LOG')
            if cat: return cat, 4
        # 个人身份类
        if any(kw in text_lower for kw in ['客户', '用户', 'user', 'customer', '姓名', 'name', '手机', 'phone', '邮箱', 'email']):
            cat = self._cat_by_code.get('FIN_USER_PERSONAL_BASIC')
            if cat: return cat, 4
        # 交易/金额类
        if any(kw in text_lower for kw in ['交易', 'transaction', '订单', 'order', '金额', 'amount', '支付', 'payment', '流水']):
            cat = self._cat_by_code.get('FIN_USER_PERSONAL_TXN')
            if cat: return cat, 4
        # 风控/模型类
        if any(kw in text_lower for kw in ['风控', 'risk', '模型', 'model', '策略', '评分', '预警', '黑名单']):
            cat = self._cat_by_code.get('FIN_ENT_MGMT_RISK')
            if cat: return cat, 4
        # 金融产品类
        if any(kw in text_lower for kw in ['股票', 'stock', '债券', 'bond', '基金', 'fund', '期货', '利率', 'rate']):
            cat = self._cat_by_code.get('FIN_BIZ_MKT_STOCK')
            if cat: return cat, 4

        # ═══ 第5层：遍历评分（最终兜底） ═══
        best, best_score = None, 0.0
        for cat in self._l3_cats:
            score = 0.0
            if cat.name in field.name or field.name in cat.name:
                score += 0.6
            if cat.appendix_desc:
                for i in range(len(field.name) - 1):
                    chunk = field.name[i:i+2]
                    if chunk in (cat.appendix_desc or ""):
                        score += 0.1
            if field.table_name and cat.name in field.table_name:
                score += 0.3
            if score > best_score:
                best_score = score
                best = cat

        return (best, 5) if best_score >= 0.2 else (None, 0)

    def _matrix_grade(self, field: Field, field_text: str, ref_min: str,
                       cat_matched: bool = False, match_layer: int = 0) -> tuple[str, float]:
        """按影响对象×危害程度矩阵判定数据级别。"""
        LEVEL_ORDER = {"core": 4, "important": 3, "sensitive": 2, "normal": 1}

        # ① 确定影响对象
        impact_targets = self._detect_impact_targets(field, field_text)

        # ② 确定危害程度
        impact_level = self._detect_impact_level(field, field_text)

        # ③ 查矩阵
        graded = ref_min
        matrix_upgraded = False
        for target in impact_targets:
            key = (target, impact_level)
            matrix_level = GRADING_MATRIX.get(key)
            if matrix_level and LEVEL_ORDER.get(matrix_level, 0) > LEVEL_ORDER.get(graded, 0):
                graded = matrix_level
                matrix_upgraded = True

        # ④ 就高从严
        table_max = self._get_table_max_level(field.table_name, exclude_field_id=field.id)
        table_upgraded = False
        if LEVEL_ORDER.get(table_max, 0) > LEVEL_ORDER.get(graded, 0):
            graded = table_max
            table_upgraded = True

        # ⑤ 动态置信度：基于匹配质量
        base = 0.60  # 底线：至少跑了矩阵
        if cat_matched:
            base += 0.10  # 分类命中 +10%
        if match_layer == 1:
            base += 0.20  # 精确关键词匹配 +20%
        elif match_layer == 2:
            base += 0.15  # 产品信号 +15%
        elif match_layer == 3:
            base += 0.10  # 业务域映射 +10%
        if impact_targets and impact_targets != ["org_rights"]:
            base += 0.05  # 命中了非默认影响对象 +5%
        if matrix_upgraded:
            base += 0.05  # 矩阵升级 +5%
        if table_upgraded:
            base += 0.05  # 就高从严升级 +5%

        confidence = min(base, 0.99)
        return graded, confidence

    def _detect_impact_targets(self, field: Field, field_text: str) -> list[str]:
        """检测字段涉及的影响对象。"""
        targets = []
        field_text_lower = field_text.lower()
        for target, signals in IMPACT_SIGNALS.items():
            for kw in signals["keywords"]:
                if kw in field_text or kw.lower() in field_text_lower:
                    targets.append(target)
                    break
        if not targets:
            targets.append("org_rights")  # 默认：组织权益
        return targets

    def _detect_impact_level(self, field: Field, field_text: str) -> str:
        """检测危害程度。"""
        # 系统安全类 → extremely_serious
        security_keywords = ["密钥", "证书", "私钥", "Token", "核心系统", "密码"]
        for kw in security_keywords:
            if kw in field_text:
                return "extremely_serious"

        # 大量个人数据 → serious
        if field.data_type and "BLOB" in field.data_type.upper():
            return "serious"

        # 模型/策略参数 → serious
        model_keywords = ["模型参数", "权重", "策略", "算法"]
        for kw in model_keywords:
            if kw in field_text:
                return "serious"

        # 敏感个人信息 → serious
        sensitive_pii = ["生物特征", "指纹", "人脸", "声纹", "基因"]
        for kw in sensitive_pii:
            if kw in field_text:
                return "serious"

        # 默认：一般
        return "general"

    def _upgrade_reason(self, field: Field, field_text: str,
                        ref_min: str, graded: str) -> str:
        """解释升级原因。"""
        impact_targets = self._detect_impact_targets(field, field_text)
        impact_level = self._detect_impact_level(field, field_text)
        return (
            f"参考最低级别为 {ref_min}，因涉及影响对象 {impact_targets}，"
            f"危害程度判定为 {impact_level}，按矩阵升级至 {graded}"
        )

    def _get_table_max_level(self, table_name: str, exclude_field_id: int | None = None) -> str | None:
        """获取同表其他字段的最高金融数据级别（就高从严原则）。"""
        q = self.db.query(Field).filter(
            Field.table_name == table_name,
            Field.status == "active",
            Field.finance_data_level.isnot(None),
        )
        if exclude_field_id:
            q = q.filter(Field.id != exclude_field_id)
        fields = q.all()

        if not fields:
            return None
        LEVEL_ORDER = {"core": 4, "important": 3, "sensitive": 2, "normal": 1}
        return max(fields, key=lambda f: LEVEL_ORDER.get(f.finance_data_level or "normal", 0)).finance_data_level

    @staticmethod
    def _field_text(field: Field) -> str:
        parts = [
            field.name or "",
            field.english_name or "",
            field.description or "",
            field.business_rules or "",
            field.table_name or "",
            field.business_domain or "",
        ]
        return " ".join(parts)
