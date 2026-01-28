---
name: seed-file-management
description: シードファイル（初期データ）のCRUD操作に関するガイドライン。IDを明示的に指定した場合のシーケンスリセット、ファイル構造、命名規則、テスト方法をカバー。シードファイルの作成・修正時にアクティベートします。
---

# Seed File Management（シードファイル管理）

## 目的
PostgreSQLのシードファイル（初期データ）を安全に作成・修正・管理するためのガイドラインを提供します。
**特に、IDを明示的に指定した場合のシーケンス衝突問題を防ぐことが重要です。**

## いつアクティベートするか
このスキルは以下の場合に自動的にアクティベートされます：
- `database/seed_*.sql` ファイルを作成・修正する時
- シードデータ生成機能（`generate_seed_file`など）を実装する時
- ユーザーが「シード」「seed」「初期データ」「マスターデータ」と言及した時
- データベース初期化に関する作業をする時
- `ON CONFLICT` や `UPSERT` を含むINSERT文を書く時

## ⚠️ CRITICAL: シーケンス衝突問題

### 問題の概要（Issue #1036）
PostgreSQLでは、`INSERT INTO table (id, ...) VALUES (1, ...)` のように**IDを明示的に指定してINSERT**すると、シーケンス（`table_id_seq`）は**更新されません**。

その後、アプリケーションからIDを指定せずにINSERTすると：
```
ERROR: duplicate key value violates unique constraint "table_pkey"
DETAIL: Key (id)=(1) already exists.
```

### 解決策：シーケンスリセット

シードファイルの**最後**に必ずシーケンスリセットを追加：

```sql
-- シーケンスを最大ID+1にリセット
SELECT setval('table_name_id_seq', COALESCE((SELECT MAX(id) FROM table_name), 0) + 1, false);
```

## クイックチェックリスト

シードファイル作成時：
- [ ] **シーケンスリセット**: IDを指定するINSERTの後にシーケンスリセットを追加
- [ ] **冪等性**: `ON CONFLICT` を使用して再実行可能に
- [ ] **依存関係**: 外部キー制約を考慮した実行順序
- [ ] **テスト**: シードデータ投入後に新規レコード作成が成功することを確認

シードファイル修正時：
- [ ] **既存シーケンス**: 新しいIDを追加した場合、シーケンスリセットを更新
- [ ] **マイグレーション**: 必要に応じてシーケンスリセット用マイグレーションを追加

## ファイル構造と命名規則

### ディレクトリ構造
```
database/
├── init.sql                              # 初期スキーマ
├── 02_run_migrations.sql                 # マイグレーション実行
├── 03_seed_governing_bodies_generated.sql # シード（3番目以降）
├── 04_seed_political_parties_generated.sql
├── 05_seed_conferences_generated.sql
├── 06_seed_parliamentary_groups_generated.sql
└── migrations/
    └── 049_reset_parliamentary_groups_sequence.sql  # シーケンスリセット
```

### 命名規則
- **形式**: `{番号}_{seed|seed_テーブル名}_{generated|manual}.sql`
- **番号**: PostgreSQLの実行順序を制御（アルファベット順）
- **generated**: 自動生成されたシード
- **manual**: 手動で作成・管理するシード

## シードファイルの基本パターン

### パターン1: UPSERT（推奨）

```sql
-- シードデータ（IDを明示的に指定）
INSERT INTO parliamentary_groups (id, name, conference_id, url, description, is_active)
VALUES
    (1, '自由民主党京都市会議員団', 54, 'https://example.com', NULL, true),
    (2, '公明党京都市会議員団', 54, 'https://example.com', NULL, true)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    conference_id = EXCLUDED.conference_id,
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active;

-- ⚠️ 必須: シーケンスリセット
SELECT setval('parliamentary_groups_id_seq',
    COALESCE((SELECT MAX(id) FROM parliamentary_groups), 0) + 1, false);
```

### パターン2: DELETE + INSERT（クリーンリセット）

```sql
-- 既存データを削除
DELETE FROM parliamentary_groups WHERE id > 0;

-- シードデータを挿入
INSERT INTO parliamentary_groups (id, name, conference_id)
VALUES
    (1, '会派A', 1),
    (2, '会派B', 1);

-- ⚠️ 必須: シーケンスリセット
SELECT setval('parliamentary_groups_id_seq',
    COALESCE((SELECT MAX(id) FROM parliamentary_groups), 0) + 1, false);
```

### パターン3: IDを指定しない（自動採番）

```sql
-- IDを指定しない場合はシーケンスリセット不要
INSERT INTO parliamentary_groups (name, conference_id)
VALUES
    ('会派A', 1),
    ('会派B', 1)
ON CONFLICT (name, conference_id) DO NOTHING;
```

## シード生成コードの実装

`generate_seed_file` などのメソッドでシードファイルを生成する場合：

```python
async def generate_seed_file(self) -> GenerateSeedFileOutputDto:
    """シードファイルを生成する（シーケンスリセット付き）"""
    all_groups = await self.repository.get_all()

    seed_content = "-- Parliamentary Groups Seed Data\n"
    seed_content += "-- Generated from current database\n\n"

    # INSERT文を生成
    seed_content += "INSERT INTO parliamentary_groups (id, name, ...) VALUES\n"
    values = []
    for group in all_groups:
        values.append(f"    ({group.id}, '{group.name}', ...)")
    seed_content += ",\n".join(values) + "\n"

    # UPSERT用のON CONFLICT句
    seed_content += "ON CONFLICT (id) DO UPDATE SET\n"
    seed_content += "    name = EXCLUDED.name,\n"
    seed_content += "    ...;\n\n"

    # ⚠️ 必須: シーケンスリセット
    seed_content += "-- Reset sequence to max id + 1\n"
    seed_content += "SELECT setval('parliamentary_groups_id_seq', "
    seed_content += "COALESCE((SELECT MAX(id) FROM parliamentary_groups), 0) + 1, false);\n"

    return GenerateSeedFileOutputDto(success=True, seed_content=seed_content)
```

## 外部キー制約と実行順序

### 依存関係の例
```
governing_bodies (親)
    ↓
conferences (子: governing_body_id → governing_bodies.id)
    ↓
parliamentary_groups (孫: conference_id → conferences.id)
```

### 実行順序（番号で制御）
```
03_seed_governing_bodies_generated.sql  # 先に実行
04_seed_conferences_generated.sql       # 次に実行
05_seed_parliamentary_groups_generated.sql  # 最後に実行
```

## テスト方法

### 1. シードデータ投入テスト

```bash
# データベースをリセットしてシードを適用
./reset-database.sh

# または Docker で
docker compose down -v && docker compose up -d
```

### 2. 新規レコード作成テスト

シードデータ投入後、必ず新規レコードが作成できることを確認：

```python
@pytest.mark.asyncio
async def test_create_after_seed(self, repository):
    """シードデータ投入後に新規作成できることを確認"""
    entity = ParliamentaryGroup(
        name="新しい会派",
        conference_id=1,
    )
    created = await repository.create(entity)

    # IDが正しく採番されること（既存IDと衝突しない）
    assert created.id is not None
    assert created.id > 0
```

### 3. シーケンス確認

```sql
-- 現在のシーケンス値を確認
SELECT last_value, is_called FROM parliamentary_groups_id_seq;

-- 最大IDを確認
SELECT MAX(id) FROM parliamentary_groups;

-- シーケンス値 > 最大ID であること
```

## トラブルシューティング

### Q: シーケンス衝突エラーが発生する

```
ERROR: duplicate key value violates unique constraint "xxx_pkey"
```

**解決策**:
1. シーケンスをリセット
```sql
SELECT setval('table_name_id_seq',
    COALESCE((SELECT MAX(id) FROM table_name), 0) + 1, false);
```

2. マイグレーションを追加（永続的な修正）
```sql
-- database/migrations/XXX_reset_table_sequence.sql
SELECT setval('table_name_id_seq',
    COALESCE((SELECT MAX(id) FROM table_name), 0) + 1, false);
```

### Q: シードファイルを再実行するとエラーになる

**解決策**: `ON CONFLICT` を使用して冪等性を確保
```sql
INSERT INTO table (id, name) VALUES (1, 'value')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
```

### Q: 外部キー制約エラーが発生する

**解決策**: ファイル名の番号を調整して実行順序を制御

## 関連リンク

- [migration-helper](../migration-helper/SKILL.md) - マイグレーション作成
- [project-conventions](../project-conventions/SKILL.md) - プロジェクト規約
