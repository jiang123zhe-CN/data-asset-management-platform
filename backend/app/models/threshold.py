"""30%变化阈值快照模型 — 追踪核心/重要数据量变化，满足指南动态管理要求。"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey

from app.core.database import Base


class ImportantDataSnapshot(Base):
    """核心数据 + 重要数据 条目数 & 存储量快照。

    每次报送（或手动创建快照）时记录当时的 core/important 数据统计。
    下次检测时对比，变化超过 30% 即触发重新报送提醒。
    标准依据：国信办通字〔2026〕2号 §6.5 动态更新管理。
    """
    __tablename__ = "important_data_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 统计快照
    total_fields = Column(Integer, nullable=False, default=0)     # core + important 合计字段数
    core_records = Column(Integer, nullable=False, default=0)      # 核心数据字段数
    important_records = Column(Integer, nullable=False, default=0)  # 重要数据字段数
    storage_estimate = Column(Integer, nullable=False, default=0)  # 存储量估算（字段数，实际可扩展为GB）

    # 上一次快照对比
    prev_total_fields = Column(Integer, nullable=True)
    prev_core_records = Column(Integer, nullable=True)
    prev_important_records = Column(Integer, nullable=True)
    prev_storage_estimate = Column(Integer, nullable=True)

    # 阈值检测结果
    exceeds_threshold = Column(Boolean, nullable=False, default=False)  # 是否超过30%

    # 报送状态
    status = Column(String(20), nullable=False, default="draft")  # draft / submitted / acknowledged

    # 治理
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, nullable=False, default=True)
