---
name: migration-helper
description: Assists in creating database migrations for Sagebase using Alembic. Activates when creating migration files, modifying database schema, or adding tables/columns/indexes. Ensures proper migration structure, rollback support, and Alembic best practices.
---

# Migration Helper

## Purpose
Assist in creating database migrations following Sagebase conventions using Alembic migration tool.

## When to Activate
This skill activates automatically when:
- Creating new migration files
- Modifying database schema
- Adding tables, columns, indexes, or constraints
- User mentions "migration", "schema", or "database change"
- User asks about rollback or migration history

## 🚀 Quick Start with Alembic

### Creating a New Migration

```bash
# Docker環境内で新しいマイグレーションを作成
just migrate-new "add_column_to_table"

# または直接Alembicコマンドを実行
docker compose exec sagebase uv run alembic revision -m "add_column_to_table"
```

### Migration Commands

```bash
# マイグレーション実行（未適用分を全て適用）
just migrate

# ロールバック（1つ前に戻す）
just migrate-rollback

# 現在のバージョン確認
just migrate-current

# マイグレーション履歴確認
just migrate-history

# 新規マイグレーション作成
just migrate-new "description"
```

## Quick Checklist

Before completing a migration:

- [ ] **Migration Created**: `alembic revision -m "description"` で作成
- [ ] **upgrade() 実装**: スキーマ変更のSQL
- [ ] **downgrade() 実装**: ロールバック用のSQL
- [ ] **Idempotent**: `IF NOT EXISTS`/`IF EXISTS` 使用
- [ ] **Tested**: `just migrate` で適用確認
- [ ] **Rollback Tested**: `just migrate-rollback` で戻せることを確認

## Migration File Structure

```python
"""Description of migration.

Revision ID: xxx
Revises: yyy
Create Date: 2025-01-20
"""

from alembic import op


revision = "xxx"
down_revision = "yyy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration."""
    op.execute("""
        ALTER TABLE your_table
        ADD COLUMN IF NOT EXISTS new_column VARCHAR(100);
    """)


def downgrade() -> None:
    """Rollback migration."""
    op.execute("""
        ALTER TABLE your_table
        DROP COLUMN IF EXISTS new_column;
    """)
```

## Common Patterns

### Add Column
```python
def upgrade() -> None:
    op.execute("""
        ALTER TABLE table_name
        ADD COLUMN IF NOT EXISTS column_name VARCHAR(255);
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE table_name
        DROP COLUMN IF EXISTS column_name;
    """)
```

### Create Table
```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS new_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS new_table;
    """)
```

### Add Index
```python
def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_table_column
        ON table_name(column_name);
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_table_column;
    """)
```

See [examples.md](examples.md) for more patterns.

## ⚠️ Important Notes

1. **Always implement downgrade()**: ロールバック機能を活用するために必須
2. **Use IF NOT EXISTS/IF EXISTS**: 冪等性を確保
3. **Test rollback**: `just migrate-rollback` でロールバックできることを確認
4. **Don't modify existing migrations**: 一度適用されたマイグレーションは変更しない

## Legacy Migration Files

既存の45個のSQLマイグレーション（`database/migrations/`）は参照用として保持されています。
新規マイグレーションは必ずAlembicを使用してください。

## CLI Commands

```bash
# sagebase CLI経由
sagebase migrate            # マイグレーション実行
sagebase migrate-rollback   # ロールバック
sagebase migrate-status     # 現在のバージョン確認
sagebase migrate-history    # 履歴確認
sagebase migrate-new "desc" # 新規作成
```

## Detailed Reference

For comprehensive migration patterns and SQL details, see [reference.md](reference.md).
