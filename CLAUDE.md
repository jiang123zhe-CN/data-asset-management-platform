# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Backend (from backend/)
pip install -r requirements.txt                    # Install dependencies
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # Dev server
python seed.py                                     # Seed sample data (idempotent)

# Frontend (from frontend/)
npm install                                        # Install dependencies
npm run dev                                        # Vite dev server on :5173
npm run build                                      # Production build

# Deploy (from deploy/)
bash deploy/deploy.sh                              # Full deploy to Alibaba Cloud (run as root on server)
```

## Architecture Overview

**Stack**: FastAPI (Python) + React 19 + Ant Design 6 + SQLite (dev) / PostgreSQL (prod) + JWT auth + DashScope AI

**Request flow**: Browser → Vite dev server (`:5173`) → proxy `/api` → FastAPI (`:8000`). The Vite proxy rewrites 307 redirect Location headers so redirects don't bypass the proxy. The frontend axios interceptor proactively adds trailing slashes to avoid redirects.

**Database**: SQLite with WAL mode in dev; PostgreSQL on Alibaba Cloud. Alembic migration files exist but are empty — `Base.metadata.create_all()` handles schema management.

**Auth**: JWT tokens (HS256, 30min) in `localStorage` key `dam_token`. Five roles: `admin` > `system_admin` > `data_admin` > `data_entry` > `reviewer`. Routes declare minimum role via `require_role(*roles)`.

## Core Feature: 金融合规分类分级

The platform implements the **《金融信息服务数据分类分级指南》** (国信办通字〔2026〕2号):

### Data Model
- `FinanceDataCategory` — 67-class 3-level standard (3 L1 → 9 L2 → 67 L3), self-referential `parent_id`
- `FinanceGradingRule` — 18-grid matrix: impact target × impact level → data level
- `ImportantDataSnapshot` — 30% change threshold tracking for core/important data
- `Field` has `finance_category_id` + `finance_data_level` (core/important/sensitive/normal)

### ComplianceEngine (`backend/app/services/compliance_engine.py`)
5-layer matching pipeline:
1. **Exact keywords** → `EXACT_MAP` dict, highest confidence (+20%)
2. **Product signals** → financial product detection (stock/bond/fund/forex/…)
3. **Domain mapping** → `business_domain` field → category
4. **Fallback inference** → heuristic patterns (logs, personal info, transactions, …)
5. **Traversal scoring** → substring match across all L3 categories

Grading: impact target × impact level matrix → data level. Principles: 就高从严 (table-level max inheritance), 级别不可降 (no downgrade below ref_min_level).

Confidence: `base 0.60 + cat_matched 0.10 + layer_bonus (0.20/0.15/0.10) + signal_bonus 0.05 + upgrade_bonus 0.05`, capped at 0.99.

### Key Endpoints
- `POST /api/compliance/classify` — Run compliance classification on all/selected fields
- `GET /api/compliance/export/inventory` — Export §6.4 standard format Excel
- `GET /api/compliance/threshold` — 30% change threshold check
- `POST /api/compliance/threshold/snapshot` — Create baseline snapshot
- `GET /api/tagging/export` — Export all tagging results Excel
- `GET /api/fields` — Now includes `finance_category_path` (L1 > L2 > L3) + `finance_data_level`

### Frontend Pages
- `/standards` — **StandardPage**: 3 tabs: 分类标准 (3-column cascade picker), 分级矩阵 (18-grid table), 执行分类 (classify + export + threshold snapshots)
- `/tagging` — **TaggingPage**: Tagging results with compliance path/level, export, manual correction drawer, multi-engine trigger
- `/fields` — **FieldPage**: Fields table with compliance classification column + level filter

## Key Modules

### Backend Routers (prefixes)
- `/api/auth` — Login, token refresh, password change
- `/api/compliance` — Finance compliance: categories tree, grading matrix, classify, export, threshold snapshots
- `/api/directories` — Tree CRUD. Self-referential FK; delete blocked if children exist.
- `/api/fields` — CRUD + Excel import/export. Auto-runs ComplianceEngine on create/import. Soft-delete via `status=inactive`.
- `/api/mappings` — Many-to-many directories ↔ fields. AI auto-map only targets leaf directories (deepest level). Batch create/delete, ECharts visualization.
- `/api/reviews` — Human review: `anomaly` (auto-detected) and `ai_mapping` (AI suggestions).
- `/api/reports` — Aggregation: summary, by-directory, by-sensitivity distribution.
- `/api/tagging` — Tagging pipeline: compliance matrix + AI. Stats, manual update, batch update, export.
- `/api/users` — Admin-only user management.
- `/api/logs` — Operation log query.

### Services
- `compliance_engine.py` — 5-layer matching + matrix grading + 就高从严 (see above)
- `tagging_service.py` — `TaggingPipeline`: "compliance" mode = ComplianceEngine only; "full" = compliance + AI fallback
- `llm_service.py` — Qwen (`qwen-plus`) via DashScope API. AI auto-map + field classification.
- `excel_service.py` — Template gen, import, export: fields, mappings, compliance inventory (§6.4), tagging results
- `anomaly_detector.py` — Unmapped fields + missing metadata detection
- `log_service.py` — Available but not wired into most CRUD routes.

## Patterns and Conventions

- **Trailing slash**: Frontend interceptor adds `/` to single-segment URLs. All compliance/tagging routes have dual decorators (with/without trailing slash).
- **Soft deletion**: Fields → `status=inactive`; directories → `is_active=False`; users → `is_active=False`.
- **Idempotent seed**: `seed.py` checks counts before inserting — safe to run multiple times. Seeds finance categories (67 classes) + grading rules (18 matrix rows).
- **AI is human-in-the-loop**: Auto-map creates `ReviewRecord` entries; reviewer must approve before mapping is created.
- **Mappings go to leaf level**: Both batch dialog and AI auto-map only target leaf directories (no children).
- **Compliance auto-classify**: New field creation and Excel import both auto-run ComplianceEngine.

## Gotchas

- **Alembic migrations are empty**: Use `Base.metadata.create_all()` for schema in both dev and prod.
- **New models must be imported before create_all()**: Add imports to `main.py` or the relevant API module's top level.
- **Trailing slash = 307**: All compliance routes must have dual `@router.get("/path/")` + `@router.get("/path")` decorators.
- **SQLite FK constraints**: `NoReferencedTableError` in standalone scripts means not all models are imported. Import `User` and all referenced models.
- **CORS**: Only `localhost:5173` allowed in dev. Update for different port/domain.
