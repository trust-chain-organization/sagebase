"""Baseline migration for existing database schema.

このマイグレーションは既存のデータベーススキーマのベースラインを設定します。

=== 2026-01-28 更新 ===
init.sql に全てのスキーマ変更が統合されました:
- レガシーマイグレーション: database/migrations/001〜048
- Alembicマイグレーション: 003〜007の変更内容

新規データベースの場合:
- Docker起動時に init.sql のみが自動実行されます
- Alembicは `just up` 実行時に `alembic upgrade head` で最新状態をマーク

既存のデータベースがある場合:
- `alembic stamp head` で現在のスキーマが最新であることをマーク

Revision ID: 001
Revises:
Create Date: 2025-01-20
Updated: 2026-01-28 (ADR 0006)
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

    2026-01-28以降:
    - database/init.sql に全てのスキーマが統合されています
    - レガシーマイグレーション（001-048）は履歴として保持
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
