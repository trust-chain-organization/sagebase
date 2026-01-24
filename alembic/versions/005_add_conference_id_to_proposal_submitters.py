"""Add conference_id to proposal_submitters table.

Revision ID: 005
Revises: 004
Create Date: 2025-01-24

議案提出者テーブルに会議体IDを追加し、会議体が提出者となるケースに対応する。
"""

from alembic import op


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add conference_id column to proposal_submitters."""
    op.execute("""
        -- 会議体IDカラムを追加
        ALTER TABLE proposal_submitters
        ADD COLUMN IF NOT EXISTS conference_id INT
            REFERENCES conferences(id) ON DELETE SET NULL;

        -- インデックスを作成
        CREATE INDEX IF NOT EXISTS idx_proposal_submitters_conference_id
        ON proposal_submitters(conference_id);

        -- コメント追加
        COMMENT ON COLUMN proposal_submitters.conference_id
            IS '会議体が提出者の場合のConference ID';
    """)


def downgrade() -> None:
    """Rollback migration: Remove conference_id column from proposal_submitters."""
    op.execute("""
        -- インデックスを削除
        DROP INDEX IF EXISTS idx_proposal_submitters_conference_id;

        -- カラムを削除
        ALTER TABLE proposal_submitters
        DROP COLUMN IF EXISTS conference_id;
    """)
