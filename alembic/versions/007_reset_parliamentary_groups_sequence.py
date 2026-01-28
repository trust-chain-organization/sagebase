"""Issue #1036: 議員団シーケンスのリセット.

Revision ID: 007
Revises: 006
Create Date: 2026-01-28

シードデータでIDを明示的に指定してINSERTした後、シーケンスが古い値のままになっている
問題を修正。既存データの最大IDに基づいてシーケンスをリセットする。
"""

from alembic import op


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Reset parliamentary_groups sequence."""
    # 議員団テーブルのシーケンスを最大ID+1にリセット
    op.execute("""
        SELECT setval(
            'parliamentary_groups_id_seq',
            COALESCE((SELECT MAX(id) FROM parliamentary_groups), 0) + 1,
            false
        );
    """)

    # 議員団メンバーシップのシーケンスも同様にリセット
    op.execute("""
        SELECT setval(
            'parliamentary_group_memberships_id_seq',
            COALESCE((SELECT MAX(id) FROM parliamentary_group_memberships), 0) + 1,
            false
        );
    """)


def downgrade() -> None:
    """Rollback migration: No action needed.

    シーケンスリセットはデータを破壊しないため、ロールバックは不要。
    シーケンスを元の値に戻すことは危険（衝突の原因になる）なため、何もしない。
    """
    pass
