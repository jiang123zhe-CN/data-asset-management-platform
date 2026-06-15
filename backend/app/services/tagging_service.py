"""数据打标流水线 — 以金融合规矩阵引擎为核心。

判定链路：ComplianceEngine（67类+矩阵）→ AI语义分析（兜底）→ 人工复核。
旧 RuleEngine 已移除。
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.field import Field
from app.models.finance_category import FinanceDataCategory, FinanceGradingRule
from app.models.tagging import TaggingHistory
from app.services.compliance_engine import ComplianceEngine
from app.services.llm_service import classify_field_with_ai


class TaggingPipeline:
    """打标流水线：合规矩阵 → AI兜底 → 人工复核。"""

    def __init__(self, db: Session):
        self.db = db

    def run(self, field_ids: list[int] | None = None, mode: str = "full") -> dict:
        """执行打标流水线。

        mode: "compliance" | "ai_only" | "full"
        默认 "full" = compliance_matrix + AI fallback
        """
        if field_ids:
            fields = self.db.query(Field).filter(
                Field.id.in_(field_ids), Field.status == "active"
            ).all()
        else:
            fields = self.db.query(Field).filter(Field.status == "active").all()

        processed = 0
        classified = 0
        tiered = 0
        errors = []

        for field in fields:
            try:
                if mode in ("compliance", "full"):
                    comp = ComplianceEngine(self.db)
                    results = comp.classify_fields([field.id])
                    if results:
                        r = results[0]
                        if r.get("finance_category_code") or r.get("finance_data_level"):
                            self._record_history(field, "compliance_matrix",
                                                r.get("finance_data_level"),
                                                r.get("confidence", 0.0))
                            if r.get("finance_category_code"):
                                classified += 1
                            if r.get("finance_data_level"):
                                tiered += 1
                            processed += 1
                            continue

                if mode in ("ai_only", "full"):
                    ai_result = self._run_ai(field)
                    if ai_result and (ai_result.get("finance_category_id") or ai_result.get("finance_data_level")):
                        self._apply_ai_result(field, ai_result)
                        if ai_result.get("finance_category_id"):
                            classified += 1
                        if ai_result.get("finance_data_level"):
                            tiered += 1
                        processed += 1
            except Exception as e:
                errors.append({"field_id": field.id, "field_name": field.name, "error": str(e)})

        self.db.commit()
        return {"processed": processed, "classified": classified, "tiered": tiered, "errors": errors}

    def _record_history(self, field: Field, method: str, new_level: str | None, confidence: float):
        """记录打标历史（仅当数据变化时）。"""
        now = datetime.now(timezone.utc)
        old_level = field.finance_data_level

        if old_level == new_level:
            return

        history = TaggingHistory(
            field_id=field.id,
            action="auto_tagged",
            old_tier_level=old_level,
            new_tier_level=new_level,
            new_confidence=confidence,
            tagging_method=method,
            comment=f"Auto-tagged via {method}",
        )
        self.db.add(history)

    def _apply_ai_result(self, field: Field, result: dict):
        """应用 AI 分析结果到字段。"""
        now = datetime.now(timezone.utc)
        old_level = field.finance_data_level
        new_level = result.get("finance_data_level")
        new_cat_id = result.get("finance_category_id")

        field.finance_category_id = new_cat_id or field.finance_category_id
        field.finance_data_level = new_level or field.finance_data_level
        field.tagging_method = "ai"
        field.tagging_confidence = result.get("confidence", 0.6)
        field.last_tagged_at = now
        field.updated_at = now

        if old_level != new_level or field.finance_category_id != new_cat_id:
            history = TaggingHistory(
                field_id=field.id,
                action="auto_tagged",
                old_tier_level=old_level,
                new_tier_level=new_level,
                new_confidence=result.get("confidence", 0.6),
                tagging_method="ai",
                comment="AI auto-tagged",
            )
            self.db.add(history)

    def _run_ai(self, field: Field) -> dict | None:
        """AI 语义兜底——使用金融合规分类标准。"""
        categories = (
            self.db.query(FinanceDataCategory)
            .filter(FinanceDataCategory.is_active == True, FinanceDataCategory.level == 3)
            .all()
        )
        grading_rules = (
            self.db.query(FinanceGradingRule)
            .filter(FinanceGradingRule.is_active == True)
            .all()
        )

        field_data = {
            "id": field.id,
            "name": field.name,
            "data_type": field.data_type,
            "table_name": field.table_name,
            "business_domain": field.business_domain,
            "description": field.description or "",
        }
        categories_data = [
            {"id": c.id, "name": c.name, "code": c.code,
             "ref_min_level": c.ref_min_level, "appendix_desc": c.appendix_desc or ""}
            for c in categories
        ]
        grading_data = [
            {"impact_target": r.impact_target, "impact_level": r.impact_level,
             "data_level": r.data_level, "description": r.description or ""}
            for r in grading_rules
        ]

        try:
            return classify_field_with_ai(field_data, categories_data, grading_data)
        except Exception:
            return None

    def manual_update(self, field: Field,
                      finance_category_id: int | None = None,
                      finance_data_level: str | None = None,
                      confidence: float = 1.0,
                      operator_id: int | None = None,
                      comment: str = "") -> Field:
        """人工修正打标结果。"""
        now = datetime.now(timezone.utc)
        old_cat = field.finance_category_id
        old_level = field.finance_data_level

        field.finance_category_id = finance_category_id if finance_category_id is not None else field.finance_category_id
        field.finance_data_level = finance_data_level if finance_data_level is not None else field.finance_data_level
        field.tagging_method = "manual"
        field.tagging_confidence = confidence
        field.last_tagged_at = now
        field.updated_at = now

        history = TaggingHistory(
            field_id=field.id,
            action="manual_update",
            old_tier_level=old_level,
            new_tier_level=field.finance_data_level,
            new_confidence=confidence,
            tagging_method="manual",
            operator_id=operator_id,
            comment=comment,
        )
        self.db.add(history)
        return field
