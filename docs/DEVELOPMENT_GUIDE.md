# Sagebase 開発ガイド

## 目次

1. [はじめに](#はじめに)
2. [Clean Architecture 概要](#clean-architecture-概要)
3. [開発環境のセットアップ](#開発環境のセットアップ)
4. [新規機能開発の手順](#新規機能開発の手順)
5. [テスト作成のガイドライン](#テスト作成のガイドライン)
6. [コーディング規約](#コーディング規約)
7. [トラブルシューティング](#トラブルシューティング)
8. [参考リソース](#参考リソース)

---

## はじめに

### このガイドについて

このガイドは、Sagebaseプロジェクトで開発を始める新規開発者向けのドキュメントです。Clean Architectureの基本概念、開発環境のセットアップ、実装パターン、テスト作成方法などを網羅しています。

### Sagebaseとは

**Sagebase**は、日本の政治活動を追跡・分析するアプリケーションです。主な機能：

- **議事録処理**: PDFから発言を抽出し、話者をデータベースの政治家とマッチング
- **Web scraping**: 政党Webサイトから政治家情報を収集
- **LLM統合**: Gemini APIを使用した構造化データ抽出（BAML）
- **BI Dashboard**: Plotly Dashによるデータ可視化
- **管理画面**: Streamlitによる管理UI

### 前提知識

このプロジェクトで開発を行うには、以下の知識が推奨されます：

- **Python 3.13**: 型ヒント、async/await、dataclass
- **SQLAlchemy**: ORM、非同期クエリ
- **PostgreSQL**: データベース基礎
- **Docker & Docker Compose**: コンテナ基礎
- **Clean Architecture**: 4層構造、依存性逆転の原則（このガイドで学習可能）

---

## Clean Architecture 概要

### なぜClean Architectureなのか

Sagebaseでは、**Clean Architecture**を採用しています。理由：

1. **ビジネスロジックの独立性**: LLMプロバイダーやデータベースの変更がビジネスロジックに影響しない
2. **テスト容易性**: ドメインロジックを単体テストで検証できる（データベース不要）
3. **長期的な保守性**: 責務が明確で、変更の影響範囲が限定的

詳細は [ADR 0001: Clean Architecture採用](ADR/0001-clean-architecture-adoption.md) を参照。

### 4層構造

```
┌─────────────────────────────────────────────────────────────┐
│ Interface Layer (CLI, Streamlit UI)                         │
│  責務: ユーザーインターフェース、エントリーポイント              │
└───────────────────────┬─────────────────────────────────────┘
                        │ 依存
┌───────────────────────▼─────────────────────────────────────┐
│ Application Layer (Use Cases, DTOs)                         │
│  責務: ビジネスフローの調整、トランザクション管理                │
└───────────────────────┬─────────────────────────────────────┘
                        │ 依存
┌───────────────────────▼─────────────────────────────────────┐
│ Domain Layer (Entities, Domain Services, Repositories)      │
│  責務: ビジネスロジック、ビジネスルール                         │
└───────────────────────▲─────────────────────────────────────┘
                        │ 実装
┌───────────────────────┴─────────────────────────────────────┐
│ Infrastructure Layer (Repository Impl, External Services)   │
│  責務: データベースアクセス、外部サービス統合                   │
└─────────────────────────────────────────────────────────────┘
```

### 依存関係のルール

**重要**: 依存関係は常に**内側（Domain層）に向かう**

- ✅ **Infrastructure層 → Domain層**: リポジトリインターフェースを実装
- ✅ **Application層 → Domain層**: ユースケースがエンティティを操作
- ✅ **Interface層 → Application層**: UIがユースケースを呼び出す
- ❌ **Domain層 → Infrastructure層**: 絶対にNG！

### 各層の役割（簡潔版）

| 層 | 責務 | 例 |
|----|------|-----|
| **Domain** | ビジネスロジック、ビジネスルール | Politicianエンティティ、PoliticianRepository（IF） |
| **Application** | ビジネスフローの調整 | ManagePoliticiansUseCase、CreatePoliticianInputDto |
| **Infrastructure** | 外部システムとの連携 | PoliticianRepositoryImpl、GeminiLLMService |
| **Interface** | ユーザーインターフェース | politicians_view.py、politician_commands.py |

詳細は各層のガイドを参照：
- [DOMAIN_LAYER.md](architecture/DOMAIN_LAYER.md)
- [APPLICATION_LAYER.md](architecture/APPLICATION_LAYER.md)
- [INFRASTRUCTURE_LAYER.md](architecture/INFRASTRUCTURE_LAYER.md)
- [INTERFACE_LAYER.md](architecture/INTERFACE_LAYER.md)

---

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/trust-chain-organization/sagebase.git
cd sagebase
```

### 2. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集
vim .env
```

**必須の環境変数**:

```bash
# Google Gemini API Key（必須）
GOOGLE_API_KEY=your_api_key_here

# データベース接続
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/sagebase

# Google Cloud Storage（オプション）
GCS_BUCKET_NAME=your_bucket_name
GCP_PROJECT_ID=your_project_id
```

### 3. Docker環境の起動

```bash
# すべてのサービスを起動（PostgreSQL、アプリケーション、Streamlit）
just up

# または個別に起動
docker compose up -d
```

### 4. データベースのセットアップ

```bash
# データベースのリセット（初回のみ）
./reset-database.sh

# または手動で
just db  # PostgreSQLに接続
\i database/01_create_database.sql
\i database/02_run_migrations.sql
\i database/03_seed_data.sql
```

### 5. 動作確認

```bash
# Streamlit UIにアクセス
# ブラウザで http://localhost:8501 を開く

# CLIコマンドの実行
docker compose exec app sagebase --help

# テストの実行
just test
```

### 6. 開発用ツールのインストール（ローカル開発の場合）

```bash
# UVでPython環境をセットアップ
uv sync

# Pre-commitフックのインストール
pre-commit install

# VSCode拡張機能（推奨）
# - Python (Microsoft)
# - Pylance (Microsoft)
# - Ruff (Astral Software)
```

---

## 新規機能開発の手順

### ステップ1: 要件の理解

1. **GitHub Issueを確認**: 実装する機能の要件を理解
2. **受入条件を確認**: どのような条件で完了とするか
3. **関連ドキュメントを読む**: 既存の実装パターンを理解

### ステップ2: 設計（どの層に何を実装するか）

#### 2.1 Domain層の設計

**質問**: ビジネスルールは何か？

- 新しいエンティティが必要か？ → `src/domain/entities/`
- 複数エンティティにまたがるロジックか？ → `src/domain/services/`
- データアクセスのインターフェースが必要か？ → `src/domain/repositories/`

**例**: 政治家の重複チェック機能

```python
# src/domain/services/politician_domain_service.py

class PoliticianDomainService:
    def is_duplicate_politician(
        self, politician: Politician, existing: list[Politician]
    ) -> bool:
        """政治家が重複しているかチェック"""
        for e in existing:
            if self._is_name_similar(politician.name, e.name):
                return True
        return False
```

#### 2.2 Application層の設計

**質問**: どのようなビジネスフローか？

- ユースケースは何か？ → `src/application/usecases/`
- 入出力のDTOは何か？ → ユースケースファイル内にInputDto/OutputDto

**例**: 政治家作成ユースケース

```python
# src/application/usecases/manage_politicians_usecase.py

class ManagePoliticiansUseCase:
    async def create_politician(
        self, input_dto: CreatePoliticianInputDto
    ) -> CreatePoliticianOutputDto:
        # 1. 重複チェック（ドメインサービス呼び出し）
        existing = await self.repository.get_by_name_and_party(...)
        if existing:
            return CreatePoliticianOutputDto(
                success=False, error_message="重複しています"
            )

        # 2. エンティティの作成
        politician = Politician(...)

        # 3. 永続化
        created = await self.repository.create(politician)
        return CreatePoliticianOutputDto(success=True, politician_id=created.id)
```

#### 2.3 Infrastructure層の設計

**質問**: どの外部システムと連携するか？

- データベースアクセスか？ → `src/infrastructure/persistence/`
- 外部APIか？ → `src/infrastructure/external/`

**例**: 政治家リポジトリ実装

```python
# src/infrastructure/persistence/politician_repository_impl.py

class PoliticianRepositoryImpl(BaseRepositoryImpl[Politician], PoliticianRepository):
    def _to_entity(self, model: PoliticianModel) -> Politician:
        """Model → Entity 変換"""
        return Politician(id=model.id, name=model.name, ...)

    def _to_model(self, entity: Politician) -> PoliticianModel:
        """Entity → Model 変換"""
        return PoliticianModel(id=entity.id, name=entity.name, ...)
```

#### 2.4 Interface層の設計

**質問**: どのUIが必要か？

- CLIコマンドか？ → `src/interfaces/cli/commands/`
- Streamlit UIか？ → `src/interfaces/web/streamlit/views/` & `presenters/`

**例**: Streamlit UI

```python
# src/interfaces/web/streamlit/views/politicians_view.py

def render_new_politician_tab(presenter: PoliticianPresenter) -> None:
    """新規政治家登録タブ"""
    with st.form("new_politician_form"):
        name = st.text_input("氏名")
        party_id = st.selectbox("政党", ...)

        if st.form_submit_button("登録"):
            result = presenter.create_politician(name, party_id)
            if result.success:
                st.success("✅ 登録しました")
            else:
                st.error(f"❌ {result.error_message}")
```

### ステップ3: 実装

#### 実装の順序（推奨）

1. **Domain層**: エンティティ、リポジトリIF、ドメインサービス
2. **Application層**: ユースケース、DTO
3. **Infrastructure層**: リポジトリ実装、外部サービス
4. **Interface層**: CLI/UI
5. **テスト**: 各層のテスト

#### 実装時の注意点

- **各層の責務を守る**: ビジネスロジックをUI層に書かない
- **依存関係のルールを守る**: Domain層が他の層に依存しない
- **型ヒントを必ず書く**: `def foo(name: str) -> bool:`
- **async/awaitを適切に使う**: すべてのI/O操作は非同期

### ステップ4: テストの作成

各層のテストを作成します。詳細は[テスト作成のガイドライン](#テスト作成のガイドライン)を参照。

### ステップ5: コード品質チェック

```bash
# フォーマット
uv run ruff format .

# リント
uv run ruff check . --fix

# 型チェック
uv run pyright

# テスト実行
uv run pytest -xvs
```

### ステップ6: コミットとプルリクエスト

```bash
# 変更をステージング
git add .

# コミット（pre-commitフックが自動実行）
git commit -m "feat: 政治家重複チェック機能を追加"

# プッシュ
git push origin feature/politician-duplicate-check

# GitHub上でプルリクエストを作成
```

---

## テスト作成のガイドライン

### テスト戦略

Sagebaseでは、以下のテスト戦略を採用しています：

| テスト種別 | 対象 | 実行速度 | 外部依存 |
|-----------|------|---------|---------|
| **単体テスト** | Domain層、Application層 | 高速 | なし（モック） |
| **統合テスト** | Infrastructure層 | 中速 | あり（DB） |
| **E2Eテスト** | Interface層 | 低速 | あり（DB、外部API） |

### Domain層のテスト

**特徴**: 外部依存なし、高速

```python
# tests/domain/services/test_politician_domain_service.py

import pytest
from src.domain.entities.politician import Politician
from src.domain.services.politician_domain_service import PoliticianDomainService


def test_is_duplicate_politician_完全一致():
    """政治家名が完全一致する場合、重複と判定される"""
    # Arrange
    service = PoliticianDomainService()
    politician = Politician(id=None, name="山田太郎", party_id=1)
    existing = [Politician(id=1, name="山田太郎", party_id=1)]

    # Act
    result = service.is_duplicate_politician(politician, existing)

    # Assert
    assert result is True


def test_is_duplicate_politician_類似():
    """政治家名が類似する場合、重複と判定される"""
    # Arrange
    service = PoliticianDomainService()
    politician = Politician(id=None, name="山田太郎", party_id=1)
    existing = [Politician(id=1, name="山田　太郎", party_id=1)]  # 全角スペース

    # Act
    result = service.is_duplicate_politician(politician, existing)

    # Assert
    assert result is True
```

### Application層のテスト

**特徴**: リポジトリをモック、高速

```python
# tests/application/usecases/test_manage_politicians_usecase.py

import pytest
from unittest.mock import AsyncMock
from src.application.usecases.manage_politicians_usecase import (
    ManagePoliticiansUseCase,
    CreatePoliticianInputDto,
)
from src.domain.entities.politician import Politician


@pytest.mark.asyncio
async def test_create_politician_成功():
    """政治家の新規作成が成功する"""
    # Arrange
    mock_repository = AsyncMock()
    mock_repository.get_by_name_and_party.return_value = None  # 重複なし
    mock_repository.create.return_value = Politician(id=1, name="山田太郎", party_id=1)

    use_case = ManagePoliticiansUseCase(mock_repository)
    input_dto = CreatePoliticianInputDto(name="山田太郎", party_id=1)

    # Act
    result = await use_case.create_politician(input_dto)

    # Assert
    assert result.success is True
    assert result.politician_id == 1
    mock_repository.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_politician_重複エラー():
    """同名の政治家が存在する場合、エラーになる"""
    # Arrange
    mock_repository = AsyncMock()
    mock_repository.get_by_name_and_party.return_value = Politician(
        id=1, name="山田太郎", party_id=1
    )  # 重複あり

    use_case = ManagePoliticiansUseCase(mock_repository)
    input_dto = CreatePoliticianInputDto(name="山田太郎", party_id=1)

    # Act
    result = await use_case.create_politician(input_dto)

    # Assert
    assert result.success is False
    assert "重複" in result.error_message
```

### Infrastructure層のテスト

**特徴**: データベース接続あり、中速

```python
# tests/infrastructure/persistence/test_politician_repository_impl.py

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.politician import Politician
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)


@pytest.mark.asyncio
async def test_create_politician(async_session: AsyncSession):
    """政治家を作成できる"""
    # Arrange
    repository = PoliticianRepositoryImpl(async_session)
    politician = Politician(id=None, name="山田太郎", party_id=1)

    # Act
    created = await repository.create(politician)
    await async_session.commit()

    # Assert
    assert created.id is not None
    assert created.name == "山田太郎"

    # Cleanup
    await repository.delete(created.id)
    await async_session.commit()
```

### テスト作成時の注意点

1. **外部サービスは必ずモック**: LLM API、GCS、Webスクレイピングなどは本物を呼ばない
2. **テストの独立性**: 各テストは他のテストに依存しない
3. **テスト名は日本語OK**: `test_create_politician_成功()`
4. **Arrange-Act-Assert**: テストの構造を明確にする
5. **pytest-asyncio**: 非同期テストは`@pytest.mark.asyncio`を使用

詳細は [.claude/skills/test-writer/](../.claude/skills/test-writer/) を参照。

---

## コーディング規約

### Python スタイル

- **フォーマッター**: Ruff（自動フォーマット）
- **リンター**: Ruff（自動チェック）
- **型チェッカー**: Pyright
- **行の長さ**: 最大100文字（Ruff設定）

### 命名規則

| 対象 | 規則 | 例 |
|------|------|-----|
| クラス名 | PascalCase | `PoliticianRepository` |
| 関数名 | snake_case | `get_by_id()` |
| 変数名 | snake_case | `politician_id` |
| 定数 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| プライベート | `_`プレフィックス | `_to_entity()` |

### 型ヒント

**すべての関数に型ヒントを書く**:

```python
# ✅ 良い例
def get_politician_by_id(politician_id: int) -> Politician | None:
    ...

async def create_politician(politician: Politician) -> Politician:
    ...

# ❌ 悪い例（型ヒントなし）
def get_politician_by_id(politician_id):
    ...
```

### 非同期処理

**すべてのI/O操作は非同期**:

```python
# ✅ 良い例
async def get_by_id(self, entity_id: int) -> Politician | None:
    result = await self.session.get(PoliticianModel, entity_id)
    return self._to_entity(result) if result else None

# ❌ 悪い例（同期処理）
def get_by_id(self, entity_id: int) -> Politician | None:
    result = self.session.query(PoliticianModel).filter_by(id=entity_id).first()
    return self._to_entity(result) if result else None
```

### ドキュメント文字列

**すべてのパブリック関数にdocstringを書く**:

```python
def is_duplicate_politician(
    self, politician: Politician, existing: list[Politician]
) -> bool:
    """政治家が重複しているかチェックする

    Args:
        politician: チェック対象の政治家
        existing: 既存の政治家リスト

    Returns:
        重複している場合True、それ以外はFalse
    """
    ...
```

### インポート順序

```python
# 1. 標準ライブラリ
import os
from datetime import datetime

# 2. サードパーティライブラリ
from sqlalchemy import select
import streamlit as st

# 3. ローカルモジュール（src.から始まる）
from src.domain.entities.politician import Politician
from src.application.usecases.manage_politicians_usecase import ManagePoliticiansUseCase
```

### コミットメッセージ

**Conventional Commits**に従う:

```bash
# 新機能
git commit -m "feat: 政治家重複チェック機能を追加"

# バグ修正
git commit -m "fix: 話者マッチングの信頼度計算を修正"

# リファクタリング
git commit -m "refactor: PoliticianRepositoryをClean Architectureに移行"

# ドキュメント
git commit -m "docs: DEVELOPMENT_GUIDE.mdを追加"

# テスト
git commit -m "test: PoliticianDomainServiceのテストを追加"
```

---

## トラブルシューティング

### よくある問題と解決策

#### 1. Docker コンテナが起動しない

**症状**: `docker compose up` が失敗する

**解決策**:

```bash
# コンテナとボリュームをすべて削除
docker compose down -v

# イメージを再ビルド
docker compose build --no-cache

# 再起動
docker compose up -d
```

#### 2. データベース接続エラー

**症状**: `sqlalchemy.exc.OperationalError: could not connect to server`

**解決策**:

```bash
# データベースコンテナが起動しているか確認
docker compose ps

# データベースログを確認
docker compose logs db

# データベースコンテナを再起動
docker compose restart db
```

#### 3. GOOGLE_API_KEY エラー

**症状**: `ValueError: Google API key is required`

**解決策**:

```bash
# .envファイルにGoogle API keyを設定
echo "GOOGLE_API_KEY=your_actual_api_key" >> .env

# コンテナを再起動（環境変数を再読み込み）
docker compose restart app
```

#### 4. BAML クライアント生成エラー

**症状**: `baml_client` モジュールが見つからない

**解決策**:

```bash
# BAMLクライアントを再生成
docker compose exec app uv run baml-cli generate

# または手動で
cd baml_src
uv run baml-cli generate --output ../baml_client
```

#### 5. マイグレーションエラー

**症状**: データベーススキーマが古い

**解決策**:

```bash
# データベースをリセット
./reset-database.sh

# または手動で
just db
\i database/02_run_migrations.sql
```

#### 6. テスト失敗（外部サービス）

**症状**: テストで実際のLLM APIを呼んでしまう

**解決策**:

```python
# テストで外部サービスをモック
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm_service():
    mock = AsyncMock()
    mock.match_speaker_to_politician.return_value = LLMMatchResult(
        matched=True, confidence=0.95, matched_id=1, reason="完全一致"
    )
    return mock

async def test_with_mock(mock_llm_service):
    # モックを使用してテスト
    result = await mock_llm_service.match_speaker_to_politician(...)
    assert result.matched is True
```

---

## 参考リソース

### プロジェクトドキュメント

#### アーキテクチャ

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 全体アーキテクチャの詳細
- **[CLEAN_ARCHITECTURE_MIGRATION.md](CLEAN_ARCHITECTURE_MIGRATION.md)** - Clean Architecture移行の進捗

#### 各層のガイド

- **[DOMAIN_LAYER.md](architecture/DOMAIN_LAYER.md)** - Domain層の実装ガイド
- **[APPLICATION_LAYER.md](architecture/APPLICATION_LAYER.md)** - Application層の実装ガイド
- **[INFRASTRUCTURE_LAYER.md](architecture/INFRASTRUCTURE_LAYER.md)** - Infrastructure層の実装ガイド
- **[INTERFACE_LAYER.md](architecture/INTERFACE_LAYER.md)** - Interface層の実装ガイド

#### ADR（アーキテクチャ決定記録）

- **[ADR 0001: Clean Architecture採用](ADR/0001-clean-architecture-adoption.md)**
- **[ADR 0002: BAML for LLM Outputs](ADR/0002-baml-for-llm-outputs.md)**
- **[ADR 0003: リポジトリパターン](ADR/0003-repository-pattern.md)**

#### その他のドキュメント

- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - データベーススキーマの詳細
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - テスト戦略とベストプラクティス
- **[BI_DASHBOARD.md](BI_DASHBOARD.md)** - BI Dashboardのセットアップと使用方法

### スキル（Claude Code）

- **[clean-architecture-checker](../.claude/skills/clean-architecture-checker/)** - Clean Architecture原則のチェック
- **[test-writer](../.claude/skills/test-writer/)** - テスト作成ガイド
- **[migration-helper](../.claude/skills/migration-helper/)** - データベースマイグレーション支援
- **[baml-integration](../.claude/skills/baml-integration/)** - BAML統合ガイド

### 外部リソース

#### Clean Architecture

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - 原典
- [Architecture Patterns with Python](https://www.cosmicpython.com/) - Pythonでの実装例

#### Python

- [Python 3.13 Documentation](https://docs.python.org/3.13/)
- [Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

#### フレームワーク・ライブラリ

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Click Documentation](https://click.palletsprojects.com/)
- [BAML Documentation](https://docs.boundaryml.com/)
- [LangChain Documentation](https://python.langchain.com/)

---

## まとめ

このガイドでは、Sagebaseプロジェクトでの開発に必要な基本的な知識と手順を説明しました。

### 重要なポイント

1. **Clean Architectureの原則を守る**: 各層の責務を理解し、依存関係のルールに従う
2. **テストを書く**: すべての層でテストを作成し、品質を担保する
3. **コーディング規約を守る**: Ruff、Pyright、Pre-commitフックを活用
4. **ドキュメントを読む**: 各層のガイド、ADR、スキルを活用

### 困ったときは

- **ドキュメントを確認**: 各層のガイド、ADRを読む
- **コード例を見る**: 既存の実装を参考にする
- **スキルを活用**: Claude Codeのスキル（clean-architecture-checker、test-writerなど）を使用
- **質問する**: チームメンバーに相談

Happy Coding! 🚀
