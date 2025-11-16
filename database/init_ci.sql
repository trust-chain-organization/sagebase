-- Database Schema for Political Activity Tracking Application
-- Generated from polibase.dbml

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 開催主体テーブル
CREATE TABLE governing_bodies (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    type VARCHAR, -- 例: "国", "都道府県", "市町村"
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
    governing_body_id INTEGER NOT NULL REFERENCES governing_bodies(id),
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議事録テーブル
CREATE TABLE minutes (
    id SERIAL PRIMARY KEY,
    url VARCHAR, -- 議事録PDFなどのURL
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 発言者テーブル
CREATE TABLE speakers (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL, -- 発言者名
    type VARCHAR, -- 例: "政治家", "参考人", "議長", "政府職員"
    political_party_name VARCHAR, -- 所属政党名（政治家の場合）
    position VARCHAR, -- 役職・肩書き
    is_politician BOOLEAN DEFAULT FALSE, -- 政治家かどうか
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 同じ名前、政党、役職の組み合わせは一意とする
    UNIQUE(name, political_party_name, position)
);

-- 政党テーブル
CREATE TABLE political_parties (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE, -- 政党名 (重複なし)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 政治家テーブル
CREATE TABLE politicians (
    id SERIAL PRIMARY KEY, -- 政治家固有のID
    name VARCHAR NOT NULL, -- 政治家名
    political_party_id INTEGER REFERENCES political_parties(id), -- 現在の主要所属政党
    furigana VARCHAR, -- 名前の読み（ひらがな）
    district VARCHAR, -- 選挙区
    profile_page_url VARCHAR, -- プロフィールページURL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- speakers テーブルにpolitician_idを追加 (多対1の関係: 複数のspeakerが1人の政治家を指す)
ALTER TABLE speakers ADD COLUMN politician_id INTEGER REFERENCES politicians(id);
CREATE INDEX idx_speakers_politician_id ON speakers(politician_id);
COMMENT ON COLUMN speakers.politician_id IS 'Reference to the politician this speaker represents. Multiple speakers can point to the same politician.';

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

-- 発言テーブル
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    minutes_id INTEGER REFERENCES minutes(id), -- どの議事録の発言か（NULL許可で仮の議事録なしでも保存可能）
    speaker_id INTEGER REFERENCES speakers(id), -- どの発言者の発言か（NULL許可で発言者が特定できない場合）
    speaker_name VARCHAR, -- 元の発言者名（名前の完全一致ができない場合のための保管用）
    comment TEXT NOT NULL, -- 発言内容
    sequence_number INTEGER NOT NULL, -- 議事録内の発言順序
    chapter_number INTEGER, -- 分割した文字列を前から順に割り振った番号
    sub_chapter_number INTEGER, -- 再分割した場合の文字列番号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議案テーブル
CREATE TABLE proposals (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL, -- 議案内容
    status VARCHAR, -- 例: "審議中", "可決", "否決"
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議員の議会所属情報テーブル
CREATE TABLE politician_affiliations (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の所属情報か
    conference_id INTEGER NOT NULL REFERENCES conferences(id), -- どの会議体（議会・委員会）に所属しているか
    start_date DATE NOT NULL, -- 所属開始日
    end_date DATE, -- 所属終了日 (現所属の場合はNULL)
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

-- ユーザーテーブル (ログインユーザー管理)
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- インデックスの作成
CREATE INDEX idx_conferences_governing_body ON conferences(governing_body_id);
CREATE INDEX idx_meetings_conference ON meetings(conference_id);
CREATE INDEX idx_minutes_meeting ON minutes(meeting_id);
CREATE INDEX idx_politicians_political_party ON politicians(political_party_id);
CREATE INDEX idx_pledges_politician ON pledges(politician_id);
CREATE INDEX idx_party_membership_politician ON party_membership_history(politician_id);
CREATE INDEX idx_party_membership_party ON party_membership_history(political_party_id);
CREATE INDEX idx_conversations_minutes ON conversations(minutes_id);
CREATE INDEX idx_conversations_speaker ON conversations(speaker_id);
CREATE INDEX idx_proposal_judges_proposal ON proposal_judges(proposal_id);
CREATE INDEX idx_proposal_judges_politician ON proposal_judges(politician_id);
CREATE INDEX idx_politician_affiliations_politician ON politician_affiliations(politician_id);
CREATE INDEX idx_politician_affiliations_conference ON politician_affiliations(conference_id);
CREATE INDEX idx_proposal_meeting_occurrences_proposal ON proposal_meeting_occurrences(proposal_id);
CREATE INDEX idx_proposal_meeting_occurrences_meeting ON proposal_meeting_occurrences(meeting_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_last_login_at ON users(last_login_at);

-- トリガー関数：updated_atカラムを自動更新
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 各テーブルにupdated_atトリガーを設定
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

-- SEEDデータの読み込みはPostgreSQL起動後に実行する

COMMENT ON TABLE governing_bodies IS '開催主体';
COMMENT ON TABLE conferences IS '会議体 (議会や委員会など)';
COMMENT ON TABLE meetings IS '会議 (具体的な開催インスタンス)';
COMMENT ON TABLE minutes IS '議事録';
COMMENT ON TABLE speakers IS '発言者';
COMMENT ON TABLE political_parties IS '政党';
COMMENT ON TABLE politicians IS '政治家';
COMMENT ON TABLE pledges IS '公約';
COMMENT ON TABLE party_membership_history IS '政治家の政党所属履歴';
COMMENT ON TABLE conversations IS '発言';
COMMENT ON TABLE proposals IS '議案';
COMMENT ON TABLE proposal_judges IS '議案への賛否情報 (誰が議案に賛成したか)';
COMMENT ON TABLE politician_affiliations IS '議員の議会所属情報';
COMMENT ON TABLE proposal_meeting_occurrences IS '議案と会議の紐付け情報（議案の会議経過）';
