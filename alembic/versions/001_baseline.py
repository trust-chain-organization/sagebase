"""Baseline migration for existing database schema.

このマイグレーションは既存のデータベーススキーマのベースラインを設定します。

既存のデータベースがある場合:
- init.sql で作成されたテーブル
- database/migrations/ 配下の45個のSQLマイグレーション
これらが適用済みであることを前提とします。

新規データベースの場合:
- Docker起動時に init.sql と 02_run_migrations.sql が自動実行されます
- このマイグレーションは「既に適用済み」としてマークするだけです

Revision ID: 001
Revises:
Create Date: 2025-01-20
"""

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Baseline - 既存スキーマが存在することを確認するのみ。

    このマイグレーションは実際のスキーマ変更を行いません。
    既存のデータベースに対してAlembicのバージョン管理を開始するためのマーカーです。

    既存のスキーマは以下で管理されています:
    - database/init.sql: 初期スキーマ
    - database/migrations/001-045: 追加のマイグレーション
    """
    # 既存スキーマのベースライン - 変更なし
    # alembic_version テーブルが作成され、このリビジョンが記録されます
    pass


def downgrade() -> None:
    """ベースラインへのダウングレードは許可されていません。

    ベースラインより前の状態に戻すことはデータ損失を招く可能性があるため、
    明示的に禁止しています。
    """
    raise Exception(
        "Cannot downgrade past baseline. "
        "To reset the database, use 'just clean' and restart Docker."
    )
