-- Execute all migration files in order
-- This file is needed because PostgreSQL doesn't automatically execute files in subdirectories

\echo 'Running migrations...'

\i /docker-entrypoint-initdb.d/02_migrations/001_add_url_to_meetings.sql
\i /docker-entrypoint-initdb.d/02_migrations/002_add_members_list_url_to_political_parties.sql
\i /docker-entrypoint-initdb.d/02_migrations/003_add_politician_details.sql
\i /docker-entrypoint-initdb.d/02_migrations/004_add_gcs_uri_to_meetings.sql
\i /docker-entrypoint-initdb.d/02_migrations/005_add_members_introduction_url_to_conferences.sql
\i /docker-entrypoint-initdb.d/02_migrations/006_add_role_to_politician_affiliations.sql
\i /docker-entrypoint-initdb.d/02_migrations/007_create_extracted_conference_members_table.sql
\i /docker-entrypoint-initdb.d/02_migrations/008_create_parliamentary_groups_tables.sql
\i /docker-entrypoint-initdb.d/02_migrations/009_add_processed_at_to_minutes.sql
\i /docker-entrypoint-initdb.d/02_migrations/010_add_name_to_meetings.sql
\i /docker-entrypoint-initdb.d/02_migrations/011_add_organization_code_to_governing_bodies.sql
\i /docker-entrypoint-initdb.d/02_migrations/012_remove_conference_governing_body_fk.sql
\i /docker-entrypoint-initdb.d/02_migrations/013_create_llm_processing_history.sql
\i /docker-entrypoint-initdb.d/02_migrations/014_create_prompt_versions.sql
\i /docker-entrypoint-initdb.d/02_migrations/015_add_party_position_to_politicians.sql
\i /docker-entrypoint-initdb.d/02_migrations/016_add_created_by_to_llm_processing_history.sql
\i /docker-entrypoint-initdb.d/02_migrations/017_add_process_id_to_minutes.sql
\i /docker-entrypoint-initdb.d/02_migrations/018_add_matching_history_to_speakers.sql
\i /docker-entrypoint-initdb.d/02_migrations/019_add_performance_indexes.sql
\i /docker-entrypoint-initdb.d/02_migrations/020_add_attendees_mapping_to_meetings.sql
\i /docker-entrypoint-initdb.d/02_migrations/021_create_extracted_parliamentary_group_members_table.sql
\i /docker-entrypoint-initdb.d/02_migrations/022_add_proposal_metadata.sql
\i /docker-entrypoint-initdb.d/02_migrations/023_create_extracted_proposal_judges.sql
\i /docker-entrypoint-initdb.d/02_migrations/024_add_status_url_to_proposals.sql
\i /docker-entrypoint-initdb.d/02_migrations/025_create_proposal_parliamentary_group_judges.sql
\i /docker-entrypoint-initdb.d/02_migrations/026_create_extracted_politicians_table.sql
\i /docker-entrypoint-initdb.d/02_migrations/027_migrate_existing_politicians.sql
\i /docker-entrypoint-initdb.d/02_migrations/028_add_converted_status_to_extracted_politicians.sql
\i /docker-entrypoint-initdb.d/02_migrations/029_remove_image_url_from_extracted_politicians.sql
\i /docker-entrypoint-initdb.d/02_migrations/030_remove_position_from_politicians_tables.sql
\i /docker-entrypoint-initdb.d/02_migrations/031_make_speaker_id_nullable_in_politicians.sql
\i /docker-entrypoint-initdb.d/02_migrations/032_normalize_speaker_politician_relationship.sql
\i /docker-entrypoint-initdb.d/02_migrations/033_add_furigana_to_politicians.sql
\i /docker-entrypoint-initdb.d/02_migrations/034_add_unique_constraint_extracted_parliamentary_group_members.sql
\i /docker-entrypoint-initdb.d/02_migrations/035_create_users_table.sql
\i /docker-entrypoint-initdb.d/02_migrations/036_add_user_id_to_work_tables.sql
\i /docker-entrypoint-initdb.d/02_migrations/037_add_created_by_user_id_to_parliamentary_group_memberships.sql
\i /docker-entrypoint-initdb.d/02_migrations/038_create_extraction_logs.sql
\i /docker-entrypoint-initdb.d/02_migrations/039_add_verification_fields_to_gold_entities.sql
\i /docker-entrypoint-initdb.d/02_migrations/040_add_extraction_log_fields_to_extracted_members.sql
\i /docker-entrypoint-initdb.d/02_migrations/041_drop_extracted_politicians_table.sql
\i /docker-entrypoint-initdb.d/02_migrations/042_remove_verification_fields_from_politicians.sql
\i /docker-entrypoint-initdb.d/02_migrations/043_create_politician_operation_logs.sql

\echo 'Migrations completed.'
