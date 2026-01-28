"""議案テーブルのスキーマ変更.

contentをtitleにリネーム、不要カラム削除、新規カラム追加。

Revision ID: 003
Revises: 002
Create Date: 2025-01-24
"""

from alembic import op


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """マイグレーション: 議案テーブルのスキーマ変更を適用.

    変更内容:
    - contentをtitleにリネーム
    - votes_url、conference_idを追加
    - status、submission_date、submitter、proposal_number、summaryを削除

    Note: init.sqlで既に最新スキーマが適用されている場合も安全に実行できる（冪等性）
    """
    # 1. contentをtitleにリネーム（contentカラムが存在する場合のみ）
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'proposals' AND column_name = 'content'
            ) THEN
                ALTER TABLE proposals RENAME COLUMN content TO title;
            END IF;
        END$$;
    """)

    # 2. 新規カラム追加
    op.execute("ALTER TABLE proposals ADD COLUMN IF NOT EXISTS votes_url VARCHAR;")
    op.execute("""
        ALTER TABLE proposals ADD COLUMN IF NOT EXISTS conference_id INT
        REFERENCES conferences(id) ON DELETE SET NULL;
    """)

    # 3. インデックス追加
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_proposals_conference_id
        ON proposals(conference_id);
    """)

    # 4. 不要カラム削除
    op.execute("ALTER TABLE proposals DROP COLUMN IF EXISTS status;")
    op.execute("ALTER TABLE proposals DROP COLUMN IF EXISTS submission_date;")
    op.execute("ALTER TABLE proposals DROP COLUMN IF EXISTS submitter;")
    op.execute("ALTER TABLE proposals DROP COLUMN IF EXISTS proposal_number;")
    op.execute("ALTER TABLE proposals DROP COLUMN IF EXISTS summary;")


def downgrade() -> None:
    """ロールバック: 議案テーブルのスキーマ変更を元に戻す.

    注意: データ損失を伴う変更のため、削除したカラムのデータは復元できません。
    """
    # 1. 削除したカラムを再追加（データは空）
    op.execute("ALTER TABLE proposals ADD COLUMN IF NOT EXISTS status VARCHAR;")
    op.execute(
        "ALTER TABLE proposals ADD COLUMN IF NOT EXISTS submission_date TIMESTAMP;"
    )
    op.execute("ALTER TABLE proposals ADD COLUMN IF NOT EXISTS submitter VARCHAR;")
    op.execute(
        "ALTER TABLE proposals ADD COLUMN IF NOT EXISTS proposal_number VARCHAR;"
    )
    op.execute("ALTER TABLE proposals ADD COLUMN IF NOT EXISTS summary TEXT;")

    # 2. インデックス削除
    op.execute("DROP INDEX IF EXISTS idx_proposals_conference_id;")

    # 3. 追加したカラムを削除
    op.execute("ALTER TABLE proposals DROP COLUMN IF EXISTS conference_id;")
    op.execute("ALTER TABLE proposals DROP COLUMN IF EXISTS votes_url;")

    # 4. titleをcontentに戻す
    op.execute("ALTER TABLE proposals RENAME COLUMN title TO content;")
