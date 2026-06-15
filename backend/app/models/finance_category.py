from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey

from app.core.database import Base


class FinanceDataCategory(Base):
    """金融信息服务数据分类（67类三级标准分类）

    源自六部门《金融信息服务数据分类分级指南》（国信办通字〔2026〕2号）。
    层级：一级(3类) → 二级(9类) → 三级(67类)，每级含附录A的参考最低级别。
    """
    __tablename__ = "finance_data_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # 如 FIN_BIZ_MKT_STOCK
    name = Column(String(200), nullable=False)                          # 如"股票数据"
    level = Column(Integer, nullable=False, default=1)                  # 1=一级, 2=二级, 3=三级
    parent_id = Column(Integer, ForeignKey("finance_data_categories.id"), nullable=True, index=True)

    # 数据属性
    data_type = Column(String(50), nullable=False)                      # business / user / enterprise
    finance_product = Column(String(100), nullable=True)                # stock / bond / fund / forex / commodity / futures_option

    # 分级参考（附录A）
    ref_min_level = Column(String(20), nullable=False, default="normal")  # core / important / sensitive / normal
    level_rationale = Column(Text, nullable=True)                          # 分级理由

    # 附录A 描述
    appendix_desc = Column(Text, nullable=True)    # 数据描述
    appendix_example = Column(Text, nullable=True)  # 数据示例

    # 映射到现有分类体系
    mapped_category_id = Column(Integer, ForeignKey("classification_categories.id"), nullable=True)

    # 治理字段
    standard_ref = Column(String(500), nullable=True, default="国信办通字〔2026〕2号")
    version = Column(String(50), nullable=False, default="2026-06")
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class FinanceGradingRule(Base):
    """金融数据分级矩阵规则

    按指南§5的分级判定矩阵：影响对象 × 危害程度 → 数据级别。
    替代 / 补充现有的关键词匹配式 TieringRule。
    """
    __tablename__ = "finance_grading_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    impact_target = Column(String(50), nullable=False, index=True)
    # national_security / economy / social_order / public_interest / org_rights / personal_rights

    impact_level = Column(String(50), nullable=False)
    # extremely_serious / serious / general

    data_level = Column(String(20), nullable=False)
    # core / important / sensitive / normal

    priority = Column(Integer, nullable=False, default=0)

    # 规则描述
    description = Column(Text, nullable=True)
    examples = Column(Text, nullable=True)

    # 治理
    standard_ref = Column(String(500), nullable=True, default="国信办通字〔2026〕2号 §5")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
