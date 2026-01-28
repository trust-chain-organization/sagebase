-- Issue #1036: 議員団シーケンスのリセット
-- シードデータでIDを明示的に指定してINSERTした後、シーケンスが古い値のままになっている問題を修正
-- 既存データの最大IDに基づいてシーケンスをリセットする

SELECT setval('parliamentary_groups_id_seq', COALESCE((SELECT MAX(id) FROM parliamentary_groups), 0) + 1, false);

-- 議員団メンバーシップのシーケンスも同様にリセット（念のため）
SELECT setval('parliamentary_group_memberships_id_seq', COALESCE((SELECT MAX(id) FROM parliamentary_group_memberships), 0) + 1, false);
