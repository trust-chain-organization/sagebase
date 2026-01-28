"""議案操作ログテーブルの作成.

議案の作成・更新・削除操作を記録するテーブルを追加。

Revision ID: 004
Revises: 003
Create Date: 2025-01-24
"""

from alembic import op


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """マイグレーション: 議案操作ログテーブルを作成.

    Note: init.sqlで既に最新スキーマが適用されている場合も安全に実行できる（冪等性）
    """
    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_operation_logs (
            id SERIAL PRIMARY KEY,
            proposal_id INTEGER NOT NULL,
            proposal_title VARCHAR(500) NOT NULL,
            operation_type VARCHAR(20) NOT NULL,
            user_id UUID REFERENCES users(user_id),
            operation_details JSONB,
            operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT check_proposal_operation_type
                CHECK (operation_type IN ('create', 'update', 'delete'))
        );
    """)

    # インデックス作成（冪等性確保のためIF NOT EXISTSを使用）
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_proposal_operation_logs_user_id
        ON proposal_operation_logs(user_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_proposal_operation_logs_operated_at
        ON proposal_operation_logs(operated_at DESC);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_proposal_operation_logs_operation_type
        ON proposal_operation_logs(operation_type);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_proposal_operation_logs_proposal_id
        ON proposal_operation_logs(proposal_id);
    """)

    # コメント追加
    op.execute("""
        COMMENT ON TABLE proposal_operation_logs
        IS '議案操作ログ（作成・更新・削除の履歴）';
    """)
    op.execute("""
        COMMENT ON COLUMN proposal_operation_logs.proposal_id
        IS '操作対象の議案ID';
    """)
    op.execute("""
        COMMENT ON COLUMN proposal_operation_logs.proposal_title
        IS '操作時点の議案タイトル';
    """)
    op.execute("""
        COMMENT ON COLUMN proposal_operation_logs.operation_type
        IS '操作種別（create: 作成, update: 更新, delete: 削除）';
    """)
    op.execute("""
        COMMENT ON COLUMN proposal_operation_logs.user_id
        IS '操作を行ったユーザーID';
    """)
    op.execute("""
        COMMENT ON COLUMN proposal_operation_logs.operation_details
        IS '操作の詳細（JSONフォーマット）';
    """)
    op.execute("""
        COMMENT ON COLUMN proposal_operation_logs.operated_at
        IS '操作日時';
    """)


def downgrade() -> None:
    """ロールバック: 議案操作ログテーブルを削除."""
    op.execute("DROP TABLE IF EXISTS proposal_operation_logs;")
