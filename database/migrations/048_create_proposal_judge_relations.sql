-- Many-to-Many構造への変更: 1つの賛否レコードに複数の会派・政治家を紐付け可能にする
-- 中間テーブルを作成し、既存データを移行

-- 1. 中間テーブル作成: 賛否⇔会派
CREATE TABLE IF NOT EXISTS proposal_judge_parliamentary_groups (
    id SERIAL PRIMARY KEY,
    judge_id INTEGER NOT NULL REFERENCES proposal_parliamentary_group_judges(id) ON DELETE CASCADE,
    parliamentary_group_id INTEGER NOT NULL REFERENCES parliamentary_groups(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(judge_id, parliamentary_group_id)
);

-- 2. 中間テーブル作成: 賛否⇔政治家
CREATE TABLE IF NOT EXISTS proposal_judge_politicians (
    id SERIAL PRIMARY KEY,
    judge_id INTEGER NOT NULL REFERENCES proposal_parliamentary_group_judges(id) ON DELETE CASCADE,
    politician_id INTEGER NOT NULL REFERENCES politicians(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(judge_id, politician_id)
);

-- 3. 既存データを中間テーブルに移行
INSERT INTO proposal_judge_parliamentary_groups (judge_id, parliamentary_group_id)
SELECT id, parliamentary_group_id
FROM proposal_parliamentary_group_judges
WHERE parliamentary_group_id IS NOT NULL
ON CONFLICT (judge_id, parliamentary_group_id) DO NOTHING;

INSERT INTO proposal_judge_politicians (judge_id, politician_id)
SELECT id, politician_id
FROM proposal_parliamentary_group_judges
WHERE politician_id IS NOT NULL
ON CONFLICT (judge_id, politician_id) DO NOTHING;

-- 4. 旧UNIQUE制約とインデックスを削除
DROP INDEX IF EXISTS idx_proposal_pg_judges_unique;

-- 5. 旧カラムを削除
ALTER TABLE proposal_parliamentary_group_judges DROP COLUMN IF EXISTS parliamentary_group_id;
ALTER TABLE proposal_parliamentary_group_judges DROP COLUMN IF EXISTS politician_id;

-- 6. 新しいインデックスを作成
CREATE INDEX IF NOT EXISTS idx_pjpg_judge_id ON proposal_judge_parliamentary_groups(judge_id);
CREATE INDEX IF NOT EXISTS idx_pjpg_parliamentary_group_id ON proposal_judge_parliamentary_groups(parliamentary_group_id);
CREATE INDEX IF NOT EXISTS idx_pjp_judge_id ON proposal_judge_politicians(judge_id);
CREATE INDEX IF NOT EXISTS idx_pjp_politician_id ON proposal_judge_politicians(politician_id);

-- 7. コメント追加
COMMENT ON TABLE proposal_judge_parliamentary_groups IS '賛否レコードと会派の中間テーブル（Many-to-Many）';
COMMENT ON TABLE proposal_judge_politicians IS '賛否レコードと政治家の中間テーブル（Many-to-Many）';
