-- Database Schema for Political Activity Tracking Application
-- Version: 2026-01-28
--
-- このスキーマは以下のマイグレーションを統合した最新版です:
--   - レガシーマイグレーション: database/migrations/001〜048
--   - Alembicマイグレーション: alembic/versions/001〜007
--
-- 新規環境ではこのファイルのみで最新スキーマが構築されます。
-- その後、Alembicの `alembic stamp head` でバージョン管理を開始します。

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- エンティティタイプのENUM型
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'entity_type') THEN
        CREATE TYPE entity_type AS ENUM (
            'statement',
            'politician',
            'speaker',
            'conference_member',
            'parliamentary_group_member'
        );
    END IF;
END$$;

-- =============================================================================
-- 基本テーブル
-- =============================================================================

-- 開催主体テーブル
CREATE TABLE governing_bodies (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    type VARCHAR, -- 例: "国", "都道府県", "市町村"
    organization_code CHAR(6) UNIQUE, -- 総務省の6桁地方自治体コード
    organization_type VARCHAR(20), -- 詳細な組織種別
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 同じ名前と種別の組み合わせは一意とする
    UNIQUE(name, type)
);

-- 会議体テーブル (議会や委員会など)
CREATE TABLE conferences (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    type VARCHAR, -- 例: "国会全体", "議院", "地方議会全体", "常任委員会"
    governing_body_id INTEGER REFERENCES governing_bodies(id), -- NULL許容 (migration 012)
    members_introduction_url VARCHAR(255), -- メンバー紹介ページURL
    prefecture VARCHAR(10), -- 都道府県（全国は国会を表す）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 同じ開催主体内で同じ名前の会議体は一意とする
    UNIQUE(name, governing_body_id)
);

-- 会議テーブル (具体的な開催インスタンス)
CREATE TABLE meetings (
    id SERIAL PRIMARY KEY,
    conference_id INTEGER NOT NULL REFERENCES conferences(id),
    date DATE, -- 開催日
    url VARCHAR, -- 会議関連のURLまたは議事録PDFのURL
    name VARCHAR, -- 会議名
    gcs_pdf_uri VARCHAR(512), -- Google Cloud Storage URI for PDF
    gcs_text_uri VARCHAR(512), -- Google Cloud Storage URI for text
    attendees_mapping JSONB, -- 出席者の役職と名前のマッピング
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議事録テーブル
CREATE TABLE minutes (
    id SERIAL PRIMARY KEY,
    url VARCHAR, -- 議事録PDFなどのURL
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    processed_at TIMESTAMP, -- 処理済み日時
    llm_process_id VARCHAR(100), -- LLM処理履歴との関連付けID
    role_name_mappings JSONB, -- 役職-人名マッピング
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 政党テーブル
CREATE TABLE political_parties (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE, -- 政党名 (重複なし)
    members_list_url TEXT, -- 議員一覧ページのURL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 政治家テーブル
CREATE TABLE politicians (
    id SERIAL PRIMARY KEY, -- 政治家固有のID
    name VARCHAR NOT NULL, -- 政治家名
    political_party_id INTEGER REFERENCES political_parties(id), -- 現在の主要所属政党
    prefecture VARCHAR(10), -- 選挙区の都道府県
    furigana VARCHAR, -- 名前の読み（ひらがな）
    district VARCHAR, -- 選挙区
    profile_page_url VARCHAR, -- プロフィールページURL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- ユーザー管理テーブル
-- =============================================================================

-- ユーザーテーブル (ログインユーザー管理)
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- LLM処理関連テーブル
-- =============================================================================

-- LLM処理履歴テーブル
CREATE TABLE llm_processing_history (
    id SERIAL PRIMARY KEY,

    -- Processing information
    processing_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,

    -- Prompt information
    prompt_template TEXT NOT NULL,
    prompt_variables JSONB NOT NULL DEFAULT '{}',

    -- Input reference
    input_reference_type VARCHAR(50) NOT NULL,
    input_reference_id INTEGER NOT NULL,

    -- Processing status and results
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result JSONB,
    error_message TEXT,

    -- Additional metadata
    processing_metadata JSONB NOT NULL DEFAULT '{}',
    created_by VARCHAR(100) DEFAULT 'system',

    -- Timing information
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Standard timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- プロンプトテンプレートのバージョン管理テーブル
CREATE TABLE prompt_versions (
    id SERIAL PRIMARY KEY,

    -- Prompt identification
    prompt_key VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,

    -- Prompt content
    template TEXT NOT NULL,
    description TEXT,

    -- Status and metadata
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    variables TEXT[], -- Array of variable names expected in the template
    prompt_metadata JSONB NOT NULL DEFAULT '{}',
    created_by VARCHAR(100),

    -- Standard timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint to prevent duplicate versions
    CONSTRAINT uk_prompt_version UNIQUE (prompt_key, version)
);

-- 抽出ログテーブル
CREATE TABLE extraction_logs (
    id SERIAL PRIMARY KEY,

    -- 抽出対象エンティティの情報
    entity_type entity_type NOT NULL,
    entity_id INTEGER NOT NULL,

    -- パイプライン情報
    pipeline_version VARCHAR(100) NOT NULL,

    -- 抽出データ
    extracted_data JSONB NOT NULL,
    confidence_score FLOAT,

    -- 追加メタデータ
    extraction_metadata JSONB NOT NULL DEFAULT '{}',

    -- 標準タイムスタンプ
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 発言者・発言関連テーブル
-- =============================================================================

-- 発言者テーブル
CREATE TABLE speakers (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL, -- 発言者名
    type VARCHAR, -- 例: "政治家", "参考人", "議長", "政府職員"
    political_party_name VARCHAR, -- 所属政党名（政治家の場合）
    position VARCHAR, -- 役職・肩書き
    is_politician BOOLEAN DEFAULT FALSE, -- 政治家かどうか
    politician_id INTEGER REFERENCES politicians(id), -- 政治家との紐付け
    -- マッチング履歴
    matching_process_id INTEGER,
    matching_confidence DECIMAL(3,2),
    matching_reason TEXT,
    matched_by_user_id UUID REFERENCES users(user_id),
    -- 検証フィールド
    is_manually_verified BOOLEAN DEFAULT FALSE,
    latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 同じ名前、政党、役職の組み合わせは一意とする
    UNIQUE(name, political_party_name, position)
);

-- 発言テーブル
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    minutes_id INTEGER REFERENCES minutes(id), -- どの議事録の発言か
    speaker_id INTEGER REFERENCES speakers(id), -- どの発言者の発言か
    speaker_name VARCHAR, -- 元の発言者名
    comment TEXT NOT NULL, -- 発言内容
    sequence_number INTEGER NOT NULL, -- 議事録内の発言順序
    chapter_number INTEGER, -- 分割した文字列を前から順に割り振った番号
    sub_chapter_number INTEGER, -- 再分割した場合の文字列番号
    -- 検証フィールド
    is_manually_verified BOOLEAN DEFAULT FALSE,
    latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 議員団（会派）関連テーブル
-- =============================================================================

-- 議員団テーブル
CREATE TABLE parliamentary_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    conference_id INT NOT NULL REFERENCES conferences(id),
    url VARCHAR(500),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, conference_id)
);

-- 議員団所属履歴テーブル
CREATE TABLE parliamentary_group_memberships (
    id SERIAL PRIMARY KEY,
    politician_id INT NOT NULL REFERENCES politicians(id),
    parliamentary_group_id INT NOT NULL REFERENCES parliamentary_groups(id),
    start_date DATE NOT NULL,
    end_date DATE,
    role VARCHAR(100), -- 団長、幹事長、政調会長など
    created_by_user_id UUID REFERENCES users(user_id),
    -- 検証フィールド
    is_manually_verified BOOLEAN DEFAULT FALSE,
    latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_end_date_after_start CHECK (end_date IS NULL OR end_date >= start_date)
);

-- =============================================================================
-- 抽出結果テーブル（中間テーブル）
-- =============================================================================

-- 議会メンバー情報の抽出結果
CREATE TABLE extracted_conference_members (
    id SERIAL PRIMARY KEY,
    conference_id INTEGER NOT NULL REFERENCES conferences(id),
    extracted_name VARCHAR(255) NOT NULL,
    extracted_role VARCHAR(100),
    extracted_party_name VARCHAR(255),
    source_url VARCHAR(500) NOT NULL,
    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Matching results
    matched_politician_id INTEGER REFERENCES politicians(id),
    matching_confidence DECIMAL(3,2),
    matching_status VARCHAR(50) DEFAULT 'pending',
    matched_at TIMESTAMP,

    -- Additional extracted data
    additional_info TEXT,

    -- 検証フィールド
    is_manually_verified BOOLEAN DEFAULT FALSE,
    latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 議員団メンバー情報の抽出結果
CREATE TABLE extracted_parliamentary_group_members (
    id SERIAL PRIMARY KEY,
    parliamentary_group_id INTEGER NOT NULL REFERENCES parliamentary_groups(id),
    extracted_name VARCHAR(255) NOT NULL,
    extracted_role VARCHAR(100),
    extracted_party_name VARCHAR(255),
    extracted_district VARCHAR(255),
    source_url VARCHAR(500) NOT NULL,
    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Matching results
    matched_politician_id INTEGER REFERENCES politicians(id),
    matching_confidence DECIMAL(3,2),
    matching_status VARCHAR(50) DEFAULT 'pending',
    matched_at TIMESTAMP,

    -- Additional extracted data
    additional_info TEXT,

    -- ユーザーID
    reviewed_by_user_id UUID REFERENCES users(user_id),

    -- 検証フィールド
    is_manually_verified BOOLEAN DEFAULT FALSE,
    latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- ユニーク制約
    CONSTRAINT unique_parliamentary_group_member UNIQUE (parliamentary_group_id, extracted_name)
);

-- =============================================================================
-- 議案関連テーブル
-- =============================================================================

-- 議案テーブル
-- Note: Alembic migration 003で content → title にリネーム、複数カラム削除
CREATE TABLE proposals (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL, -- 議案タイトル（旧content）
    detail_url VARCHAR, -- 議案の詳細本文URL
    status_url VARCHAR, -- 議案の審議状況URL
    meeting_id INTEGER REFERENCES meetings(id), -- 関連する会議
    votes_url VARCHAR, -- 賛否URL
    conference_id INT REFERENCES conferences(id) ON DELETE SET NULL, -- 会議体
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議案への賛否情報テーブル (誰が議案に賛成したか)
CREATE TABLE proposal_judges (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id), -- どの議案に対する賛否か
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の賛否か
    politician_party_id INTEGER REFERENCES political_parties(id), -- 票決時の所属政党
    approve VARCHAR, -- 例: "賛成", "反対", "棄権", "欠席"
    parliamentary_group_id INTEGER REFERENCES parliamentary_groups(id), -- 賛否投票時の所属議員団
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議案への会派単位の賛否情報テーブル
-- Note: Alembic migration 006でparliamentary_group_id, politician_idカラムを削除しMany-to-Many構造に変更
CREATE TABLE proposal_parliamentary_group_judges (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id),
    judgment VARCHAR(50) NOT NULL, -- 賛成/反対/棄権/欠席
    member_count INTEGER, -- この判断をした会派メンバーの人数
    note TEXT, -- 備考
    judge_type VARCHAR(50) DEFAULT 'parliamentary_group', -- 賛否の種別
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 賛否⇔会派の中間テーブル（Many-to-Many）
CREATE TABLE proposal_judge_parliamentary_groups (
    id SERIAL PRIMARY KEY,
    judge_id INTEGER NOT NULL REFERENCES proposal_parliamentary_group_judges(id) ON DELETE CASCADE,
    parliamentary_group_id INTEGER NOT NULL REFERENCES parliamentary_groups(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(judge_id, parliamentary_group_id)
);

-- 賛否⇔政治家の中間テーブル（Many-to-Many）
CREATE TABLE proposal_judge_politicians (
    id SERIAL PRIMARY KEY,
    judge_id INTEGER NOT NULL REFERENCES proposal_parliamentary_group_judges(id) ON DELETE CASCADE,
    politician_id INTEGER NOT NULL REFERENCES politicians(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(judge_id, politician_id)
);

-- 議案賛否情報の抽出結果
CREATE TABLE extracted_proposal_judges (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id),

    -- Extracted data
    extracted_politician_name VARCHAR(255),
    extracted_party_name VARCHAR(255),
    extracted_parliamentary_group_name VARCHAR(255),
    extracted_judgment VARCHAR(50),
    source_url VARCHAR(500),
    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Matching results
    matched_politician_id INTEGER REFERENCES politicians(id),
    matched_parliamentary_group_id INTEGER REFERENCES parliamentary_groups(id),
    matching_confidence DECIMAL(3,2),
    matching_status VARCHAR(50) DEFAULT 'pending',
    matched_at TIMESTAMP,

    -- Additional data
    additional_data JSONB,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 議案提出者テーブル
CREATE TABLE proposal_submitters (
    id SERIAL PRIMARY KEY,
    proposal_id INT NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    submitter_type VARCHAR(50) NOT NULL,
    politician_id INT REFERENCES politicians(id) ON DELETE SET NULL,
    parliamentary_group_id INT REFERENCES parliamentary_groups(id) ON DELETE SET NULL,
    conference_id INT REFERENCES conferences(id) ON DELETE SET NULL, -- Alembic migration 005
    raw_name VARCHAR(255),
    is_representative BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 操作ログテーブル
-- =============================================================================

-- 政治家操作ログ
CREATE TABLE politician_operation_logs (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL,
    politician_name VARCHAR(255) NOT NULL,
    operation_type VARCHAR(20) NOT NULL,
    user_id UUID REFERENCES users(user_id),
    operation_details JSONB,
    operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_operation_type CHECK (operation_type IN ('create', 'update', 'delete'))
);

-- 議案操作ログ (Alembic migration 004)
CREATE TABLE proposal_operation_logs (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL,
    proposal_title VARCHAR(500) NOT NULL,
    operation_type VARCHAR(20) NOT NULL,
    user_id UUID REFERENCES users(user_id),
    operation_details JSONB,
    operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_proposal_operation_type CHECK (operation_type IN ('create', 'update', 'delete'))
);

-- =============================================================================
-- その他のテーブル
-- =============================================================================

-- 公約テーブル
CREATE TABLE pledges (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の公約か
    title VARCHAR NOT NULL, -- 公約のタイトル
    content TEXT, -- 公約の詳細内容
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 政治家の政党所属履歴テーブル
CREATE TABLE party_membership_history (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の所属履歴か
    political_party_id INTEGER NOT NULL REFERENCES political_parties(id), -- どの政党に所属していたか
    start_date DATE NOT NULL, -- 所属開始日
    end_date DATE, -- 所属終了日 (現所属の場合はNULL)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議員の議会所属情報テーブル
CREATE TABLE politician_affiliations (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の所属情報か
    conference_id INTEGER NOT NULL REFERENCES conferences(id), -- どの会議体に所属しているか
    start_date DATE NOT NULL, -- 所属開始日
    end_date DATE, -- 所属終了日 (現所属の場合はNULL)
    role VARCHAR(100), -- 会議体での役職
    -- 検証フィールド
    is_manually_verified BOOLEAN DEFAULT FALSE,
    latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議案と会議の紐付け情報テーブル（議案の会議経過）
CREATE TABLE proposal_meeting_occurrences (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id), -- どの議案か
    meeting_id INTEGER NOT NULL REFERENCES meetings(id), -- どの会議で扱われたか
    occurrence_type VARCHAR, -- 例: "提出", "審議", "委員会採決", "本会議採決"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 外部キー制約の追加
-- =============================================================================

-- speakers.matching_process_id の外部キー制約
ALTER TABLE speakers
    ADD CONSTRAINT fk_speakers_matching_process
    FOREIGN KEY (matching_process_id)
    REFERENCES llm_processing_history(id)
    ON DELETE SET NULL;

-- =============================================================================
-- インデックスの作成
-- =============================================================================

-- 基本テーブル
CREATE INDEX idx_conferences_governing_body ON conferences(governing_body_id);
CREATE INDEX idx_conferences_prefecture ON conferences(prefecture);
CREATE INDEX idx_meetings_conference ON meetings(conference_id);
CREATE INDEX idx_meetings_gcs_pdf_uri ON meetings(gcs_pdf_uri);
CREATE INDEX idx_meetings_gcs_text_uri ON meetings(gcs_text_uri);
CREATE INDEX idx_minutes_meeting ON minutes(meeting_id);
CREATE INDEX idx_minutes_processed_at ON minutes(processed_at);
CREATE INDEX idx_minutes_llm_process_id ON minutes(llm_process_id);
CREATE INDEX idx_politicians_political_party ON politicians(political_party_id);
CREATE INDEX idx_pledges_politician ON pledges(politician_id);
CREATE INDEX idx_party_membership_politician ON party_membership_history(politician_id);
CREATE INDEX idx_party_membership_party ON party_membership_history(political_party_id);
CREATE INDEX idx_conversations_minutes ON conversations(minutes_id);
CREATE INDEX idx_conversations_speaker ON conversations(speaker_id);
CREATE INDEX idx_conversations_manually_verified ON conversations(is_manually_verified);

-- 発言者テーブル
CREATE INDEX idx_speakers_politician_id ON speakers(politician_id);
CREATE INDEX idx_speakers_matching_process_id ON speakers(matching_process_id);
CREATE INDEX idx_speakers_matched_by_user_id ON speakers(matched_by_user_id);
CREATE INDEX idx_speakers_manually_verified ON speakers(is_manually_verified);

-- 議案関連
CREATE INDEX idx_proposal_judges_proposal ON proposal_judges(proposal_id);
CREATE INDEX idx_proposal_judges_politician ON proposal_judges(politician_id);
CREATE INDEX idx_proposal_judges_parliamentary_group ON proposal_judges(parliamentary_group_id);
CREATE INDEX idx_proposals_meeting ON proposals(meeting_id);
CREATE INDEX idx_proposals_conference_id ON proposals(conference_id);
CREATE INDEX idx_proposals_detail_url ON proposals(detail_url);
CREATE INDEX idx_proposals_status_url ON proposals(status_url);
CREATE INDEX idx_proposal_parliamentary_group_judges_proposal ON proposal_parliamentary_group_judges(proposal_id);
CREATE INDEX idx_proposal_parliamentary_group_judges_judgment ON proposal_parliamentary_group_judges(judgment);
CREATE INDEX idx_pjpg_judge_id ON proposal_judge_parliamentary_groups(judge_id);
CREATE INDEX idx_pjpg_parliamentary_group_id ON proposal_judge_parliamentary_groups(parliamentary_group_id);
CREATE INDEX idx_pjp_judge_id ON proposal_judge_politicians(judge_id);
CREATE INDEX idx_pjp_politician_id ON proposal_judge_politicians(politician_id);
CREATE INDEX idx_proposal_submitters_proposal_id ON proposal_submitters(proposal_id);
CREATE INDEX idx_proposal_submitters_politician_id ON proposal_submitters(politician_id);
CREATE INDEX idx_proposal_submitters_parliamentary_group_id ON proposal_submitters(parliamentary_group_id);
CREATE INDEX idx_proposal_submitters_conference_id ON proposal_submitters(conference_id);
CREATE UNIQUE INDEX idx_proposal_submitters_unique ON proposal_submitters(
    proposal_id,
    COALESCE(politician_id, -1),
    COALESCE(parliamentary_group_id, -1)
);

-- 抽出テーブル
CREATE INDEX idx_extracted_conference_members_conference ON extracted_conference_members(conference_id);
CREATE INDEX idx_extracted_conference_members_status ON extracted_conference_members(matching_status);
CREATE INDEX idx_extracted_conference_members_politician ON extracted_conference_members(matched_politician_id);
CREATE INDEX idx_extracted_conference_members_manually_verified ON extracted_conference_members(is_manually_verified);
CREATE INDEX idx_extracted_parliamentary_group_members_group ON extracted_parliamentary_group_members(parliamentary_group_id);
CREATE INDEX idx_extracted_parliamentary_group_members_status ON extracted_parliamentary_group_members(matching_status);
CREATE INDEX idx_extracted_parliamentary_group_members_politician ON extracted_parliamentary_group_members(matched_politician_id);
CREATE INDEX idx_extracted_parliamentary_group_members_reviewed_by_user_id ON extracted_parliamentary_group_members(reviewed_by_user_id);
CREATE INDEX idx_extracted_parliamentary_group_members_manually_verified ON extracted_parliamentary_group_members(is_manually_verified);
CREATE INDEX idx_extracted_proposal_judges_proposal ON extracted_proposal_judges(proposal_id);
CREATE INDEX idx_extracted_proposal_judges_status ON extracted_proposal_judges(matching_status);
CREATE INDEX idx_extracted_proposal_judges_politician ON extracted_proposal_judges(matched_politician_id);
CREATE INDEX idx_extracted_proposal_judges_group ON extracted_proposal_judges(matched_parliamentary_group_id);
CREATE INDEX idx_extracted_proposal_judges_judgment ON extracted_proposal_judges(extracted_judgment);

-- 議員団関連
CREATE INDEX idx_parliamentary_groups_name_conference ON parliamentary_groups(name, conference_id);
CREATE INDEX idx_parliamentary_group_memberships_politician ON parliamentary_group_memberships(politician_id);
CREATE INDEX idx_parliamentary_group_memberships_group ON parliamentary_group_memberships(parliamentary_group_id);
CREATE INDEX idx_parliamentary_group_memberships_dates ON parliamentary_group_memberships(start_date, end_date);
CREATE INDEX idx_parliamentary_group_memberships_created_by_user_id ON parliamentary_group_memberships(created_by_user_id);
CREATE INDEX idx_parliamentary_group_memberships_manually_verified ON parliamentary_group_memberships(is_manually_verified);

-- 議員の議会所属
CREATE INDEX idx_politician_affiliations_politician ON politician_affiliations(politician_id);
CREATE INDEX idx_politician_affiliations_conference ON politician_affiliations(conference_id);
CREATE INDEX idx_politician_affiliations_role ON politician_affiliations(role);
CREATE INDEX idx_politician_affiliations_manually_verified ON politician_affiliations(is_manually_verified);

-- 議案と会議
CREATE INDEX idx_proposal_meeting_occurrences_proposal ON proposal_meeting_occurrences(proposal_id);
CREATE INDEX idx_proposal_meeting_occurrences_meeting ON proposal_meeting_occurrences(meeting_id);

-- ユーザー
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_last_login_at ON users(last_login_at);

-- LLM処理
CREATE INDEX idx_llm_history_processing_type ON llm_processing_history(processing_type);
CREATE INDEX idx_llm_history_model ON llm_processing_history(model_name, model_version);
CREATE INDEX idx_llm_history_status ON llm_processing_history(status);
CREATE INDEX idx_llm_history_input_ref ON llm_processing_history(input_reference_type, input_reference_id);
CREATE INDEX idx_llm_history_created_at ON llm_processing_history(created_at);
CREATE INDEX idx_llm_history_started_at ON llm_processing_history(started_at);
CREATE INDEX idx_llm_history_created_by ON llm_processing_history(created_by);

-- プロンプトバージョン
CREATE INDEX idx_prompt_versions_key ON prompt_versions(prompt_key);
CREATE INDEX idx_prompt_versions_active ON prompt_versions(prompt_key, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_prompt_versions_created_at ON prompt_versions(created_at);

-- 抽出ログ
CREATE INDEX idx_extraction_logs_entity ON extraction_logs(entity_type, entity_id);
CREATE INDEX idx_extraction_logs_pipeline ON extraction_logs(pipeline_version);
CREATE INDEX idx_extraction_logs_created_at ON extraction_logs(created_at DESC);
CREATE INDEX idx_extraction_logs_entity_type ON extraction_logs(entity_type);
CREATE INDEX idx_extraction_logs_confidence ON extraction_logs(confidence_score);

-- 操作ログ
CREATE INDEX idx_politician_operation_logs_user_id ON politician_operation_logs(user_id);
CREATE INDEX idx_politician_operation_logs_operated_at ON politician_operation_logs(operated_at DESC);
CREATE INDEX idx_politician_operation_logs_operation_type ON politician_operation_logs(operation_type);
CREATE INDEX idx_politician_operation_logs_politician_id ON politician_operation_logs(politician_id);
CREATE INDEX idx_proposal_operation_logs_user_id ON proposal_operation_logs(user_id);
CREATE INDEX idx_proposal_operation_logs_operated_at ON proposal_operation_logs(operated_at DESC);
CREATE INDEX idx_proposal_operation_logs_operation_type ON proposal_operation_logs(operation_type);
CREATE INDEX idx_proposal_operation_logs_proposal_id ON proposal_operation_logs(proposal_id);

-- =============================================================================
-- トリガー関数
-- =============================================================================

-- updated_atカラムを自動更新するトリガー関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 単一アクティブバージョン確保関数
CREATE OR REPLACE FUNCTION ensure_single_active_prompt_version()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = TRUE THEN
        UPDATE prompt_versions
        SET is_active = FALSE
        WHERE prompt_key = NEW.prompt_key
          AND id != NEW.id
          AND is_active = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- トリガーの作成
-- =============================================================================

-- 基本テーブル
CREATE TRIGGER update_governing_bodies_updated_at BEFORE UPDATE ON governing_bodies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conferences_updated_at BEFORE UPDATE ON conferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_meetings_updated_at BEFORE UPDATE ON meetings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_minutes_updated_at BEFORE UPDATE ON minutes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_speakers_updated_at BEFORE UPDATE ON speakers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_political_parties_updated_at BEFORE UPDATE ON political_parties FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_politicians_updated_at BEFORE UPDATE ON politicians FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pledges_updated_at BEFORE UPDATE ON pledges FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_party_membership_history_updated_at BEFORE UPDATE ON party_membership_history FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proposals_updated_at BEFORE UPDATE ON proposals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proposal_judges_updated_at BEFORE UPDATE ON proposal_judges FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_politician_affiliations_updated_at BEFORE UPDATE ON politician_affiliations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proposal_meeting_occurrences_updated_at BEFORE UPDATE ON proposal_meeting_occurrences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_parliamentary_groups_updated_at BEFORE UPDATE ON parliamentary_groups FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_parliamentary_group_memberships_updated_at BEFORE UPDATE ON parliamentary_group_memberships FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- LLM処理関連
CREATE TRIGGER trigger_update_llm_processing_history_updated_at BEFORE UPDATE ON llm_processing_history FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_update_prompt_versions_updated_at BEFORE UPDATE ON prompt_versions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_ensure_single_active_prompt_version BEFORE INSERT OR UPDATE ON prompt_versions FOR EACH ROW WHEN (NEW.is_active = TRUE) EXECUTE FUNCTION ensure_single_active_prompt_version();
CREATE TRIGGER trigger_update_extraction_logs_updated_at BEFORE UPDATE ON extraction_logs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- テーブルコメント
-- =============================================================================

COMMENT ON TABLE governing_bodies IS '開催主体';
COMMENT ON COLUMN governing_bodies.organization_code IS '総務省の6桁地方自治体コード';
COMMENT ON COLUMN governing_bodies.organization_type IS '詳細な組織種別（都道府県、市、区、町、村など）';

COMMENT ON TABLE conferences IS '会議体 (議会や委員会など)';
COMMENT ON COLUMN conferences.governing_body_id IS 'Optional reference to governing body. NULL means the conference is not associated with any governing body.';
COMMENT ON COLUMN conferences.members_introduction_url IS 'URL where the council members of this conference are introduced';
COMMENT ON COLUMN conferences.prefecture IS '都道府県（全国は国会を表す）';

COMMENT ON TABLE meetings IS '会議 (具体的な開催インスタンス)';
COMMENT ON COLUMN meetings.url IS '会議関連のURLまたは議事録PDFのURL';
COMMENT ON COLUMN meetings.gcs_pdf_uri IS 'Google Cloud Storage URI for the PDF file';
COMMENT ON COLUMN meetings.gcs_text_uri IS 'Google Cloud Storage URI for the extracted text file';
COMMENT ON COLUMN meetings.attendees_mapping IS '出席者の役職と名前のマッピング';

COMMENT ON TABLE minutes IS '議事録';
COMMENT ON COLUMN minutes.llm_process_id IS 'LLM処理履歴との関連付けID';
COMMENT ON COLUMN minutes.role_name_mappings IS '議事録冒頭の出席者情報から抽出した役職-人名マッピング';

COMMENT ON TABLE speakers IS '発言者';
COMMENT ON COLUMN speakers.politician_id IS 'Reference to the politician this speaker represents. Multiple speakers can point to the same politician.';
COMMENT ON COLUMN speakers.matching_process_id IS 'LLM処理履歴のID（speaker_matchingプロセス）';
COMMENT ON COLUMN speakers.matching_confidence IS 'マッチングの信頼度スコア (0.00-1.00)';
COMMENT ON COLUMN speakers.matching_reason IS 'マッチング判定の理由';
COMMENT ON COLUMN speakers.matched_by_user_id IS '発言者と政治家の紐付けを実行したユーザーID';
COMMENT ON COLUMN speakers.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN speakers.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。';

COMMENT ON TABLE political_parties IS '政党';
COMMENT ON COLUMN political_parties.members_list_url IS '議員一覧ページのURL';

COMMENT ON TABLE politicians IS '政治家';
COMMENT ON COLUMN politicians.furigana IS 'Name reading in hiragana';
COMMENT ON COLUMN politicians.district IS 'Electoral district';
COMMENT ON COLUMN politicians.profile_page_url IS 'URL to profile page on party or government website';

COMMENT ON TABLE pledges IS '公約';
COMMENT ON TABLE party_membership_history IS '政治家の政党所属履歴';
COMMENT ON TABLE conversations IS '発言';
COMMENT ON COLUMN conversations.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN conversations.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。';

COMMENT ON TABLE proposals IS '議案';
COMMENT ON COLUMN proposals.title IS '議案タイトル';
COMMENT ON COLUMN proposals.detail_url IS '議案の詳細本文URL';
COMMENT ON COLUMN proposals.status_url IS '議案の審議状況URL';
COMMENT ON COLUMN proposals.votes_url IS '賛否URL';

COMMENT ON TABLE proposal_judges IS '議案への賛否情報 (誰が議案に賛成したか)';
COMMENT ON COLUMN proposal_judges.parliamentary_group_id IS '賛否投票時の所属議員団ID';

COMMENT ON TABLE politician_affiliations IS '議員の議会所属情報';
COMMENT ON COLUMN politician_affiliations.role IS '会議体での役職（議長、副議長、委員長など）';
COMMENT ON COLUMN politician_affiliations.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN politician_affiliations.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。';

COMMENT ON TABLE proposal_meeting_occurrences IS '議案と会議の紐付け情報（議案の会議経過）';

COMMENT ON TABLE parliamentary_groups IS '議員団（会派）';
COMMENT ON COLUMN parliamentary_groups.name IS '議員団名';
COMMENT ON COLUMN parliamentary_groups.conference_id IS '所属する会議体ID';
COMMENT ON COLUMN parliamentary_groups.url IS '議員団の公式URL';
COMMENT ON COLUMN parliamentary_groups.description IS '議員団の説明';
COMMENT ON COLUMN parliamentary_groups.is_active IS '現在活動中かどうか';

COMMENT ON TABLE parliamentary_group_memberships IS '議員団所属履歴';
COMMENT ON COLUMN parliamentary_group_memberships.politician_id IS '政治家ID';
COMMENT ON COLUMN parliamentary_group_memberships.parliamentary_group_id IS '議員団ID';
COMMENT ON COLUMN parliamentary_group_memberships.start_date IS '所属開始日';
COMMENT ON COLUMN parliamentary_group_memberships.end_date IS '所属終了日（現在所属中の場合はNULL）';
COMMENT ON COLUMN parliamentary_group_memberships.role IS '議員団内での役職';
COMMENT ON COLUMN parliamentary_group_memberships.created_by_user_id IS '議員団メンバーを作成したユーザーID';
COMMENT ON COLUMN parliamentary_group_memberships.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN parliamentary_group_memberships.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。';

COMMENT ON TABLE extracted_conference_members IS '議会メンバー情報の抽出結果を保存する中間テーブル';
COMMENT ON COLUMN extracted_conference_members.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN extracted_conference_members.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。';

COMMENT ON TABLE extracted_parliamentary_group_members IS '議員団メンバー情報の抽出結果を保存する中間テーブル';
COMMENT ON COLUMN extracted_parliamentary_group_members.reviewed_by_user_id IS 'レビューを実行したユーザーID';
COMMENT ON COLUMN extracted_parliamentary_group_members.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN extracted_parliamentary_group_members.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。';
COMMENT ON CONSTRAINT unique_parliamentary_group_member ON extracted_parliamentary_group_members IS '同じ議員団内で同じ名前の議員が重複して登録されることを防ぐ制約';

COMMENT ON TABLE extracted_proposal_judges IS '議案賛否情報の抽出結果を保存する中間テーブル';

COMMENT ON TABLE proposal_parliamentary_group_judges IS '議案への会派単位の賛否情報';
COMMENT ON COLUMN proposal_parliamentary_group_judges.judge_type IS '賛否の種別（parliamentary_group: 会派単位, politician: 政治家単位）';

COMMENT ON TABLE proposal_judge_parliamentary_groups IS '賛否レコードと会派の中間テーブル（Many-to-Many）';
COMMENT ON TABLE proposal_judge_politicians IS '賛否レコードと政治家の中間テーブル（Many-to-Many）';

COMMENT ON TABLE proposal_submitters IS '議案提出者テーブル（連名提出対応）';
COMMENT ON COLUMN proposal_submitters.conference_id IS '会議体が提出者の場合のConference ID';

COMMENT ON TABLE users IS 'ログインユーザーを管理するテーブル';
COMMENT ON COLUMN users.user_id IS 'ユーザーID（UUID）';
COMMENT ON COLUMN users.email IS 'メールアドレス（一意）';
COMMENT ON COLUMN users.name IS 'ユーザーの表示名';
COMMENT ON COLUMN users.picture IS 'プロフィール画像のURL';
COMMENT ON COLUMN users.created_at IS 'ユーザー作成日時';
COMMENT ON COLUMN users.last_login_at IS '最終ログイン日時';

COMMENT ON TABLE llm_processing_history IS 'LLM処理の履歴を記録するテーブル';
COMMENT ON COLUMN llm_processing_history.processing_type IS '処理タイプ（minutes_division, speaker_matching等）';
COMMENT ON COLUMN llm_processing_history.model_name IS '使用したLLMモデル名';
COMMENT ON COLUMN llm_processing_history.model_version IS 'モデルのバージョン';
COMMENT ON COLUMN llm_processing_history.prompt_template IS '使用したプロンプトテンプレート';
COMMENT ON COLUMN llm_processing_history.prompt_variables IS 'プロンプトに代入された変数のJSON';
COMMENT ON COLUMN llm_processing_history.input_reference_type IS '処理対象のエンティティタイプ';
COMMENT ON COLUMN llm_processing_history.input_reference_id IS '処理対象のエンティティID';
COMMENT ON COLUMN llm_processing_history.status IS '処理ステータス（pending, in_progress, completed, failed）';
COMMENT ON COLUMN llm_processing_history.result IS '処理結果のJSON';
COMMENT ON COLUMN llm_processing_history.error_message IS 'エラーメッセージ（失敗時）';
COMMENT ON COLUMN llm_processing_history.processing_metadata IS '追加のメタデータ';
COMMENT ON COLUMN llm_processing_history.created_by IS '処理を開始したユーザーまたはシステム';
COMMENT ON COLUMN llm_processing_history.started_at IS '処理開始時刻';
COMMENT ON COLUMN llm_processing_history.completed_at IS '処理完了時刻';

COMMENT ON TABLE prompt_versions IS 'プロンプトテンプレートのバージョン管理テーブル';
COMMENT ON COLUMN prompt_versions.prompt_key IS 'プロンプトの識別キー';
COMMENT ON COLUMN prompt_versions.version IS 'バージョン番号';
COMMENT ON COLUMN prompt_versions.template IS 'プロンプトテンプレートの内容';
COMMENT ON COLUMN prompt_versions.description IS 'このバージョンの説明';
COMMENT ON COLUMN prompt_versions.is_active IS '現在アクティブなバージョンかどうか';
COMMENT ON COLUMN prompt_versions.variables IS 'テンプレート内で使用される変数名のリスト';
COMMENT ON COLUMN prompt_versions.prompt_metadata IS '追加のメタデータ';
COMMENT ON COLUMN prompt_versions.created_by IS 'このバージョンを作成したユーザーまたはシステム';

COMMENT ON TABLE extraction_logs IS 'LLM抽出結果の履歴を記録するテーブル（全エンティティタイプ対応）';
COMMENT ON COLUMN extraction_logs.entity_type IS '抽出対象のエンティティタイプ';
COMMENT ON COLUMN extraction_logs.entity_id IS '抽出対象のエンティティID';
COMMENT ON COLUMN extraction_logs.pipeline_version IS 'パイプラインのバージョン';
COMMENT ON COLUMN extraction_logs.extracted_data IS 'LLMが出力した生データ（JSON形式）';
COMMENT ON COLUMN extraction_logs.confidence_score IS '抽出の信頼度スコア（0.0〜1.0）';
COMMENT ON COLUMN extraction_logs.extraction_metadata IS '抽出に関する追加メタデータ';

COMMENT ON TABLE politician_operation_logs IS '政治家操作ログ（作成・更新・削除の履歴）';
COMMENT ON COLUMN politician_operation_logs.politician_id IS '操作対象の政治家ID';
COMMENT ON COLUMN politician_operation_logs.politician_name IS '操作時点の政治家名';
COMMENT ON COLUMN politician_operation_logs.operation_type IS '操作種別（create: 作成, update: 更新, delete: 削除）';
COMMENT ON COLUMN politician_operation_logs.user_id IS '操作を行ったユーザーID';
COMMENT ON COLUMN politician_operation_logs.operation_details IS '操作の詳細（JSONフォーマット）';
COMMENT ON COLUMN politician_operation_logs.operated_at IS '操作日時';

COMMENT ON TABLE proposal_operation_logs IS '議案操作ログ（作成・更新・削除の履歴）';
COMMENT ON COLUMN proposal_operation_logs.proposal_id IS '操作対象の議案ID';
COMMENT ON COLUMN proposal_operation_logs.proposal_title IS '操作時点の議案タイトル';
COMMENT ON COLUMN proposal_operation_logs.operation_type IS '操作種別（create: 作成, update: 更新, delete: 削除）';
COMMENT ON COLUMN proposal_operation_logs.user_id IS '操作を行ったユーザーID';
COMMENT ON COLUMN proposal_operation_logs.operation_details IS '操作の詳細（JSONフォーマット）';
COMMENT ON COLUMN proposal_operation_logs.operated_at IS '操作日時';
