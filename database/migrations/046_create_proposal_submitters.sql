-- proposal_submittersテーブルの作成
-- 議案の提出者情報を構造化して管理するための中間テーブル
-- 1つの議案に対して複数の提出者（連名提出）を紐付けることができる

CREATE TABLE proposal_submitters (
    id SERIAL PRIMARY KEY,
    proposal_id INT NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    submitter_type VARCHAR(50) NOT NULL,
    politician_id INT REFERENCES politicians(id) ON DELETE SET NULL,
    parliamentary_group_id INT REFERENCES parliamentary_groups(id) ON DELETE SET NULL,
    raw_name VARCHAR(255),
    is_representative BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックスの作成
CREATE INDEX idx_proposal_submitters_proposal_id ON proposal_submitters(proposal_id);
CREATE INDEX idx_proposal_submitters_politician_id ON proposal_submitters(politician_id);
CREATE INDEX idx_proposal_submitters_parliamentary_group_id ON proposal_submitters(parliamentary_group_id);

-- 同一議案内でpolitician_idとparliamentary_group_idの組み合わせが重複しないようにする
-- ただし、NULLの場合は重複を許容する（COALESCE使用）
CREATE UNIQUE INDEX idx_proposal_submitters_unique ON proposal_submitters(
    proposal_id,
    COALESCE(politician_id, -1),
    COALESCE(parliamentary_group_id, -1)
);
