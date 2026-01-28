# ADR 0006: マイグレーションのAlembic完全統一

## Status

Accepted (2026-01-28)

## Context

### 背景

Sagebaseプロジェクトでは、データベースマイグレーションに2つの方式が混在していました：

1. **レガシー方式**: `database/migrations/` 配下のSQLファイル（001〜048）
   - Docker起動時に `02_run_migrations.sql` で順次実行
   - ダウングレード機能なし
   - 履歴管理はファイル名の連番のみ

2. **Alembic方式**: `alembic/versions/` 配下のPythonファイル
   - `alembic_version` テーブルで履歴管理
   - ダウングレード（ロールバック）機能あり
   - マイグレーションの依存関係を明示的に管理

### 問題

- **開発者の混乱**: 新しいマイグレーションをどちらの方式で作成すべきか不明確
- **二重管理**: 一部のマイグレーションが両方式で重複、init.sqlとの同期維持が必要
- **CI環境との不整合**: ローカルとCIで異なるマイグレーション適用方法
- **ロールバック不可**: レガシー方式ではスキーマ変更を元に戻せない
- **Single Source of Truthの欠如**: init.sqlとAlembic migrationsの両方にスキーマ定義が存在

## Decision

### 決定事項

1. **Alembicを唯一のスキーマ定義源（Single Source of Truth）とする**
2. **init.sqlは最小限のブートストラップのみ**（extensions + enum型）
3. **Migration 001で完全なスキーマを作成**
4. **シードファイルはAlembic実行後に読み込む**
5. **レガシーファイルの削除**: `database/migrations/` を削除
6. **migrate-legacyの削除**: justfileの `migrate-legacy` コマンドを削除

### アーキテクチャ

```
Database Initialization Flow:
┌─────────────────────────────────────────────────────────────┐
│ 1. PostgreSQL起動                                           │
│    └─ init.sql: Extensions + ENUM型のみ作成                │
├─────────────────────────────────────────────────────────────┤
│ 2. alembic upgrade head                                     │
│    ├─ 001_baseline.py: 全テーブル・インデックス・トリガー  │
│    ├─ 002_example.py: (例示用、変更なし)                   │
│    ├─ 003_update_proposals.py: proposals変更               │
│    ├─ 004_create_operation_logs.py: 操作ログ               │
│    ├─ 005_add_conference_id.py: submitters拡張             │
│    ├─ 006_create_relations.py: Many-to-Many構造            │
│    └─ 007_reset_sequence.py: シーケンスリセット            │
├─────────────────────────────────────────────────────────────┤
│ 3. load-seeds.sh                                            │
│    └─ シードファイル読み込み（初回のみ）                   │
└─────────────────────────────────────────────────────────────┘
```

### 具体的な変更

#### init.sql / init_ci.sql
- **Before**: 完全なスキーマ定義（887行）
- **After**: 最小限のブートストラップ（25行）
  - `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`
  - `CREATE TYPE entity_type AS ENUM (...)`

#### Migration 001 (001_baseline.py)
- **Before**: 空（既存スキーマのマーカーのみ）
- **After**: 完全なスキーマ作成（780行）
  - 全テーブル定義
  - 全インデックス
  - 全トリガー関数・トリガー
  - 全テーブルコメント

#### docker-compose.yml
- シードファイルのマウントを削除（docker-entrypoint-initdb.dから）
- init.sqlのみマウント

#### justfile
- `./scripts/load-seeds.sh` を Alembic 実行後に呼び出し
- `up`, `up-fast`, `up-detached` 全てで実行

#### CI環境
- `alembic stamp head` → `alembic upgrade head` に変更

## Consequences

### 利点

1. **Single Source of Truth**: スキーマ定義はAlembic migrationsのみ
2. **一元管理**: マイグレーションの管理方法が統一され、開発者の混乱を解消
3. **ロールバック可能**: Alembicの `downgrade` 機能で安全にスキーマ変更を戻せる
4. **CI/CD改善**: ローカルとCI環境で完全に同じマイグレーション方式を使用
5. **同期不要**: init.sqlとAlembicの同期維持が不要に

### トレードオフ

1. **既存環境の移行作業**: 既存のデータベースでは `alembic stamp head` の実行が必要
2. **履歴の断絶**: レガシーマイグレーションの履歴はAlembicでは追跡されない（gitの履歴で参照可能）
3. **初回起動時の処理増加**: Alembic + シード読み込みで若干時間がかかる

### 移行ガイド

#### 新規環境
特別な対応は不要。`just up` で自動的に最新スキーマが構築される。

#### 既存環境（この変更前のスキーマがある場合）
既にデータがある環境では、以下のコマンドでAlembicのバージョン管理を開始：

```bash
# Alembicに「現在のスキーマは最新版」と認識させる
docker compose exec sagebase uv run alembic stamp head
```

## References

- Issue: #1032
- 関連ADR: なし
- レガシーマイグレーション: 削除済み（gitの履歴で `database/migrations/001_*.sql` 〜 `048_*.sql` を参照可能）
- Alembicマイグレーション: `alembic/versions/001_*.py` 〜 `007_*.py`
