"""Baseline migration: Complete database schema.

このマイグレーションは完全なデータベーススキーマを作成します。
Alembicが唯一のスキーマ定義源（Single Source of Truth）となります。

前提条件:
- init.sql で extensions と enum型 が作成済み

Revision ID: 001
Revises:
Create Date: 2025-01-20
Updated: 2026-01-28 (ADR 0006 - Alembic完全統一)
"""

from alembic import op


revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all database tables, indexes, triggers, and comments."""
    # ==========================================================================
    # 基本テーブル
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS governing_bodies (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            type VARCHAR,
            organization_code CHAR(6) UNIQUE,
            organization_type VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, type)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS conferences (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            type VARCHAR,
            governing_body_id INTEGER REFERENCES governing_bodies(id),
            members_introduction_url VARCHAR(255),
            prefecture VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, governing_body_id)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id SERIAL PRIMARY KEY,
            conference_id INTEGER NOT NULL REFERENCES conferences(id),
            date DATE,
            url VARCHAR,
            name VARCHAR,
            gcs_pdf_uri VARCHAR(512),
            gcs_text_uri VARCHAR(512),
            attendees_mapping JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS minutes (
            id SERIAL PRIMARY KEY,
            url VARCHAR,
            meeting_id INTEGER NOT NULL REFERENCES meetings(id),
            processed_at TIMESTAMP,
            llm_process_id VARCHAR(100),
            role_name_mappings JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS political_parties (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL UNIQUE,
            members_list_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS politicians (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            political_party_id INTEGER REFERENCES political_parties(id),
            prefecture VARCHAR(10),
            furigana VARCHAR,
            district VARCHAR,
            profile_page_url VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ==========================================================================
    # ユーザー管理テーブル
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            picture TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ==========================================================================
    # LLM処理関連テーブル
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS llm_processing_history (
            id SERIAL PRIMARY KEY,
            processing_type VARCHAR(50) NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            model_version VARCHAR(50) NOT NULL,
            prompt_template TEXT NOT NULL,
            prompt_variables JSONB NOT NULL DEFAULT '{}',
            input_reference_type VARCHAR(50) NOT NULL,
            input_reference_id INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            result JSONB,
            error_message TEXT,
            processing_metadata JSONB NOT NULL DEFAULT '{}',
            created_by VARCHAR(100) DEFAULT 'system',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prompt_versions (
            id SERIAL PRIMARY KEY,
            prompt_key VARCHAR(100) NOT NULL,
            version VARCHAR(50) NOT NULL,
            template TEXT NOT NULL,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            variables TEXT[],
            prompt_metadata JSONB NOT NULL DEFAULT '{}',
            created_by VARCHAR(100),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uk_prompt_version UNIQUE (prompt_key, version)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS extraction_logs (
            id SERIAL PRIMARY KEY,
            entity_type entity_type NOT NULL,
            entity_id INTEGER NOT NULL,
            pipeline_version VARCHAR(100) NOT NULL,
            extracted_data JSONB NOT NULL,
            confidence_score FLOAT,
            extraction_metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ==========================================================================
    # 発言者・発言関連テーブル
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS speakers (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            type VARCHAR,
            political_party_name VARCHAR,
            position VARCHAR,
            is_politician BOOLEAN DEFAULT FALSE,
            politician_id INTEGER REFERENCES politicians(id),
            matching_process_id INTEGER,
            matching_confidence DECIMAL(3,2),
            matching_reason TEXT,
            matched_by_user_id UUID REFERENCES users(user_id),
            is_manually_verified BOOLEAN DEFAULT FALSE,
            latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, political_party_name, position)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            minutes_id INTEGER REFERENCES minutes(id),
            speaker_id INTEGER REFERENCES speakers(id),
            speaker_name VARCHAR,
            comment TEXT NOT NULL,
            sequence_number INTEGER NOT NULL,
            chapter_number INTEGER,
            sub_chapter_number INTEGER,
            is_manually_verified BOOLEAN DEFAULT FALSE,
            latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ==========================================================================
    # 議員団（会派）関連テーブル
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS parliamentary_groups (
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
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS parliamentary_group_memberships (
            id SERIAL PRIMARY KEY,
            politician_id INT NOT NULL REFERENCES politicians(id),
            parliamentary_group_id INT NOT NULL REFERENCES parliamentary_groups(id),
            start_date DATE NOT NULL,
            end_date DATE,
            role VARCHAR(100),
            created_by_user_id UUID REFERENCES users(user_id),
            is_manually_verified BOOLEAN DEFAULT FALSE,
            latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_end_date_after_start CHECK (end_date IS NULL OR end_date >= start_date)
        );
    """)

    # ==========================================================================
    # 抽出結果テーブル（中間テーブル）
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS extracted_conference_members (
            id SERIAL PRIMARY KEY,
            conference_id INTEGER NOT NULL REFERENCES conferences(id),
            extracted_name VARCHAR(255) NOT NULL,
            extracted_role VARCHAR(100),
            extracted_party_name VARCHAR(255),
            source_url VARCHAR(500) NOT NULL,
            extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            matched_politician_id INTEGER REFERENCES politicians(id),
            matching_confidence DECIMAL(3,2),
            matching_status VARCHAR(50) DEFAULT 'pending',
            matched_at TIMESTAMP,
            additional_info TEXT,
            is_manually_verified BOOLEAN DEFAULT FALSE,
            latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS extracted_parliamentary_group_members (
            id SERIAL PRIMARY KEY,
            parliamentary_group_id INTEGER NOT NULL REFERENCES parliamentary_groups(id),
            extracted_name VARCHAR(255) NOT NULL,
            extracted_role VARCHAR(100),
            extracted_party_name VARCHAR(255),
            extracted_district VARCHAR(255),
            source_url VARCHAR(500) NOT NULL,
            extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            matched_politician_id INTEGER REFERENCES politicians(id),
            matching_confidence DECIMAL(3,2),
            matching_status VARCHAR(50) DEFAULT 'pending',
            matched_at TIMESTAMP,
            additional_info TEXT,
            reviewed_by_user_id UUID REFERENCES users(user_id),
            is_manually_verified BOOLEAN DEFAULT FALSE,
            latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_parliamentary_group_member UNIQUE (parliamentary_group_id, extracted_name)
        );
    """)

    # ==========================================================================
    # 議案関連テーブル
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS proposals (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            detail_url VARCHAR,
            status_url VARCHAR,
            meeting_id INTEGER REFERENCES meetings(id),
            votes_url VARCHAR,
            conference_id INT REFERENCES conferences(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_judges (
            id SERIAL PRIMARY KEY,
            proposal_id INTEGER NOT NULL REFERENCES proposals(id),
            politician_id INTEGER NOT NULL REFERENCES politicians(id),
            politician_party_id INTEGER REFERENCES political_parties(id),
            approve VARCHAR,
            parliamentary_group_id INTEGER REFERENCES parliamentary_groups(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_parliamentary_group_judges (
            id SERIAL PRIMARY KEY,
            proposal_id INTEGER NOT NULL REFERENCES proposals(id),
            judgment VARCHAR(50) NOT NULL,
            member_count INTEGER,
            note TEXT,
            judge_type VARCHAR(50) DEFAULT 'parliamentary_group',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_judge_parliamentary_groups (
            id SERIAL PRIMARY KEY,
            judge_id INTEGER NOT NULL REFERENCES proposal_parliamentary_group_judges(id) ON DELETE CASCADE,
            parliamentary_group_id INTEGER NOT NULL REFERENCES parliamentary_groups(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(judge_id, parliamentary_group_id)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_judge_politicians (
            id SERIAL PRIMARY KEY,
            judge_id INTEGER NOT NULL REFERENCES proposal_parliamentary_group_judges(id) ON DELETE CASCADE,
            politician_id INTEGER NOT NULL REFERENCES politicians(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(judge_id, politician_id)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS extracted_proposal_judges (
            id SERIAL PRIMARY KEY,
            proposal_id INTEGER NOT NULL REFERENCES proposals(id),
            extracted_politician_name VARCHAR(255),
            extracted_party_name VARCHAR(255),
            extracted_parliamentary_group_name VARCHAR(255),
            extracted_judgment VARCHAR(50),
            source_url VARCHAR(500),
            extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            matched_politician_id INTEGER REFERENCES politicians(id),
            matched_parliamentary_group_id INTEGER REFERENCES parliamentary_groups(id),
            matching_confidence DECIMAL(3,2),
            matching_status VARCHAR(50) DEFAULT 'pending',
            matched_at TIMESTAMP,
            additional_data JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_submitters (
            id SERIAL PRIMARY KEY,
            proposal_id INT NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
            submitter_type VARCHAR(50) NOT NULL,
            politician_id INT REFERENCES politicians(id) ON DELETE SET NULL,
            parliamentary_group_id INT REFERENCES parliamentary_groups(id) ON DELETE SET NULL,
            conference_id INT REFERENCES conferences(id) ON DELETE SET NULL,
            raw_name VARCHAR(255),
            is_representative BOOLEAN DEFAULT FALSE,
            display_order INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ==========================================================================
    # 操作ログテーブル
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS politician_operation_logs (
            id SERIAL PRIMARY KEY,
            politician_id INTEGER NOT NULL,
            politician_name VARCHAR(255) NOT NULL,
            operation_type VARCHAR(20) NOT NULL,
            user_id UUID REFERENCES users(user_id),
            operation_details JSONB,
            operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT check_operation_type CHECK (operation_type IN ('create', 'update', 'delete'))
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_operation_logs (
            id SERIAL PRIMARY KEY,
            proposal_id INTEGER NOT NULL,
            proposal_title VARCHAR(500) NOT NULL,
            operation_type VARCHAR(20) NOT NULL,
            user_id UUID REFERENCES users(user_id),
            operation_details JSONB,
            operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT check_proposal_operation_type CHECK (operation_type IN ('create', 'update', 'delete'))
        );
    """)

    # ==========================================================================
    # その他のテーブル
    # ==========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS pledges (
            id SERIAL PRIMARY KEY,
            politician_id INTEGER NOT NULL REFERENCES politicians(id),
            title VARCHAR NOT NULL,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS party_membership_history (
            id SERIAL PRIMARY KEY,
            politician_id INTEGER NOT NULL REFERENCES politicians(id),
            political_party_id INTEGER NOT NULL REFERENCES political_parties(id),
            start_date DATE NOT NULL,
            end_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS politician_affiliations (
            id SERIAL PRIMARY KEY,
            politician_id INTEGER NOT NULL REFERENCES politicians(id),
            conference_id INTEGER NOT NULL REFERENCES conferences(id),
            start_date DATE NOT NULL,
            end_date DATE,
            role VARCHAR(100),
            is_manually_verified BOOLEAN DEFAULT FALSE,
            latest_extraction_log_id INTEGER REFERENCES extraction_logs(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS proposal_meeting_occurrences (
            id SERIAL PRIMARY KEY,
            proposal_id INTEGER NOT NULL REFERENCES proposals(id),
            meeting_id INTEGER NOT NULL REFERENCES meetings(id),
            occurrence_type VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ==========================================================================
    # 外部キー制約の追加
    # ==========================================================================
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_speakers_matching_process'
            ) THEN
                ALTER TABLE speakers
                ADD CONSTRAINT fk_speakers_matching_process
                FOREIGN KEY (matching_process_id)
                REFERENCES llm_processing_history(id)
                ON DELETE SET NULL;
            END IF;
        END$$;
    """)

    # ==========================================================================
    # インデックスの作成
    # ==========================================================================
    _create_indexes()

    # ==========================================================================
    # トリガー関数とトリガーの作成
    # ==========================================================================
    _create_triggers()

    # ==========================================================================
    # テーブルコメント
    # ==========================================================================
    _create_comments()


def _create_indexes() -> None:
    """Create all database indexes."""
    indexes = [
        # 基本テーブル
        "CREATE INDEX IF NOT EXISTS idx_conferences_governing_body ON conferences(governing_body_id)",
        "CREATE INDEX IF NOT EXISTS idx_conferences_prefecture ON conferences(prefecture)",
        "CREATE INDEX IF NOT EXISTS idx_meetings_conference ON meetings(conference_id)",
        "CREATE INDEX IF NOT EXISTS idx_meetings_gcs_pdf_uri ON meetings(gcs_pdf_uri)",
        "CREATE INDEX IF NOT EXISTS idx_meetings_gcs_text_uri ON meetings(gcs_text_uri)",
        "CREATE INDEX IF NOT EXISTS idx_minutes_meeting ON minutes(meeting_id)",
        "CREATE INDEX IF NOT EXISTS idx_minutes_processed_at ON minutes(processed_at)",
        "CREATE INDEX IF NOT EXISTS idx_minutes_llm_process_id ON minutes(llm_process_id)",
        "CREATE INDEX IF NOT EXISTS idx_politicians_political_party ON politicians(political_party_id)",
        "CREATE INDEX IF NOT EXISTS idx_pledges_politician ON pledges(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_party_membership_politician ON party_membership_history(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_party_membership_party ON party_membership_history(political_party_id)",
        "CREATE INDEX IF NOT EXISTS idx_conversations_minutes ON conversations(minutes_id)",
        "CREATE INDEX IF NOT EXISTS idx_conversations_speaker ON conversations(speaker_id)",
        "CREATE INDEX IF NOT EXISTS idx_conversations_manually_verified ON conversations(is_manually_verified)",
        # 発言者テーブル
        "CREATE INDEX IF NOT EXISTS idx_speakers_politician_id ON speakers(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_speakers_matching_process_id ON speakers(matching_process_id)",
        "CREATE INDEX IF NOT EXISTS idx_speakers_matched_by_user_id ON speakers(matched_by_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_speakers_manually_verified ON speakers(is_manually_verified)",
        # 議案関連
        "CREATE INDEX IF NOT EXISTS idx_proposal_judges_proposal ON proposal_judges(proposal_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_judges_politician ON proposal_judges(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_judges_parliamentary_group ON proposal_judges(parliamentary_group_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposals_meeting ON proposals(meeting_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposals_conference_id ON proposals(conference_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposals_detail_url ON proposals(detail_url)",
        "CREATE INDEX IF NOT EXISTS idx_proposals_status_url ON proposals(status_url)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_parliamentary_group_judges_proposal ON proposal_parliamentary_group_judges(proposal_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_parliamentary_group_judges_judgment ON proposal_parliamentary_group_judges(judgment)",
        "CREATE INDEX IF NOT EXISTS idx_pjpg_judge_id ON proposal_judge_parliamentary_groups(judge_id)",
        "CREATE INDEX IF NOT EXISTS idx_pjpg_parliamentary_group_id ON proposal_judge_parliamentary_groups(parliamentary_group_id)",
        "CREATE INDEX IF NOT EXISTS idx_pjp_judge_id ON proposal_judge_politicians(judge_id)",
        "CREATE INDEX IF NOT EXISTS idx_pjp_politician_id ON proposal_judge_politicians(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_submitters_proposal_id ON proposal_submitters(proposal_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_submitters_politician_id ON proposal_submitters(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_submitters_parliamentary_group_id ON proposal_submitters(parliamentary_group_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_submitters_conference_id ON proposal_submitters(conference_id)",
        # 抽出テーブル
        "CREATE INDEX IF NOT EXISTS idx_extracted_conference_members_conference ON extracted_conference_members(conference_id)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_conference_members_status ON extracted_conference_members(matching_status)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_conference_members_politician ON extracted_conference_members(matched_politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_conference_members_manually_verified ON extracted_conference_members(is_manually_verified)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_parliamentary_group_members_group ON extracted_parliamentary_group_members(parliamentary_group_id)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_parliamentary_group_members_status ON extracted_parliamentary_group_members(matching_status)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_parliamentary_group_members_politician ON extracted_parliamentary_group_members(matched_politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_parliamentary_group_members_reviewed_by_user_id ON extracted_parliamentary_group_members(reviewed_by_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_parliamentary_group_members_manually_verified ON extracted_parliamentary_group_members(is_manually_verified)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_proposal_judges_proposal ON extracted_proposal_judges(proposal_id)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_proposal_judges_status ON extracted_proposal_judges(matching_status)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_proposal_judges_politician ON extracted_proposal_judges(matched_politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_proposal_judges_group ON extracted_proposal_judges(matched_parliamentary_group_id)",
        "CREATE INDEX IF NOT EXISTS idx_extracted_proposal_judges_judgment ON extracted_proposal_judges(extracted_judgment)",
        # 議員団関連
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_groups_name_conference ON parliamentary_groups(name, conference_id)",
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_group_memberships_politician ON parliamentary_group_memberships(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_group_memberships_group ON parliamentary_group_memberships(parliamentary_group_id)",
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_group_memberships_dates ON parliamentary_group_memberships(start_date, end_date)",
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_group_memberships_created_by_user_id ON parliamentary_group_memberships(created_by_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_parliamentary_group_memberships_manually_verified ON parliamentary_group_memberships(is_manually_verified)",
        # 議員の議会所属
        "CREATE INDEX IF NOT EXISTS idx_politician_affiliations_politician ON politician_affiliations(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_politician_affiliations_conference ON politician_affiliations(conference_id)",
        "CREATE INDEX IF NOT EXISTS idx_politician_affiliations_role ON politician_affiliations(role)",
        "CREATE INDEX IF NOT EXISTS idx_politician_affiliations_manually_verified ON politician_affiliations(is_manually_verified)",
        # 議案と会議
        "CREATE INDEX IF NOT EXISTS idx_proposal_meeting_occurrences_proposal ON proposal_meeting_occurrences(proposal_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_meeting_occurrences_meeting ON proposal_meeting_occurrences(meeting_id)",
        # ユーザー
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_users_last_login_at ON users(last_login_at)",
        # LLM処理
        "CREATE INDEX IF NOT EXISTS idx_llm_history_processing_type ON llm_processing_history(processing_type)",
        "CREATE INDEX IF NOT EXISTS idx_llm_history_model ON llm_processing_history(model_name, model_version)",
        "CREATE INDEX IF NOT EXISTS idx_llm_history_status ON llm_processing_history(status)",
        "CREATE INDEX IF NOT EXISTS idx_llm_history_input_ref ON llm_processing_history(input_reference_type, input_reference_id)",
        "CREATE INDEX IF NOT EXISTS idx_llm_history_created_at ON llm_processing_history(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_llm_history_started_at ON llm_processing_history(started_at)",
        "CREATE INDEX IF NOT EXISTS idx_llm_history_created_by ON llm_processing_history(created_by)",
        # プロンプトバージョン
        "CREATE INDEX IF NOT EXISTS idx_prompt_versions_key ON prompt_versions(prompt_key)",
        "CREATE INDEX IF NOT EXISTS idx_prompt_versions_created_at ON prompt_versions(created_at)",
        # 抽出ログ
        "CREATE INDEX IF NOT EXISTS idx_extraction_logs_entity ON extraction_logs(entity_type, entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_extraction_logs_pipeline ON extraction_logs(pipeline_version)",
        "CREATE INDEX IF NOT EXISTS idx_extraction_logs_created_at ON extraction_logs(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_extraction_logs_entity_type ON extraction_logs(entity_type)",
        "CREATE INDEX IF NOT EXISTS idx_extraction_logs_confidence ON extraction_logs(confidence_score)",
        # 操作ログ
        "CREATE INDEX IF NOT EXISTS idx_politician_operation_logs_user_id ON politician_operation_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_politician_operation_logs_operated_at ON politician_operation_logs(operated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_politician_operation_logs_operation_type ON politician_operation_logs(operation_type)",
        "CREATE INDEX IF NOT EXISTS idx_politician_operation_logs_politician_id ON politician_operation_logs(politician_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_operation_logs_user_id ON proposal_operation_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_operation_logs_operated_at ON proposal_operation_logs(operated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_operation_logs_operation_type ON proposal_operation_logs(operation_type)",
        "CREATE INDEX IF NOT EXISTS idx_proposal_operation_logs_proposal_id ON proposal_operation_logs(proposal_id)",
    ]
    for idx in indexes:
        op.execute(idx)

    # 特殊なインデックス（部分インデックス、複合インデックス）
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_prompt_versions_active
        ON prompt_versions(prompt_key, is_active) WHERE is_active = TRUE
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_proposal_submitters_unique
        ON proposal_submitters(
            proposal_id,
            COALESCE(politician_id, -1),
            COALESCE(parliamentary_group_id, -1)
        )
    """)


def _create_triggers() -> None:
    """Create trigger functions and triggers."""
    # updated_at トリガー関数
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # 単一アクティブバージョン確保関数
    op.execute("""
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
    """)

    # トリガー作成（存在チェック付き）
    triggers = [
        ("update_governing_bodies_updated_at", "governing_bodies"),
        ("update_conferences_updated_at", "conferences"),
        ("update_meetings_updated_at", "meetings"),
        ("update_minutes_updated_at", "minutes"),
        ("update_speakers_updated_at", "speakers"),
        ("update_political_parties_updated_at", "political_parties"),
        ("update_politicians_updated_at", "politicians"),
        ("update_pledges_updated_at", "pledges"),
        ("update_party_membership_history_updated_at", "party_membership_history"),
        ("update_conversations_updated_at", "conversations"),
        ("update_proposals_updated_at", "proposals"),
        ("update_proposal_judges_updated_at", "proposal_judges"),
        ("update_politician_affiliations_updated_at", "politician_affiliations"),
        (
            "update_proposal_meeting_occurrences_updated_at",
            "proposal_meeting_occurrences",
        ),
        ("update_parliamentary_groups_updated_at", "parliamentary_groups"),
        (
            "update_parliamentary_group_memberships_updated_at",
            "parliamentary_group_memberships",
        ),
        ("trigger_update_llm_processing_history_updated_at", "llm_processing_history"),
        ("trigger_update_prompt_versions_updated_at", "prompt_versions"),
        ("trigger_update_extraction_logs_updated_at", "extraction_logs"),
    ]

    for trigger_name, table_name in triggers:
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = '{trigger_name}'
                ) THEN
                    CREATE TRIGGER {trigger_name}
                    BEFORE UPDATE ON {table_name}
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                END IF;
            END$$;
        """)

    # 特殊トリガー
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_ensure_single_active_prompt_version'
            ) THEN
                CREATE TRIGGER trigger_ensure_single_active_prompt_version
                BEFORE INSERT OR UPDATE ON prompt_versions
                FOR EACH ROW WHEN (NEW.is_active = TRUE)
                EXECUTE FUNCTION ensure_single_active_prompt_version();
            END IF;
        END$$;
    """)


def _create_comments() -> None:
    """Create table and column comments."""
    comments = [
        # 基本テーブル
        "COMMENT ON TABLE governing_bodies IS '開催主体'",
        "COMMENT ON COLUMN governing_bodies.organization_code IS '総務省の6桁地方自治体コード'",
        "COMMENT ON COLUMN governing_bodies.organization_type IS '詳細な組織種別（都道府県、市、区、町、村など）'",
        "COMMENT ON TABLE conferences IS '会議体 (議会や委員会など)'",
        "COMMENT ON COLUMN conferences.governing_body_id IS 'Optional reference to governing body'",
        "COMMENT ON COLUMN conferences.members_introduction_url IS 'URL where the council members are introduced'",
        "COMMENT ON COLUMN conferences.prefecture IS '都道府県（全国は国会を表す）'",
        "COMMENT ON TABLE meetings IS '会議 (具体的な開催インスタンス)'",
        "COMMENT ON COLUMN meetings.url IS '会議関連のURLまたは議事録PDFのURL'",
        "COMMENT ON COLUMN meetings.gcs_pdf_uri IS 'Google Cloud Storage URI for the PDF file'",
        "COMMENT ON COLUMN meetings.gcs_text_uri IS 'Google Cloud Storage URI for the extracted text file'",
        "COMMENT ON COLUMN meetings.attendees_mapping IS '出席者の役職と名前のマッピング'",
        "COMMENT ON TABLE minutes IS '議事録'",
        "COMMENT ON COLUMN minutes.llm_process_id IS 'LLM処理履歴との関連付けID'",
        "COMMENT ON COLUMN minutes.role_name_mappings IS '議事録冒頭の出席者情報から抽出した役職-人名マッピング'",
        "COMMENT ON TABLE speakers IS '発言者'",
        "COMMENT ON COLUMN speakers.politician_id IS 'Reference to the politician this speaker represents'",
        "COMMENT ON COLUMN speakers.is_manually_verified IS '人間による手動検証済みフラグ'",
        "COMMENT ON TABLE political_parties IS '政党'",
        "COMMENT ON TABLE politicians IS '政治家'",
        "COMMENT ON COLUMN politicians.furigana IS 'Name reading in hiragana'",
        "COMMENT ON COLUMN politicians.district IS 'Electoral district'",
        "COMMENT ON TABLE pledges IS '公約'",
        "COMMENT ON TABLE party_membership_history IS '政治家の政党所属履歴'",
        "COMMENT ON TABLE conversations IS '発言'",
        "COMMENT ON TABLE proposals IS '議案'",
        "COMMENT ON TABLE proposal_judges IS '議案への賛否情報'",
        "COMMENT ON TABLE politician_affiliations IS '議員の議会所属情報'",
        "COMMENT ON TABLE proposal_meeting_occurrences IS '議案と会議の紐付け情報'",
        "COMMENT ON TABLE parliamentary_groups IS '議員団（会派）'",
        "COMMENT ON TABLE parliamentary_group_memberships IS '議員団所属履歴'",
        "COMMENT ON TABLE extracted_conference_members IS '議会メンバー情報の抽出結果'",
        "COMMENT ON TABLE extracted_parliamentary_group_members IS '議員団メンバー情報の抽出結果'",
        "COMMENT ON TABLE extracted_proposal_judges IS '議案賛否情報の抽出結果'",
        "COMMENT ON TABLE proposal_parliamentary_group_judges IS '議案への会派単位の賛否情報'",
        "COMMENT ON TABLE proposal_judge_parliamentary_groups IS '賛否レコードと会派の中間テーブル'",
        "COMMENT ON TABLE proposal_judge_politicians IS '賛否レコードと政治家の中間テーブル'",
        "COMMENT ON TABLE proposal_submitters IS '議案提出者テーブル'",
        "COMMENT ON TABLE users IS 'ログインユーザーを管理するテーブル'",
        "COMMENT ON TABLE llm_processing_history IS 'LLM処理の履歴を記録するテーブル'",
        "COMMENT ON TABLE prompt_versions IS 'プロンプトテンプレートのバージョン管理テーブル'",
        "COMMENT ON TABLE extraction_logs IS 'LLM抽出結果の履歴を記録するテーブル'",
        "COMMENT ON TABLE politician_operation_logs IS '政治家操作ログ'",
        "COMMENT ON TABLE proposal_operation_logs IS '議案操作ログ'",
    ]
    for comment in comments:
        op.execute(comment)


def downgrade() -> None:
    """Drop all tables (dangerous operation).

    WARNING: This will delete all data. Only use in development.
    """
    raise NotImplementedError(
        "Downgrade from baseline is not supported. "
        "To reset the database, use 'just clean' and restart Docker."
    )
