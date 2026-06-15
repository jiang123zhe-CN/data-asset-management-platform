"""add_finance_compliance_tables

Revision ID: d6315e75dcfc
Revises: 0c8ad2218e8f
Create Date: 2026-06-15 11:31:54.052569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6315e75dcfc'
down_revision: Union[str, None] = '0c8ad2218e8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 新建两张金融合规表 ──
    op.create_table('finance_grading_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('impact_target', sa.String(length=50), nullable=False),
        sa.Column('impact_level', sa.String(length=50), nullable=False),
        sa.Column('data_level', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('examples', sa.Text(), nullable=True),
        sa.Column('standard_ref', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finance_grading_rules_impact_target'), 'finance_grading_rules', ['impact_target'], unique=False)

    op.create_table('finance_data_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('finance_product', sa.String(length=100), nullable=True),
        sa.Column('ref_min_level', sa.String(length=20), nullable=False),
        sa.Column('level_rationale', sa.Text(), nullable=True),
        sa.Column('appendix_desc', sa.Text(), nullable=True),
        sa.Column('appendix_example', sa.Text(), nullable=True),
        sa.Column('mapped_category_id', sa.Integer(), nullable=True),
        sa.Column('standard_ref', sa.String(length=500), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['mapped_category_id'], ['classification_categories.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['finance_data_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finance_data_categories_code'), 'finance_data_categories', ['code'], unique=True)
    op.create_index(op.f('ix_finance_data_categories_parent_id'), 'finance_data_categories', ['parent_id'], unique=False)

    # ── Fields 表新增字段（SQLite 不支持 ALTER ADD FK，用原生 SQL） ──
    op.execute('ALTER TABLE fields ADD COLUMN finance_category_id INTEGER REFERENCES finance_data_categories(id)')
    op.execute('ALTER TABLE fields ADD COLUMN finance_data_level VARCHAR(20)')


def downgrade() -> None:
    op.execute('ALTER TABLE fields DROP COLUMN finance_data_level')
    op.execute('ALTER TABLE fields DROP COLUMN finance_category_id')

    op.drop_index(op.f('ix_finance_data_categories_parent_id'), table_name='finance_data_categories')
    op.drop_index(op.f('ix_finance_data_categories_code'), table_name='finance_data_categories')
    op.drop_table('finance_data_categories')
    op.drop_index(op.f('ix_finance_grading_rules_impact_target'), table_name='finance_grading_rules')
    op.drop_table('finance_grading_rules')
