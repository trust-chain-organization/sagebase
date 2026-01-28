-- Database Bootstrap for Political Activity Tracking Application
-- Version: 2026-01-28
--
-- このファイルは最小限のブートストラップのみを行います。
-- スキーマ作成は Alembic マイグレーション (001_baseline.py) で行われます。
--
-- See: docs/ADR/0006-alembic-migration-unification.md

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- エンティティタイプのENUM型（Alembicで作成が難しいため先に作成）
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
