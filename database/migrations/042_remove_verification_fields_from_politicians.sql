-- マイグレーション: 042_remove_verification_fields_from_politicians.sql
-- 目的: politiciansテーブルから検証フィールドを削除
-- 背景: #915により政治家データは手動登録のみに統一されたため、
--       LLM抽出からの保護機能（検証フラグ）が不要になった
-- 関連Issue: #930 [PBI-007] politiciansテーブルの検証フィールド削除

-- インデックスの削除（冪等性対応）
DROP INDEX IF EXISTS idx_politicians_manually_verified;

-- politiciansテーブルから検証フィールドを削除（冪等性対応）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'politicians' AND column_name = 'is_manually_verified'
    ) THEN
        ALTER TABLE politicians DROP COLUMN is_manually_verified;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'politicians' AND column_name = 'latest_extraction_log_id'
    ) THEN
        ALTER TABLE politicians DROP COLUMN latest_extraction_log_id;
    END IF;
END$$;
