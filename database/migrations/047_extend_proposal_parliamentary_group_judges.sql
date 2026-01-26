-- 会派賛否テーブルを拡張: 政治家単位の賛否にも対応
-- judge_type: 賛否の種別（会派単位 or 政治家単位）
-- politician_id: 政治家単位の場合に使用

-- judge_type カラム追加（デフォルトは会派単位）
ALTER TABLE proposal_parliamentary_group_judges
ADD COLUMN IF NOT EXISTS judge_type VARCHAR(50) DEFAULT 'parliamentary_group';

-- politician_id カラム追加
ALTER TABLE proposal_parliamentary_group_judges
ADD COLUMN IF NOT EXISTS politician_id INTEGER REFERENCES politicians(id);

-- parliamentary_group_id を NULL許容に変更
ALTER TABLE proposal_parliamentary_group_judges
ALTER COLUMN parliamentary_group_id DROP NOT NULL;

-- 既存のUNIQUE制約を削除（存在する場合）
ALTER TABLE proposal_parliamentary_group_judges
DROP CONSTRAINT IF EXISTS proposal_parliamentary_group_judges_proposal_id_parliamentary_key;

-- 新しいUNIQUE制約を追加
-- proposal_id + parliamentary_group_id + politician_id の組み合わせで一意性を保証
-- NULLは別の値として扱うためCOALESCEを使用
CREATE UNIQUE INDEX IF NOT EXISTS idx_proposal_pg_judges_unique
ON proposal_parliamentary_group_judges(
    proposal_id,
    COALESCE(parliamentary_group_id, -1),
    COALESCE(politician_id, -1)
);

-- politician_idのインデックス
CREATE INDEX IF NOT EXISTS idx_proposal_parliamentary_group_judges_politician
    ON proposal_parliamentary_group_judges(politician_id);

-- judge_typeのインデックス
CREATE INDEX IF NOT EXISTS idx_proposal_parliamentary_group_judges_type
    ON proposal_parliamentary_group_judges(judge_type);

-- コメント追加
COMMENT ON COLUMN proposal_parliamentary_group_judges.judge_type IS '賛否の種別（parliamentary_group: 会派単位, politician: 政治家単位）';
COMMENT ON COLUMN proposal_parliamentary_group_judges.politician_id IS '政治家ID（政治家単位の場合に使用）';
