# ADR 0006: マイグレーションのAlembic統一

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
- **二重管理**: 一部のマイグレーションが両方式で重複
- **CI環境との不整合**: ローカルとCIで異なるマイグレーション適用方法
- **ロールバック不可**: レガシー方式ではスキーマ変更を元に戻せない

## Decision

### 決定事項

1. **Alembicに統一**: 新規マイグレーションは全てAlembicで管理
2. **init.sqlの更新**: レガシーマイグレーション（001〜048）とAlembicマイグレーション（003〜007）を統合した完全なスキーマを `init.sql` に反映
3. **レガシーファイルの保持**: `database/migrations/` は履歴として保持（削除しない）
4. **migrate-legacyの非推奨化**: justfileの `migrate-legacy` コマンドをエラーで終了するよう変更

### 具体的な変更

#### init.sql
- 全てのテーブル定義を最新状態に更新
- レガシーマイグレーションで追加されたカラム、インデックス、制約を統合
- Alembicマイグレーションの変更も反映（proposals.content → titleなど）

#### docker-compose.yml
- `02_run_migrations.sql` のマウントを削除
- `database/migrations/` のマウントを削除
- シードファイルの番号を再採番（02〜07）

#### CI環境
- `init_ci.sql` 適用後に `alembic stamp head` を実行
- Alembicが最新バージョンとして認識するよう設定

## Consequences

### 利点

1. **一元管理**: マイグレーションの管理方法が統一され、開発者の混乱を解消
2. **ロールバック可能**: Alembicの `downgrade` 機能で安全にスキーマ変更を戻せる
3. **CI/CD改善**: ローカルとCI環境で同じマイグレーション方式を使用
4. **新規環境構築の簡素化**: `init.sql` + `alembic upgrade head` のみで最新状態に

### トレードオフ

1. **既存環境の移行作業**: 既存のデータベースでは `alembic stamp head` の実行が必要
2. **履歴の断絶**: レガシーマイグレーションの履歴はAlembicでは追跡されない

### 移行ガイド

#### 新規環境
特別な対応は不要。`just up` で自動的に最新スキーマが構築される。

#### 既存環境
既にデータがある環境では、以下のコマンドでAlembicのバージョン管理を開始：

```bash
# Alembicに「現在のスキーマは最新版」と認識させる
docker compose exec sagebase uv run alembic stamp head
```

## References

- Issue: #1032
- 関連ADR: なし
- レガシーマイグレーション: `database/migrations/001_*.sql` 〜 `048_*.sql`
- Alembicマイグレーション: `alembic/versions/001_*.py` 〜 `007_*.py`
