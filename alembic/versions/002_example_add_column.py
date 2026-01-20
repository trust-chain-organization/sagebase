"""Example migration: Add column to table.

このファイルは新しいマイグレーションを作成する際の参考例です。
実際のマイグレーションを作成する際は、このファイルをコピーして編集するか、
以下のコマンドで新規作成してください:

    alembic revision -m "説明文"

Revision ID: 002
Revises: 001
Create Date: 2025-01-20
"""

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """マイグレーション: スキーマの変更を適用.

    例: テーブルにカラムを追加する場合
    ```python
    op.execute('''
        ALTER TABLE your_table
        ADD COLUMN new_column VARCHAR(100);
    ''')
    ```

    例: 新しいテーブルを作成する場合
    ```python
    op.execute('''
        CREATE TABLE new_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    ```

    例: インデックスを追加する場合
    ```python
    op.execute('''
        CREATE INDEX idx_your_table_column ON your_table(column_name);
    ''')
    ```
    """
    # このサンプルでは何も実行しません
    # 実際のマイグレーションでは op.execute() でSQLを実行してください
    pass


def downgrade() -> None:
    """ロールバック: upgrade() の変更を元に戻す.

    例: カラムを削除する場合
    ```python
    op.execute('''
        ALTER TABLE your_table
        DROP COLUMN new_column;
    ''')
    ```

    例: テーブルを削除する場合
    ```python
    op.execute('''
        DROP TABLE IF EXISTS new_table;
    ''')
    ```

    例: インデックスを削除する場合
    ```python
    op.execute('''
        DROP INDEX IF EXISTS idx_your_table_column;
    ''')
    ```

    注意: データ損失を伴う可能性のある操作は慎重に実装してください。
    """
    # このサンプルでは何も実行しません
    pass
