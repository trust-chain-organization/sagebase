"""Many-to-Many構造への変更: 会派賛否に複数の会派・政治家を紐付け可能に.

Revision ID: 006
Revises: 005
Create Date: 2026-01-26

1つの賛否レコードに複数の会派・政治家を紐付けられるMany-to-Many構造に変更。
中間テーブルを作成し、既存データを移行。
"""

from alembic import op


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Create junction tables for Many-to-Many relationship."""
    op.execute("""
        -- 1. 中間テーブル作成: 賛否⇔会派
        CREATE TABLE IF NOT EXISTS proposal_judge_parliamentary_groups (
            id SERIAL PRIMARY KEY,
            judge_id INTEGER NOT NULL
                REFERENCES proposal_parliamentary_group_judges(id) ON DELETE CASCADE,
            parliamentary_group_id INTEGER NOT NULL
                REFERENCES parliamentary_groups(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(judge_id, parliamentary_group_id)
        );

        -- 2. 中間テーブル作成: 賛否⇔政治家
        CREATE TABLE IF NOT EXISTS proposal_judge_politicians (
            id SERIAL PRIMARY KEY,
            judge_id INTEGER NOT NULL
                REFERENCES proposal_parliamentary_group_judges(id) ON DELETE CASCADE,
            politician_id INTEGER NOT NULL
                REFERENCES politicians(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(judge_id, politician_id)
        );

        -- 3. 既存データを中間テーブルに移行（旧カラムが存在する場合のみ）
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'proposal_parliamentary_group_judges'
                AND column_name = 'parliamentary_group_id'
            ) THEN
                INSERT INTO proposal_judge_parliamentary_groups
                    (judge_id, parliamentary_group_id)
                SELECT id, parliamentary_group_id
                FROM proposal_parliamentary_group_judges
                WHERE parliamentary_group_id IS NOT NULL
                ON CONFLICT (judge_id, parliamentary_group_id) DO NOTHING;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'proposal_parliamentary_group_judges'
                AND column_name = 'politician_id'
            ) THEN
                INSERT INTO proposal_judge_politicians (judge_id, politician_id)
                SELECT id, politician_id
                FROM proposal_parliamentary_group_judges
                WHERE politician_id IS NOT NULL
                ON CONFLICT (judge_id, politician_id) DO NOTHING;
            END IF;
        END $$;

        -- 4. 旧UNIQUE制約とインデックスを削除（存在する場合のみ）
        DROP INDEX IF EXISTS idx_proposal_pg_judges_unique;

        -- 5. 旧カラムを削除（存在する場合のみ）
        ALTER TABLE proposal_parliamentary_group_judges
            DROP COLUMN IF EXISTS parliamentary_group_id;
        ALTER TABLE proposal_parliamentary_group_judges
            DROP COLUMN IF EXISTS politician_id;

        -- 6. 新しいインデックスを作成
        CREATE INDEX IF NOT EXISTS idx_pjpg_judge_id
            ON proposal_judge_parliamentary_groups(judge_id);
        CREATE INDEX IF NOT EXISTS idx_pjpg_parliamentary_group_id
            ON proposal_judge_parliamentary_groups(parliamentary_group_id);
        CREATE INDEX IF NOT EXISTS idx_pjp_judge_id
            ON proposal_judge_politicians(judge_id);
        CREATE INDEX IF NOT EXISTS idx_pjp_politician_id
            ON proposal_judge_politicians(politician_id);

        -- 7. コメント追加
        COMMENT ON TABLE proposal_judge_parliamentary_groups
            IS '賛否レコードと会派の中間テーブル（Many-to-Many）';
        COMMENT ON TABLE proposal_judge_politicians
            IS '賛否レコードと政治家の中間テーブル（Many-to-Many）';
    """)


def downgrade() -> None:
    """Rollback migration: Restore old 1-to-1 structure."""
    op.execute("""
        -- 1. 旧カラムを復元
        ALTER TABLE proposal_parliamentary_group_judges
            ADD COLUMN IF NOT EXISTS parliamentary_group_id INTEGER
                REFERENCES parliamentary_groups(id);
        ALTER TABLE proposal_parliamentary_group_judges
            ADD COLUMN IF NOT EXISTS politician_id INTEGER
                REFERENCES politicians(id);

        -- 2. 中間テーブルからデータを復元（最初のIDのみ）
        UPDATE proposal_parliamentary_group_judges j
        SET parliamentary_group_id = (
            SELECT parliamentary_group_id
            FROM proposal_judge_parliamentary_groups pjpg
            WHERE pjpg.judge_id = j.id
            ORDER BY pjpg.id
            LIMIT 1
        )
        WHERE parliamentary_group_id IS NULL;

        UPDATE proposal_parliamentary_group_judges j
        SET politician_id = (
            SELECT politician_id
            FROM proposal_judge_politicians pjp
            WHERE pjp.judge_id = j.id
            ORDER BY pjp.id
            LIMIT 1
        )
        WHERE politician_id IS NULL;

        -- 3. 中間テーブルを削除
        DROP TABLE IF EXISTS proposal_judge_politicians;
        DROP TABLE IF EXISTS proposal_judge_parliamentary_groups;

        -- 4. インデックスを削除
        DROP INDEX IF EXISTS idx_pjpg_judge_id;
        DROP INDEX IF EXISTS idx_pjpg_parliamentary_group_id;
        DROP INDEX IF EXISTS idx_pjp_judge_id;
        DROP INDEX IF EXISTS idx_pjp_politician_id;
    """)
