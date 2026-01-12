-- 政治家操作ログテーブルの作成
-- このテーブルは政治家の作成・更新・削除操作を記録します

CREATE TABLE politician_operation_logs (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL,  -- 操作対象の政治家ID（削除後も参照可能にするためFK制約なし）
    politician_name VARCHAR(255) NOT NULL,  -- 操作時点の政治家名
    operation_type VARCHAR(20) NOT NULL,  -- 'create', 'update', 'delete'
    user_id UUID REFERENCES users(user_id),  -- 操作を行ったユーザー
    operation_details JSONB,  -- 操作の詳細（変更前後の値など）
    operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_operation_type CHECK (operation_type IN ('create', 'update', 'delete'))
);

-- インデックス
CREATE INDEX idx_politician_operation_logs_user_id ON politician_operation_logs(user_id);
CREATE INDEX idx_politician_operation_logs_operated_at ON politician_operation_logs(operated_at DESC);
CREATE INDEX idx_politician_operation_logs_operation_type ON politician_operation_logs(operation_type);
CREATE INDEX idx_politician_operation_logs_politician_id ON politician_operation_logs(politician_id);

-- コメント
COMMENT ON TABLE politician_operation_logs IS '政治家操作ログ（作成・更新・削除の履歴）';
COMMENT ON COLUMN politician_operation_logs.politician_id IS '操作対象の政治家ID';
COMMENT ON COLUMN politician_operation_logs.politician_name IS '操作時点の政治家名';
COMMENT ON COLUMN politician_operation_logs.operation_type IS '操作種別（create: 作成, update: 更新, delete: 削除）';
COMMENT ON COLUMN politician_operation_logs.user_id IS '操作を行ったユーザーID';
COMMENT ON COLUMN politician_operation_logs.operation_details IS '操作の詳細（JSONフォーマット）';
COMMENT ON COLUMN politician_operation_logs.operated_at IS '操作日時';
