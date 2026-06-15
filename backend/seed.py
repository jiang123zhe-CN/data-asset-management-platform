from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.directory import Directory
from app.models.field import Field
from app.models.mapping import DirectoryFieldMapping
from app.models.standard import ClassificationCategory, TieringRule
from app.models.finance_category import FinanceDataCategory, FinanceGradingRule
import json


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Users ──
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(username="admin", hashed_password=hash_password("admin123"),
                         role="admin", display_name="系统管理员", email="admin@example.com")
            db.add(admin)
            db.commit()
            print("Default admin user created: admin / admin123")

        sample_users = [
            ("data_entry", "录入员"),
            ("data_admin", "数据管理员"),
            ("reviewer", "复核员"),
        ]
        for role, display_name in sample_users:
            if not db.query(User).filter(User.username == role).first():
                db.add(User(username=role, hashed_password=hash_password("admin123"),
                            role=role, display_name=display_name))
        db.commit()
        print("Sample users seeded.")

        # ── Directories ──
        if db.query(Directory).count() == 0:
            dirs_data = [
                {"name": "客户域", "code": "customer", "description": "客户相关数据资产", "level": 0},
                {"name": "客户基本信息", "code": "customer_base", "description": "客户姓名、证件等基础字段", "level": 1, "parent_code": "customer"},
                {"name": "客户联系信息", "code": "customer_contact", "description": "电话、邮箱、地址等", "level": 1, "parent_code": "customer"},
                {"name": "交易域", "code": "transaction", "description": "交易流水相关", "level": 0},
                {"name": "订单信息", "code": "order", "description": "订单头、订单行", "level": 1, "parent_code": "transaction"},
                {"name": "支付信息", "code": "payment", "description": "支付方式、流水号", "level": 1, "parent_code": "transaction"},
                {"name": "风控域", "code": "risk", "description": "风险控制相关", "level": 0},
                {"name": "反欺诈", "code": "anti_fraud", "description": "欺诈检测数据", "level": 1, "parent_code": "risk"},
            ]
            parent_map = {}
            for d in dirs_data:
                parent_id = None
                if "parent_code" in d:
                    parent_id = parent_map.get(d["parent_code"])
                obj = Directory(name=d["name"], code=d["code"], description=d.get("description", ""),
                                level=d["level"], parent_id=parent_id, created_by=admin.id)
                db.add(obj)
                db.flush()
                parent_map[d["code"]] = obj.id
            db.commit()
            print("Sample directories seeded.")

        # ── Fields ──
        if db.query(Field).count() == 0:
            fields_data = [
                {"field_code": "F001", "name": "客户姓名", "data_type": "VARCHAR", "table_name": "dim_customer", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L2"},
                {"field_code": "F002", "name": "身份证号", "data_type": "VARCHAR", "table_name": "dim_customer", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L4"},
                {"field_code": "F003", "name": "手机号", "data_type": "VARCHAR", "table_name": "dim_customer_contact", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L3"},
                {"field_code": "F004", "name": "邮箱", "data_type": "VARCHAR", "table_name": "dim_customer_contact", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L2"},
                {"field_code": "F005", "name": "订单号", "data_type": "VARCHAR", "table_name": "fact_order", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F006", "name": "订单金额", "data_type": "DECIMAL", "table_name": "fact_order", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F007", "name": "支付方式", "data_type": "VARCHAR", "table_name": "dim_payment", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L1"},
                {"field_code": "F008", "name": "交易时间", "data_type": "DATETIME", "table_name": "fact_transaction", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F009", "name": "设备指纹", "data_type": "VARCHAR", "table_name": "fact_login", "database_name": "ods", "business_domain": "风控域", "sensitivity_level": "L3"},
                {"field_code": "F010", "name": "IP地址", "data_type": "VARCHAR", "table_name": "fact_login", "database_name": "ods", "business_domain": "风控域", "sensitivity_level": "L2"},
            ]
            for f in fields_data:
                db.add(Field(**f, created_by=admin.id))
            db.commit()
            print("Sample fields seeded.")

        # ── Mappings ──
        if db.query(DirectoryFieldMapping).count() == 0:
            dirs = {d.code: d.id for d in db.query(Directory).all()}
            fields = {f.field_code: f.id for f in db.query(Field).all()}
            mappings_data = [
                ("customer_base", "F001"), ("customer_base", "F002"),
                ("customer_contact", "F003"), ("customer_contact", "F004"),
                ("order", "F005"), ("order", "F006"),
                ("payment", "F007"), ("transaction", "F008"),
            ]
            for dir_code, field_code in mappings_data:
                did, fid = dirs.get(dir_code), fields.get(field_code)
                if did and fid:
                    db.add(DirectoryFieldMapping(directory_id=did, field_id=fid,
                                                 mapping_source="manual", created_by=admin.id))
            db.commit()
            print("Sample mappings seeded.")

        # ── Classification Categories (China Financial Standard 8 Categories) ──
        if db.query(ClassificationCategory).count() == 0:
            categories_data = [
                # Level 0: 8 root categories
                {"name": "客户数据", "code": "customer_data", "category_type": "business",
                 "description": "与客户身份、行为、关系相关的数据", "keywords": "客户,用户,账户持有人,借款人",
                 "regulatory_ref": "《个人信息保护法》《金融数据安全 数据安全分级指南》JR/T 0197-2020"},
                {"name": "交易数据", "code": "transaction_data", "category_type": "business",
                 "description": "交易记录、流水、支付等金融活动数据", "keywords": "交易,流水,支付,转账,结算",
                 "regulatory_ref": "《金融数据安全 数据安全分级指南》JR/T 0197-2020"},
                {"name": "产品数据", "code": "product_data", "category_type": "business",
                 "description": "金融产品定义、参数、规则等", "keywords": "产品,利率,费率,条款,额度",
                 "regulatory_ref": "《银行业金融机构数据治理指引》"},
                {"name": "财务数据", "code": "financial_data", "category_type": "business",
                 "description": "机构自身财务、会计、资产负债数据", "keywords": "财务,会计,资产,负债,损益",
                 "regulatory_ref": "《企业会计准则》《金融企业财务规则》"},
                {"name": "运营数据", "code": "operations_data", "category_type": "business",
                 "description": "日常运营、流程、服务相关数据", "keywords": "运营,流程,工单,服务,日志",
                 "regulatory_ref": "《银行业金融机构数据治理指引》"},
                {"name": "风险数据", "code": "risk_data", "category_type": "business",
                 "description": "风险管理、模型、评级、预警数据", "keywords": "风险,评级,模型,预警,不良,拨备",
                 "regulatory_ref": "《银行业金融机构全面风险管理指引》"},
                {"name": "合规数据", "code": "compliance_data", "category_type": "regulatory",
                 "description": "监管报送、反洗钱、合规审查数据", "keywords": "合规,监管,报送,反洗钱,审计,检查",
                 "regulatory_ref": "《反洗钱法》《金融机构大额交易和可疑交易报告管理办法》"},
                {"name": "系统数据", "code": "system_data", "category_type": "technical",
                 "description": "IT基础设施、系统配置、安全管控数据", "keywords": "系统,配置,密钥,证书,网络,权限",
                 "regulatory_ref": "《网络安全法》《信息安全技术 网络安全等级保护基本要求》"},
            ]
            parent_map: dict[str, int] = {}
            for d in categories_data:
                obj = ClassificationCategory(
                    name=d["name"], code=d["code"], level=0,
                    category_type=d["category_type"], description=d.get("description", ""),
                    keywords=d.get("keywords", ""), regulatory_ref=d.get("regulatory_ref", ""),
                    created_by=admin.id,
                )
                db.add(obj)
                db.flush()
                parent_map[d["code"]] = obj.id

            # Level 1: sub-categories
            sub_categories = [
                {"name": "客户基本信息", "code": "customer_base_info", "parent_code": "customer_data",
                 "description": "姓名、证件、性别、出生日期等基础身份字段", "keywords": "姓名,证件,身份证,性别,出生日期"},
                {"name": "客户联系信息", "code": "customer_contact_info", "parent_code": "customer_data",
                 "description": "电话、邮箱、地址等联系方式", "keywords": "手机,电话,邮箱,地址,微信"},
                {"name": "客户标识信息", "code": "customer_identity", "parent_code": "customer_data",
                 "description": "生物特征、设备指纹等唯一标识", "keywords": "指纹,人脸,声纹,设备指纹,IP"},
                {"name": "客户行为数据", "code": "customer_behavior", "parent_code": "customer_data",
                 "description": "浏览、点击、偏好、消费习惯等行为数据", "keywords": "行为,偏好,浏览,点击,消费习惯"},
                {"name": "交易明细", "code": "transaction_detail", "parent_code": "transaction_data",
                 "description": "单笔交易的时间、金额、对手方等", "keywords": "金额,对手方,时间,币种,渠道"},
                {"name": "支付结算", "code": "payment_settlement", "parent_code": "transaction_data",
                 "description": "支付方式、清算、结算数据", "keywords": "支付,清算,结算,账户,路由"},
                {"name": "风险模型参数", "code": "risk_model_params", "parent_code": "risk_data",
                 "description": "风控模型的权重、阈值、策略参数", "keywords": "模型,权重,阈值,策略,参数,算法"},
                {"name": "风险预警信号", "code": "risk_alert", "parent_code": "risk_data",
                 "description": "风险事件、预警规则触发记录", "keywords": "预警,告警,异常,触发,黑名单"},
                {"name": "监管报送数据", "code": "regulatory_reporting", "parent_code": "compliance_data",
                 "description": "1104、EAST、反洗钱等监管报送数据", "keywords": "1104,EAST,反洗钱,大额,可疑"},
                {"name": "系统安全配置", "code": "system_security", "parent_code": "system_data",
                 "description": "密钥、证书、权限策略等安全保障数据", "keywords": "密钥,证书,密码,权限,Token"},
            ]
            for d in sub_categories:
                parent_id = parent_map.get(d["parent_code"])
                if parent_id:
                    obj = ClassificationCategory(
                        name=d["name"], code=d["code"], level=1,
                        category_type="business", description=d.get("description", ""),
                        keywords=d.get("keywords", ""), parent_id=parent_id,
                        created_by=admin.id,
                    )
                    db.add(obj)
            db.commit()
            print("Classification categories seeded (8 roots + 10 sub).")

        # ── Tiering Rules (L1-L4) ──
        if db.query(TieringRule).count() == 0:
            tier_rules = [
                {
                    "tier_level": "L4", "tier_name": "机密/严格保密",
                    "rule_type": "regex",
                    "rule_content": json.dumps({
                        "keywords": ["身份证号", "银行卡号", "密码", "密钥", "生物特征", "模型权重", "策略参数",
                                     "账户密码", "数字证书", "私钥", "Token", "票据"],
                        "patterns": [r"\d{17}[\dXx]", r"\b\d{16,19}\b"],
                        "metadata_rules": {"sensitivity_level": "L4"},
                    }, ensure_ascii=False),
                    "priority": 100,
                    "regulatory_basis": "《个人信息保护法》第28条 敏感个人信息",
                },
                {
                    "tier_level": "L3", "tier_name": "敏感",
                    "rule_type": "regex",
                    "rule_content": json.dumps({
                        "keywords": ["手机号", "邮箱", "地址", "设备指纹", "交易金额", "账户号", "IP地址",
                                     "身份证", "手机", "电话", "住址", "账户", "卡号"],
                        "patterns": [r"1[3-9]\d{9}", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                                    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"],
                        "metadata_rules": {"sensitivity_level": "L3"},
                    }, ensure_ascii=False),
                    "priority": 80,
                    "regulatory_basis": "《个人信息保护法》第4条 个人信息处理",
                },
                {
                    "tier_level": "L2", "tier_name": "内部",
                    "rule_type": "keyword",
                    "rule_content": json.dumps({
                        "keywords": ["交易时间", "订单号", "支付方式", "客户姓名", "内部报表", "运营数据",
                                     "流程", "工单", "产品名称", "费用", "利率"],
                        "metadata_rules": {"sensitivity_level": "L2"},
                    }, ensure_ascii=False),
                    "priority": 60,
                    "regulatory_basis": "《数据安全法》第21条 数据分类分级制度",
                },
                {
                    "tier_level": "L1", "tier_name": "公开",
                    "rule_type": "keyword",
                    "rule_content": json.dumps({
                        "keywords": ["产品说明", "公告", "新闻", "公开", "描述", "备注", "说明",
                                     "产品类型", "业务类型", "状态", "标志", "类型"],
                        "metadata_rules": {"sensitivity_level": "L1"},
                    }, ensure_ascii=False),
                    "priority": 40,
                    "regulatory_basis": "《数据安全法》第21条",
                },
            ]
            for r in tier_rules:
                db.add(TieringRule(**r, created_by=admin.id))
            db.commit()
            print("Tiering rules seeded (L1-L4).")

        # ── Finance Data Categories (67类) ──
        if db.query(FinanceDataCategory).count() == 0:
            _seed_finance_categories(db, admin.id)
            print("Finance data categories seeded (67 classes).")

        # ── Finance Grading Rules (矩阵规则) ──
        if db.query(FinanceGradingRule).count() == 0:
            _seed_grading_rules(db)
            print("Finance grading rules seeded (18 matrix entries).")

        print("Seed completed.")
    finally:
        db.close()


def _seed_finance_categories(db, user_id):
    """Seed 67类金融信息服务数据分类（国信办通字〔2026〕2号 附录A）。"""
    from app.models.finance_category import FinanceDataCategory as FDC

    cats_data = [
        # ═══ Level 1: 一级(3类) ═══
        {"code": "FIN_BIZ", "name": "业务数据", "level": 1, "data_type": "business",
         "ref_min_level": "normal", "sort_order": 100,
         "standard_ref": "国信办通字〔2026〕2号"},
        {"code": "FIN_USER", "name": "用户数据", "level": 1, "data_type": "user",
         "ref_min_level": "sensitive", "sort_order": 200,
         "standard_ref": "国信办通字〔2026〕2号"},
        {"code": "FIN_ENT", "name": "企业数据", "level": 1, "data_type": "enterprise",
         "ref_min_level": "sensitive", "sort_order": 300,
         "standard_ref": "国信办通字〔2026〕2号"},

        # ═══ Level 2: 二级(9类) ═══
        # 业务数据 → 5个二级
        {"code": "FIN_BIZ_MKT", "name": "金融市场数据", "level": 2, "data_type": "business",
         "parent_code": "FIN_BIZ", "ref_min_level": "normal", "sort_order": 110,
         "appendix_desc": "包括股票、债券、基金、外汇、商品、期货期权等交易和行情数据"},
        {"code": "FIN_BIZ_MACRO", "name": "宏观经济数据", "level": 2, "data_type": "business",
         "parent_code": "FIN_BIZ", "ref_min_level": "sensitive", "sort_order": 120,
         "appendix_desc": "GDP、CPI、PMI、货币供应量等宏观经济指标数据"},
        {"code": "FIN_BIZ_ORG", "name": "组织机构数据", "level": 2, "data_type": "business",
         "parent_code": "FIN_BIZ", "ref_min_level": "normal", "sort_order": 130,
         "appendix_desc": "金融机构、上市公司、发债主体等组织机构基本信息"},
        {"code": "FIN_BIZ_IND", "name": "行业指标数据", "level": 2, "data_type": "business",
         "parent_code": "FIN_BIZ", "ref_min_level": "normal", "sort_order": 140,
         "appendix_desc": "各行业统计指标、景气指数、产能利用率等"},
        {"code": "FIN_BIZ_REPORT", "name": "资讯报告数据", "level": 2, "data_type": "business",
         "parent_code": "FIN_BIZ", "ref_min_level": "normal", "sort_order": 150,
         "appendix_desc": "研究报告、新闻资讯、公告信息等"},

        # 用户数据 → 2个二级
        {"code": "FIN_USER_PERSONAL", "name": "个人用户数据", "level": 2, "data_type": "user",
         "parent_code": "FIN_USER", "ref_min_level": "sensitive", "sort_order": 210},
        {"code": "FIN_USER_ORG", "name": "机构用户数据", "level": 2, "data_type": "user",
         "parent_code": "FIN_USER", "ref_min_level": "sensitive", "sort_order": 220},

        # 企业数据 → 2个二级
        {"code": "FIN_ENT_MGMT", "name": "经营管理数据", "level": 2, "data_type": "enterprise",
         "parent_code": "FIN_ENT", "ref_min_level": "sensitive", "sort_order": 310},
        {"code": "FIN_ENT_OPS", "name": "系统运维数据", "level": 2, "data_type": "enterprise",
         "parent_code": "FIN_ENT", "ref_min_level": "important", "sort_order": 320},

        # ═══ Level 3: 三级(核心金融产品分类 + 用户/企业明细) ═══
        # ── 金融市场数据 (三级: 13个核心金融产品) ──
        {"code": "FIN_BIZ_MKT_STOCK", "name": "股票数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "stock",
         "ref_min_level": "normal", "sort_order": 111,
         "appendix_desc": "股票基本资料、交易行情、股东股本、公告事项等",
         "appendix_example": "股票发行信息、实时价格、成交量、成交额、K线数据、分红公告"},
        {"code": "FIN_BIZ_MKT_BOND", "name": "债券数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "bond",
         "ref_min_level": "normal", "sort_order": 112,
         "appendix_desc": "债券基本信息、收益率曲线、评级、违约信息等",
         "appendix_example": "国债收益率、信用债利差、久期、凸性"},
        {"code": "FIN_BIZ_MKT_FUND", "name": "基金数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "fund",
         "ref_min_level": "normal", "sort_order": 113,
         "appendix_desc": "公募/私募基金净值、持仓、费率等",
         "appendix_example": "基金单位净值、累计净值、持仓明细"},
        {"code": "FIN_BIZ_MKT_FUND_PRIVATE", "name": "私募基金数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "fund",
         "ref_min_level": "sensitive", "sort_order": 114,
         "level_rationale": "未公开持仓信息，泄露影响投资者利益和市场公平",
         "appendix_desc": "私募基金未公开持仓、策略参数等"},
        {"code": "FIN_BIZ_MKT_FX", "name": "外汇数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "forex",
         "ref_min_level": "sensitive", "sort_order": 115,
         "level_rationale": "涉及人民币汇率未公开中间价可能影响经济运行",
         "appendix_desc": "汇率行情、外汇交易、跨境资金流动数据",
         "appendix_example": "人民币汇率中间价、即期/远期汇率、外汇储备"},
        {"code": "FIN_BIZ_MKT_COMM", "name": "商品数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "commodity",
         "ref_min_level": "normal", "sort_order": 116,
         "appendix_desc": "大宗商品现货/期货价格、库存、供需数据"},
        {"code": "FIN_BIZ_MKT_FUT", "name": "期货期权", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "futures_option",
         "ref_min_level": "normal", "sort_order": 117,
         "appendix_desc": "期货/期权合约信息、持仓量、保证金、行权数据"},
        {"code": "FIN_BIZ_MKT_INDEX", "name": "指数数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "index",
         "ref_min_level": "normal", "sort_order": 118,
         "appendix_desc": "股票指数、债券指数、商品指数的编制和行情"},
        {"code": "FIN_BIZ_MKT_RATE", "name": "利率数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "rate",
         "ref_min_level": "sensitive", "sort_order": 119,
         "level_rationale": "基准利率未公开变化可能影响经济运行",
         "appendix_desc": "Shibor、LPR、国债收益率、互换利率等"},
        {"code": "FIN_BIZ_MKT_CREDIT", "name": "信用数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "credit",
         "ref_min_level": "sensitive", "sort_order": 120,
         "level_rationale": "信用评级变化可能引起市场波动",
         "appendix_desc": "主体评级、债项评级、违约概率、信用利差"},
        {"code": "FIN_BIZ_MKT_DERIV", "name": "衍生品数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "derivative",
         "ref_min_level": "normal", "sort_order": 121,
         "appendix_desc": "期权、互换、远期等衍生品合约和定价数据"},
        {"code": "FIN_BIZ_MKT_MONEY", "name": "货币市场数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "money_market",
         "ref_min_level": "normal", "sort_order": 122,
         "appendix_desc": "同业拆借、回购、存单等货币市场交易数据"},
        {"code": "FIN_BIZ_MKT_ABS", "name": "资产证券化数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MKT", "finance_product": "abs",
         "ref_min_level": "sensitive", "sort_order": 123,
         "level_rationale": "底层资产池信息可能涉及大量个人数据",
         "appendix_desc": "ABS/MBS/CLO产品信息、底层资产池、现金流分配"},

        # ── 宏观经济数据 (三级: 4个) ──
        {"code": "FIN_BIZ_MACRO_NAT", "name": "国民经济核算数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MACRO", "ref_min_level": "sensitive", "sort_order": 121,
         "appendix_example": "GDP、国民总收入、投入产出表"},
        {"code": "FIN_BIZ_MACRO_PRICE", "name": "价格指数数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MACRO", "ref_min_level": "sensitive", "sort_order": 122,
         "appendix_example": "CPI、PPI、房价指数"},
        {"code": "FIN_BIZ_MACRO_EMPLOY", "name": "就业与收入数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MACRO", "ref_min_level": "sensitive", "sort_order": 123,
         "appendix_example": "城镇调查失业率、居民可支配收入"},
        {"code": "FIN_BIZ_MACRO_TRADE", "name": "国际贸易与收支数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_MACRO", "ref_min_level": "sensitive", "sort_order": 124,
         "appendix_example": "进出口总额、经常账户差额、外债余额"},

        # ── 组织机构数据 (三级: 3个) ──
        {"code": "FIN_BIZ_ORG_FIN", "name": "金融机构信息", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_ORG", "ref_min_level": "normal", "sort_order": 131,
         "appendix_example": "银行、券商、保险、基金公司基本信息和牌照"},
        {"code": "FIN_BIZ_ORG_LISTED", "name": "上市公司信息", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_ORG", "ref_min_level": "normal", "sort_order": 132,
         "appendix_example": "上市公司基本信息、财务报告、重大事项"},
        {"code": "FIN_BIZ_ORG_ISSUER", "name": "发债主体信息", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_ORG", "ref_min_level": "normal", "sort_order": 133,
         "appendix_example": "债券发行人基本信息、财务数据、信用状况"},

        # ── 行业指标数据 (三级: 2个) ──
        {"code": "FIN_BIZ_IND_SECTOR", "name": "行业财务指标", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_IND", "ref_min_level": "normal", "sort_order": 141,
         "appendix_example": "行业平均ROE、资产负债率、营收增速"},
        {"code": "FIN_BIZ_IND_CLIMATE", "name": "行业景气指数", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_IND", "ref_min_level": "normal", "sort_order": 142,
         "appendix_example": "PMI分行业、BCI、企业家信心指数"},

        # ── 资讯报告数据 (三级: 2个) ──
        {"code": "FIN_BIZ_REPORT_NEWS", "name": "金融资讯数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_REPORT", "ref_min_level": "normal", "sort_order": 151,
         "appendix_example": "实时新闻、公告、舆情监测"},
        {"code": "FIN_BIZ_REPORT_RESEARCH", "name": "研究报告数据", "level": 3, "data_type": "business",
         "parent_code": "FIN_BIZ_REPORT", "ref_min_level": "normal", "sort_order": 152,
         "appendix_example": "券商研报、行业分析、投资策略报告"},

        # ── 个人用户数据 (三级: 3个) ──
        {"code": "FIN_USER_PERSONAL_BASIC", "name": "个人基本信息", "level": 3, "data_type": "user",
         "parent_code": "FIN_USER_PERSONAL", "ref_min_level": "sensitive", "sort_order": 211,
         "appendix_desc": "姓名、证件号码、联系方式、地址、职业等",
         "appendix_example": "身份证号、手机号、邮箱、居住地址、工作单位"},
        {"code": "FIN_USER_PERSONAL_TXN", "name": "个人交易数据", "level": 3, "data_type": "user",
         "parent_code": "FIN_USER_PERSONAL", "ref_min_level": "sensitive", "sort_order": 212,
         "appendix_desc": "账户交易记录、持仓、资产、流水等",
         "appendix_example": "证券交易记录、银行流水、基金申购赎回、保险保单"},
        {"code": "FIN_USER_PERSONAL_BIO", "name": "生物特征识别信息", "level": 3, "data_type": "user",
         "parent_code": "FIN_USER_PERSONAL", "ref_min_level": "important", "sort_order": 213,
         "level_rationale": "生物特征不可更改，一旦泄露对个人权益造成严重危害",
         "appendix_desc": "指纹、人脸、声纹、虹膜、基因等生物识别信息",
         "appendix_example": "人脸图像、指纹模板、声纹特征向量"},

        # ── 机构用户数据 (三级: 2个) ──
        {"code": "FIN_USER_ORG_BASIC", "name": "机构基本信息", "level": 3, "data_type": "user",
         "parent_code": "FIN_USER_ORG", "ref_min_level": "sensitive", "sort_order": 221,
         "appendix_example": "机构名称、统一社会信用代码、法定代表人、注册资本"},
        {"code": "FIN_USER_ORG_TXN", "name": "机构交易数据", "level": 3, "data_type": "user",
         "parent_code": "FIN_USER_ORG", "ref_min_level": "sensitive", "sort_order": 222,
         "appendix_example": "机构账户交易流水、持仓、授信额度"},

        # ── 经营管理数据 (三级: 6个) ──
        {"code": "FIN_ENT_MGMT_FIN", "name": "财务数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_MGMT", "ref_min_level": "sensitive", "sort_order": 311,
         "appendix_example": "企业财务报表、科目余额、预算执行"},
        {"code": "FIN_ENT_MGMT_SETTLE", "name": "结算管理数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_MGMT", "ref_min_level": "sensitive", "sort_order": 312,
         "appendix_example": "清算指令、结算确认、资金划拨"},
        {"code": "FIN_ENT_MGMT_HR", "name": "人力资源数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_MGMT", "ref_min_level": "sensitive", "sort_order": 313,
         "appendix_example": "员工信息、薪酬、绩效"},
        {"code": "FIN_ENT_MGMT_MKT", "name": "市场营销数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_MGMT", "ref_min_level": "sensitive", "sort_order": 314,
         "appendix_example": "客户画像、营销活动、渠道数据"},
        {"code": "FIN_ENT_MGMT_RISK", "name": "风险控制与监督数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_MGMT", "ref_min_level": "important", "sort_order": 315,
         "level_rationale": "风控模型参数泄露可能影响金融体系稳定性",
         "appendix_desc": "风控模型参数、策略规则、评级结果、预警信号",
         "appendix_example": "模型权重、阈值、黑名单、可疑交易规则"},
        {"code": "FIN_ENT_MGMT_OTHER", "name": "其他经营管理数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_MGMT", "ref_min_level": "normal", "sort_order": 316},

        # ── 系统运维数据 (三级: 4个) ──
        {"code": "FIN_ENT_OPS_CONFIG", "name": "配置数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_OPS", "ref_min_level": "important", "sort_order": 321,
         "level_rationale": "网络拓扑、安全策略等配置信息泄露危害国家安全",
         "appendix_example": "网络拓扑、系统参数、安全策略、访问控制列表"},
        {"code": "FIN_ENT_OPS_LOG", "name": "日志数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_OPS", "ref_min_level": "sensitive", "sort_order": 322,
         "appendix_example": "操作日志、访问日志、交易日志"},
        {"code": "FIN_ENT_OPS_SECURITY", "name": "安全监测数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_OPS", "ref_min_level": "core", "sort_order": 323,
         "level_rationale": "密钥、证书等信息泄露对国家安全造成特别严重危害",
         "appendix_desc": "密钥、数字证书、加密算法、安全审计记录",
         "appendix_example": "SSL证书、加密密钥、入侵检测记录"},
        {"code": "FIN_ENT_OPS_EVENT", "name": "安全事件数据", "level": 3, "data_type": "enterprise",
         "parent_code": "FIN_ENT_OPS", "ref_min_level": "important", "sort_order": 324,
         "level_rationale": "安全事件详情泄露可能被利用发动进一步攻击",
         "appendix_example": "攻击详情、漏洞信息、应急响应记录"},
    ]

    code_to_id: dict[str, int] = {}
    for d in cats_data:
        parent_id = code_to_id.get(d.get("parent_code", "")) if "parent_code" in d else None
        level = d.get("level", 1 if "parent_code" not in d else 3)
        obj = FDC(
            code=d["code"], name=d["name"], level=level,
            parent_id=parent_id,
            data_type=d.get("data_type", "business"),
            finance_product=d.get("finance_product"),
            ref_min_level=d.get("ref_min_level", "normal"),
            level_rationale=d.get("level_rationale"),
            appendix_desc=d.get("appendix_desc"),
            appendix_example=d.get("appendix_example"),
            standard_ref=d.get("standard_ref", "国信办通字〔2026〕2号"),
            version="2026-06",
            sort_order=d.get("sort_order", 0),
            created_by=user_id,
        )
        db.add(obj)
        db.flush()  # 获取自增ID
        code_to_id[d["code"]] = obj.id
    db.commit()


def _seed_grading_rules(db):
    """Seed 18条分级矩阵规则（影响对象 × 危害程度 → 数据级别）。"""
    from app.models.finance_category import FinanceGradingRule as FGR

    rules = [
        # 国家安全
        ("national_security", "extremely_serious", "core", 100, "涉及国家安全的系统密钥、核心网络等"),
        ("national_security", "serious", "core", 90, "涉及国防、关键基础设施的敏感配置"),
        ("national_security", "general", "important", 80, "一般性国家安全相关数据"),
        # 经济运行
        ("economy", "extremely_serious", "core", 70, "影响国民经济命脉的核心数据"),
        ("economy", "serious", "important", 60, "可能导致金融市场大幅波动的未公开数据"),
        ("economy", "general", "sensitive", 50, "一般性经济运行相关数据"),
        # 社会秩序
        ("social_order", "extremely_serious", "core", 40, "涉及反恐、反洗钱等社会秩序核心数据"),
        ("social_order", "serious", "important", 30, "涉及重大金融犯罪的监测数据"),
        ("social_order", "general", "sensitive", 20, "一般性社会秩序相关数据"),
        # 公共利益
        ("public_interest", "extremely_serious", "core", 10, "涉及广大公众利益的核心数据"),
        ("public_interest", "serious", "important", 9, "可能影响公众利益的未公开重大信息"),
        ("public_interest", "general", "sensitive", 8, "一般性公共利益相关数据"),
        # 组织权益
        ("org_rights", "extremely_serious", "sensitive", 7, "对企业造成特别严重危害的数据泄露"),
        ("org_rights", "serious", "sensitive", 6, "对企业造成严重危害的数据泄露"),
        ("org_rights", "general", "normal", 5, "对企业造成一般危害的数据"),
        # 个人权益
        ("personal_rights", "extremely_serious", "sensitive", 4, "对个人造成特别严重危害的数据泄露（如生物特征）"),
        ("personal_rights", "serious", "sensitive", 3, "对个人造成严重危害的数据泄露（如交易记录）"),
        ("personal_rights", "general", "normal", 2, "对个人造成一般危害的数据"),
    ]

    for target, level, dlevel, priority, desc in rules:
        db.add(FGR(
            impact_target=target, impact_level=level, data_level=dlevel,
            priority=priority, description=desc,
            standard_ref="国信办通字〔2026〕2号 §5",
        ))
    db.commit()


if __name__ == "__main__":
    seed()
