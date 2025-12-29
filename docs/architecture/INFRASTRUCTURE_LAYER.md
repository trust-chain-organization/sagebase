# Infrastructure Layer（インフラストラクチャ層）

## 目次

1. [層の責務と境界](#層の責務と境界)
2. [リポジトリ実装](#リポジトリ実装)
3. [外部サービス統合](#外部サービス統合)
4. [データベースマッピング](#データベースマッピング)
5. [よくある落とし穴と回避方法](#よくある落とし穴と回避方法)
6. [チェックリスト](#チェックリスト)
7. [参考資料](#参考資料)

---

## 層の責務と境界

### 責務

Infrastructure層は、外部システムとの連携およびフレームワーク依存の実装を担当します：

- **リポジトリインターフェースの実装**: Domain層で定義されたリポジトリインターフェースを具体的に実装
- **外部サービスとの統合**: LLM、ストレージ、Webスクレイピングなどの外部サービスとの連携
- **データベースマッピング**: ドメインエンティティとデータベースモデルの変換
- **フレームワーク依存の実装**: SQLAlchemy、LangChain、Playwrightなどのフレームワーク固有の実装

### 境界

Infrastructure層は**最も外側の層**であり、すべての技術的詳細を実装します：

```
Domain ← Application ← Infrastructure
```

**依存関係のルール**:
- **Infrastructure層がDomain層に依存**: リポジトリインターフェースや外部サービスインターフェースを実装
- **Infrastructure層がApplication層に依存することもある**: 特定のユースケースで必要な場合のみ
- **Domain層やApplication層がInfrastructure層に依存してはならない**: 依存性逆転の原則（DIP）

### ディレクトリ構造

```
src/infrastructure/
├── persistence/              # データベース永続化
│   ├── base_repository_impl.py
│   ├── politician_repository_impl.py
│   ├── speaker_repository_impl.py
│   ├── sqlalchemy_models.py  # SQLAlchemyモデル
│   └── ...
├── external/                 # 外部サービス統合
│   ├── llm_service.py       # Gemini LLM実装
│   ├── gcs_storage_service.py
│   ├── web_scraper_service.py
│   └── ...
└── adapters/                 # アダプター実装
    └── ...
```

---

## リポジトリ実装

### BaseRepositoryImpl パターン

すべてのリポジトリ実装は`BaseRepositoryImpl[T]`を継承します。このパターンにより、共通のCRUD操作を統一的に実装できます。

#### 実装例

```python
# src/infrastructure/persistence/base_repository_impl.py

from typing import Any
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.entities.base import BaseEntity
from src.domain.repositories.base import BaseRepository
from src.domain.repositories.session_adapter import ISessionAdapter


class BaseRepositoryImpl[T: BaseEntity](BaseRepository[T]):
    """Base repository implementation using ISessionAdapter.

    This class provides generic CRUD operations using the ISessionAdapter
    interface, enabling dependency inversion and testability.

    Type Parameters:
        T: Domain entity type that extends BaseEntity

    Attributes:
        session: Database session (AsyncSession or ISessionAdapter)
        entity_class: Domain entity class for type conversions
        model_class: Database model class for ORM operations
    """

    def __init__(
        self,
        session: AsyncSession | ISessionAdapter,
        entity_class: type[T],
        model_class: type[Any],
    ):
        self.session = session
        self.entity_class = entity_class
        self.model_class = model_class

    async def get_by_id(self, entity_id: int) -> T | None:
        """Get entity by ID."""
        result = await self.session.get(self.model_class, entity_id)
        if result:
            return self._to_entity(result)
        return None

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[T]:
        """Get all entities with optional pagination."""
        query = select(self.model_class)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        # Get existing model
        model = await self.session.get(self.model_class, entity.id)
        if not model:
            raise ValueError(f"Entity with ID {entity.id} not found")

        # Update fields
        self._update_model(model, entity)

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        model = await self.session.get(self.model_class, entity_id)
        if not model:
            return False

        await self.session.delete(model)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Count total number of entities."""
        query = select(func.count()).select_from(self.model_class)
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _to_entity(self, model: Any) -> T:
        """Convert database model to domain entity."""
        raise NotImplementedError("Subclass must implement _to_entity")

    def _to_model(self, entity: T) -> Any:
        """Convert domain entity to database model."""
        raise NotImplementedError("Subclass must implement _to_model")

    def _update_model(self, model: Any, entity: T) -> None:
        """Update model fields from entity."""
        raise NotImplementedError("Subclass must implement _update_model")
```

### ISessionAdapter の使用

`ISessionAdapter`は、Domain層で定義されたデータベースセッション操作のインターフェースです。Infrastructure層はこのインターフェースを実装します。

#### ISessionAdapter インターフェース

```python
# src/domain/repositories/session_adapter.py

from abc import ABC, abstractmethod
from typing import Any


class ISessionAdapter(ABC):
    """Abstract interface for database session operations.

    This is a domain port that defines the contract for session management.
    The infrastructure layer provides concrete implementations (adapters).

    This interface enables:
    - Dependency Inversion: Domain defines needs, infrastructure implements
    - Testability: Easy to create mock implementations for testing
    - Flexibility: Can swap implementations without changing domain code
    """

    @abstractmethod
    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> Any:
        """Execute a database statement."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the session."""
        pass

    @abstractmethod
    def add(self, instance: Any) -> None:
        """Add an instance to the session."""
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Flush pending changes to the database."""
        pass

    @abstractmethod
    async def refresh(self, instance: Any) -> None:
        """Refresh an instance from the database."""
        pass

    @abstractmethod
    async def get(self, entity_type: Any, entity_id: Any) -> Any | None:
        """Get an entity by its primary key."""
        pass

    @abstractmethod
    async def delete(self, instance: Any) -> None:
        """Delete an instance from the session."""
        pass
```

**重要なポイント**:
- `ISessionAdapter`はDomain層で定義される（ポート）
- Infrastructure層がこのインターフェースを実装する（アダプター）
- これにより、Domain層がSQLAlchemyなどの具体的な実装に依存しない

### Entity ↔ Model 変換

リポジトリ実装の核心は、ドメインエンティティとデータベースモデルの変換です。

#### 具体的な実装例: PoliticianRepositoryImpl

```python
# src/infrastructure/persistence/politician_repository_impl.py（抜粋）

from src.domain.entities.politician import Politician
from src.domain.repositories.politician_repository import PoliticianRepository
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class PoliticianRepositoryImpl(BaseRepositoryImpl[Politician], PoliticianRepository):
    """Politician repository implementation."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        # PoliticianModelはSQLAlchemyモデル
        super().__init__(session, Politician, PoliticianModel)

    # Entity → Model 変換
    def _to_model(self, entity: Politician) -> PoliticianModel:
        """Convert Politician entity to PoliticianModel."""
        return PoliticianModel(
            id=entity.id,
            name=entity.name,
            name_furigana=entity.name_furigana,
            party_id=entity.party_id,
            district=entity.district,
            bio=entity.bio,
            image_url=entity.image_url,
            website_url=entity.website_url,
            email=entity.email,
            phone=entity.phone,
            birth_date=entity.birth_date,
            gender=entity.gender,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    # Model → Entity 変換
    def _to_entity(self, model: PoliticianModel) -> Politician:
        """Convert PoliticianModel to Politician entity."""
        return Politician(
            id=model.id,
            name=model.name,
            name_furigana=model.name_furigana,
            party_id=model.party_id,
            district=model.district,
            bio=model.bio,
            image_url=model.image_url,
            website_url=model.website_url,
            email=model.email,
            phone=model.phone,
            birth_date=model.birth_date,
            gender=model.gender,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # Entity の変更を Model に反映
    def _update_model(self, model: PoliticianModel, entity: Politician) -> None:
        """Update PoliticianModel from Politician entity."""
        model.name = entity.name
        model.name_furigana = entity.name_furigana
        model.party_id = entity.party_id
        model.district = entity.district
        model.bio = entity.bio
        model.image_url = entity.image_url
        model.website_url = entity.website_url
        model.email = entity.email
        model.phone = model.phone
        model.birth_date = entity.birth_date
        model.gender = entity.gender
        # created_at, updated_atはデータベース側で管理

    # カスタムメソッドの実装
    async def get_by_name_and_party(
        self, name: str, party_id: int | None
    ) -> Politician | None:
        """Get politician by name and party."""
        query = select(PoliticianModel).where(PoliticianModel.name == name)
        if party_id is not None:
            query = query.where(PoliticianModel.party_id == party_id)

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None
```

**変換パターンのポイント**:
- **`_to_model(entity)`**: エンティティをモデルに変換（作成時に使用）
- **`_to_entity(model)`**: モデルをエンティティに変換（取得時に使用）
- **`_update_model(model, entity)`**: 既存のモデルをエンティティの値で更新（更新時に使用）

### 非同期処理 (async/await)

すべてのリポジトリメソッドは非同期で実装されます：

```python
async def get_by_id(self, entity_id: int) -> T | None:
    """非同期でエンティティを取得"""
    result = await self.session.get(self.model_class, entity_id)
    if result:
        return self._to_entity(result)
    return None
```

**重要なポイント**:
- データベース操作はすべて`async`/`await`を使用
- `AsyncSession`を使用してSQLAlchemyの非同期操作を実行
- トランザクション管理も非同期（`commit`, `rollback`, `flush`）

---

## 外部サービス統合

Infrastructure層は、外部サービスとの連携を実装します。各サービスはDomain層で定義されたインターフェースを実装します。

### アダプターパターン

外部サービスの統合には**アダプターパターン**を使用します：

```
Domain Layer (Interface) → Infrastructure Layer (Implementation)
```

### LLMサービスの実装

#### ILLMService インターフェース

Domain層で定義されたインターフェース：

```python
# src/domain/services/interfaces/llm_service.py

from abc import ABC, abstractmethod
from typing import Any


class ILLMService(ABC):
    """LLM service interface."""

    @abstractmethod
    async def match_speaker_to_politician(
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match speaker to politician using LLM."""
        pass

    @abstractmethod
    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract politician information from HTML."""
        pass
```

#### GeminiLLMService 実装

Infrastructure層での実装：

```python
# src/infrastructure/external/llm_service.py

from langchain_google_genai import ChatGoogleGenerativeAI
from src.domain.services.interfaces.llm_service import ILLMService


class GeminiLLMService(ILLMService):
    """Gemini-based implementation of LLM service."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.1,
    ):
        """Initialize Gemini LLM service.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model_name: Name of the Gemini model to use
            temperature: Temperature for generation
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")

        self.model_name = model_name
        self.temperature = temperature

        # Initialize Gemini client (LangChain)
        self._llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=self.api_key,
        )

    async def match_speaker_to_politician(
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match speaker to politician using Gemini."""
        try:
            # プロンプトの準備
            prompt = self._create_matching_prompt(context)

            # LangChainを使用してLLMを呼び出し
            prompt_template = ChatPromptTemplate.from_template(prompt)
            chain = prompt_template | self._llm
            response = await chain.ainvoke({})

            # レスポンスをパース
            result = json.loads(response.content)

            return LLMMatchResult(
                matched=result.get("matched", False),
                confidence=result.get("confidence", 0.0),
                reason=result.get("reason", ""),
                matched_id=result.get("matched_id"),
                metadata={"model": self.model_name},
            )
        except Exception as e:
            logger.error(f"Failed to match speaker: {e}")
            return None
```

**実装のポイント**:
- **フレームワーク依存の隠蔽**: LangChainの詳細はInfrastructure層内に限定
- **環境変数の管理**: API keyなどの認証情報は環境変数から取得
- **エラーハンドリング**: 外部APIの失敗を適切に処理
- **ログ記録**: 処理の追跡のためにログを記録

### ストレージサービスの実装

#### GCSStorageService 実装

```python
# src/infrastructure/external/gcs_storage_service.py

import asyncio
from src.domain.services.interfaces.storage_service import IStorageService
from src.utils.gcs_storage import GCSStorage


class GCSStorageService(IStorageService):
    """GCS implementation of storage service."""

    def __init__(self, bucket_name: str, project_id: str | None = None):
        """Initialize GCS storage service.

        Args:
            bucket_name: GCS bucket name
            project_id: GCP project ID (optional)
        """
        self._gcs = GCSStorage(bucket_name=bucket_name, project_id=project_id)

    async def download_file(self, uri: str) -> bytes:
        """Download file from storage.

        Args:
            uri: Storage URI (e.g., gs://bucket/path/to/file)

        Returns:
            Content as bytes
        """
        # GCSStorage.download_content is sync, so wrap it in asyncio.to_thread
        content = await asyncio.to_thread(self._gcs.download_content, uri)
        if content is None:
            raise ValueError(f"Failed to download content from {uri}")
        return content.encode("utf-8")

    async def upload_file(
        self, file_path: str, content: bytes, content_type: str | None = None
    ) -> str:
        """Upload file to storage."""
        content_str = content.decode("utf-8")
        return await asyncio.to_thread(self._gcs.upload_content, content_str, file_path)
```

**実装のポイント**:
- **同期→非同期の変換**: `asyncio.to_thread`を使用してブロッキング操作を非同期化
- **URIの抽象化**: GCS固有のURI（`gs://`）をサービスインターフェースで隠蔽
- **エラーハンドリング**: ファイルが見つからない場合などの適切な例外処理

---

## データベースマッピング

### SQLAlchemyモデル

Infrastructure層では、SQLAlchemyを使用してデータベーステーブルをマッピングします。

#### モデルの定義例

```python
# src/infrastructure/persistence/sqlalchemy_models.py

from datetime import date, datetime
from uuid import UUID
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class ParliamentaryGroupMembershipModel(Base):
    """SQLAlchemy model for parliamentary_group_memberships table."""

    __tablename__ = "parliamentary_group_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(
        ForeignKey("politicians.id", use_alter=True, name="fk_pgm_politician")
    )
    parliamentary_group_id: Mapped[int] = mapped_column(
        ForeignKey("parliamentary_groups.id", use_alter=True, name="fk_pgm_group")
    )
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    role: Mapped[str | None] = mapped_column(String(100))
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id", use_alter=True, name="fk_pgm_user")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="chk_membership_end_date_after_start",
        ),
    )
```

**モデル定義のポイント**:
- **`Mapped[T]` 型アノテーション**: SQLAlchemy 2.0の型安全な定義方法
- **外部キー制約**: `ForeignKey`を使用してリレーションを定義
- **制約の定義**: `CheckConstraint`でビジネスルールを強制
- **タイムスタンプ管理**: `default`と`onupdate`で自動更新

### エンティティとモデルの分離

**重要な原則**: ドメインエンティティとデータベースモデルは**分離**します。

| 概念 | 層 | 役割 |
|------|-----|------|
| **エンティティ** | Domain層 | ビジネスロジックを持つドメインオブジェクト |
| **モデル** | Infrastructure層 | データベーステーブルのマッピング |

**分離する理由**:
1. **依存性逆転の原則**: Domain層がInfrastructure層（SQLAlchemy）に依存しない
2. **ビジネスロジックの保護**: データベーススキーマの変更がビジネスロジックに影響しない
3. **テスト容易性**: エンティティ単体でテスト可能

#### 悪い例（アンチパターン）

```python
# ❌ エンティティにSQLAlchemyの依存を持ち込む（悪い例）

from sqlalchemy.orm import Mapped, mapped_column

class Politician(BaseEntity):  # ❌ Domain層のエンティティ
    __tablename__ = "politicians"  # ❌ SQLAlchemy依存

    id: Mapped[int] = mapped_column(primary_key=True)  # ❌ SQLAlchemy依存
```

#### 良い例

```python
# ✅ Domain層: エンティティ（フレームワーク非依存）
class Politician(BaseEntity):
    def __init__(self, id: int | None, name: str, party_id: int | None):
        super().__init__(id)
        self.name = name
        self.party_id = party_id

# ✅ Infrastructure層: モデル（SQLAlchemy依存）
class PoliticianModel(Base):
    __tablename__ = "politicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    party_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"))
```

### マイグレーション管理

データベーススキーマの変更は、SQLマイグレーションファイルで管理します。

#### マイグレーションファイルの配置

```
database/
├── migrations/
│   ├── 001_create_initial_tables.sql
│   ├── 002_add_party_table.sql
│   ├── 013_create_llm_processing_history.sql
│   └── ...
└── 02_run_migrations.sql  # マイグレーション実行スクリプト
```

#### マイグレーション追加の手順

1. **新しいマイグレーションファイルを作成**:
   ```sql
   -- database/migrations/014_add_politician_email.sql
   ALTER TABLE politicians ADD COLUMN email VARCHAR(255);
   ```

2. **`02_run_migrations.sql`に追加**:
   ```sql
   -- マイグレーションを順番に実行
   \i migrations/001_create_initial_tables.sql
   \i migrations/002_add_party_table.sql
   ...
   \i migrations/014_add_politician_email.sql  -- 追加
   ```

3. **SQLAlchemyモデルを更新**:
   ```python
   class PoliticianModel(Base):
       # ...
       email: Mapped[str | None] = mapped_column(String(255))  # 追加
   ```

**重要**: マイグレーションは必ず`02_run_migrations.sql`に追加してください。追加しないと本番環境との不整合が発生します。

---

## よくある落とし穴と回避方法

### 1. ドメイン層への依存の逆転

#### 問題

Domain層のエンティティがSQLAlchemyなどのインフラストラクチャ層の技術に依存してしまう。

#### 悪い例

```python
# ❌ Domain層のエンティティがSQLAlchemyに依存（悪い例）
from sqlalchemy.orm import Mapped, mapped_column

class Politician(BaseEntity):
    id: Mapped[int] = mapped_column(primary_key=True)  # ❌ インフラ層への依存
```

#### 良い例

```python
# ✅ Domain層: 純粋なPythonクラス
class Politician(BaseEntity):
    def __init__(self, id: int | None, name: str):
        super().__init__(id)
        self.name = name

# ✅ Infrastructure層: SQLAlchemyモデル
class PoliticianModel(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
```

**解決策**:
- エンティティとモデルを完全に分離
- Infrastructure層でEntity ↔ Model変換を実装

---

### 2. フレームワーク型の漏洩

#### 問題

SQLAlchemyのモデルクラスをDomain層やApplication層に渡してしまう。

#### 悪い例

```python
# ❌ SQLAlchemyモデルをApplication層に公開（悪い例）
class PoliticianRepositoryImpl(PoliticianRepository):
    async def get_by_id(self, entity_id: int) -> PoliticianModel:  # ❌ モデルを返す
        return await self.session.get(PoliticianModel, entity_id)
```

#### 良い例

```python
# ✅ ドメインエンティティを返す
class PoliticianRepositoryImpl(PoliticianRepository):
    async def get_by_id(self, entity_id: int) -> Politician | None:  # ✅ エンティティを返す
        model = await self.session.get(PoliticianModel, entity_id)
        if model:
            return self._to_entity(model)  # モデル→エンティティ変換
        return None
```

**解決策**:
- リポジトリメソッドは常にドメインエンティティを返す
- モデルはリポジトリ内部でのみ使用

---

### 3. N+1問題

#### 問題

複数のエンティティを取得する際に、関連データを個別にクエリしてしまう。

#### 悪い例

```python
# ❌ N+1問題が発生（悪い例）
async def get_all_politicians_with_party(self) -> list[Politician]:
    politicians = await self.get_all()

    for politician in politicians:
        # 各政治家ごとにパーティ情報を取得（N回のクエリ）
        politician.party = await self.party_repository.get_by_id(politician.party_id)

    return politicians
```

#### 良い例

```python
# ✅ JOIN を使用して一度にデータを取得
async def get_all_politicians_with_party(self) -> list[Politician]:
    query = (
        select(PoliticianModel, PartyModel)
        .join(PartyModel, PoliticianModel.party_id == PartyModel.id)
    )

    result = await self.session.execute(query)

    politicians = []
    for politician_model, party_model in result:
        politician = self._to_entity(politician_model)
        politician.party = self._party_to_entity(party_model)
        politicians.append(politician)

    return politicians
```

**解決策**:
- SQLAlchemyの`join()`を使用して関連データを一度に取得
- `selectinload()`や`joinedload()`を使用した遅延読み込み
- 必要なデータのみを事前に取得（Eager Loading）

---

### 4. トランザクション管理の不備

#### 問題

複数の操作を行う際に、トランザクション境界が不明確。

#### 悪い例

```python
# ❌ トランザクション管理が不明確（悪い例）
async def create_politician_with_membership(
    self, politician: Politician, group_id: int
) -> Politician:
    created_politician = await self.politician_repository.create(politician)
    # ここで例外が発生すると、politicianだけが作成されてしまう
    await self.membership_repository.create(
        Membership(politician_id=created_politician.id, group_id=group_id)
    )
    return created_politician
```

#### 良い例

```python
# ✅ ユースケース層でトランザクションを明示的に管理
async def create_politician_with_membership(
    self, input_dto: CreatePoliticianWithMembershipInputDto
) -> CreatePoliticianOutputDto:
    try:
        # トランザクション開始（セッション管理）
        politician = Politician(...)
        created_politician = await self.politician_repository.create(politician)

        membership = Membership(
            politician_id=created_politician.id,
            group_id=input_dto.group_id
        )
        await self.membership_repository.create(membership)

        # すべて成功したらコミット（ユースケース層で管理）
        await self.session.commit()

        return CreatePoliticianOutputDto(success=True, politician_id=created_politician.id)
    except Exception as e:
        # エラー時はロールバック
        await self.session.rollback()
        return CreatePoliticianOutputDto(success=False, error_message=str(e))
```

**解決策**:
- トランザクション境界をApplication層（ユースケース）で管理
- リポジトリ層では`flush()`を使用し、コミットはユースケース層に任せる
- エラー時は確実にロールバックする

---

### 5. 同期コードと非同期コードの混在

#### 問題

非同期データベース操作に同期コードを混ぜてしまう。

#### 悪い例

```python
# ❌ 同期的なブロッキング操作（悪い例）
async def download_and_save(self, uri: str) -> bool:
    content = self._gcs.download_content(uri)  # ❌ ブロッキング操作
    # 非同期処理をブロックしてしまう
```

#### 良い例

```python
# ✅ 同期操作を非同期化
async def download_and_save(self, uri: str) -> bool:
    # asyncio.to_thread でブロッキング操作を非同期化
    content = await asyncio.to_thread(self._gcs.download_content, uri)
    return True
```

**解決策**:
- すべてのI/O操作は`async`/`await`を使用
- 同期的なサードパーティライブラリは`asyncio.to_thread()`でラップ
- 非同期セッション（`AsyncSession`）を使用

---

## チェックリスト

新しいリポジトリ実装やサービス実装を行う際は、以下をチェックしてください：

### リポジトリ実装

- [ ] `BaseRepositoryImpl[T]`を継承している
- [ ] `_to_entity()`, `_to_model()`, `_update_model()`の3つの変換メソッドを実装している
- [ ] Domain層で定義されたリポジトリインターフェースを実装している
- [ ] `ISessionAdapter`または`AsyncSession`を使用している
- [ ] すべてのメソッドが`async`/`await`を使用している
- [ ] エンティティとモデルが完全に分離されている
- [ ] SQLAlchemyの型（`Mapped`など）がDomain層に漏れていない
- [ ] カスタムクエリメソッドがリポジトリインターフェースで定義されている

### 外部サービス実装

- [ ] Domain層で定義されたサービスインターフェースを実装している
- [ ] フレームワーク依存の詳細がInfrastructure層内に隠蔽されている
- [ ] 環境変数から設定を取得している（APIキーなど）
- [ ] 適切なエラーハンドリングとログ記録を実装している
- [ ] 非同期操作（`async`/`await`）を使用している
- [ ] 外部サービスの型がDomain層に漏れていない

### データベースマッピング

- [ ] SQLAlchemyモデルが`Base`を継承している
- [ ] `__tablename__`が定義されている
- [ ] カラムに`Mapped[T]`型アノテーションを使用している
- [ ] 外部キー制約が適切に定義されている
- [ ] 制約（`CheckConstraint`など）が必要に応じて定義されている
- [ ] タイムスタンプ（`created_at`, `updated_at`）が自動管理されている

### マイグレーション

- [ ] 新しいマイグレーションファイルが`database/migrations/`に作成されている
- [ ] マイグレーションファイルが`02_run_migrations.sql`に追加されている
- [ ] マイグレーションの実行順序が正しい
- [ ] SQLAlchemyモデルがマイグレーションと一致している

### トランザクション管理

- [ ] トランザクション境界がユースケース層で管理されている
- [ ] リポジトリ層では`flush()`を使用し、コミットは外部に任せている
- [ ] エラー時のロールバック処理が実装されている

---

## 参考資料

### 関連ドキュメント

- [DOMAIN_LAYER.md](DOMAIN_LAYER.md) - Domain層の詳細ガイド
- [APPLICATION_LAYER.md](APPLICATION_LAYER.md) - Application層の詳細ガイド
- [INTERFACE_LAYER.md](INTERFACE_LAYER.md) - Interface層の詳細ガイド
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) - 全体的なアーキテクチャドキュメント
- [docs/DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) - データベーススキーマの詳細

### コード例

- `src/infrastructure/persistence/base_repository_impl.py` - ジェネリックリポジトリ実装
- `src/infrastructure/persistence/politician_repository_impl.py` - 具体的なリポジトリ実装例
- `src/infrastructure/external/llm_service.py` - LLMサービス実装例
- `src/infrastructure/external/gcs_storage_service.py` - ストレージサービス実装例
- `src/domain/repositories/session_adapter.py` - ISessionAdapterインターフェース
- `src/infrastructure/persistence/sqlalchemy_models.py` - SQLAlchemyモデル定義

### 外部リソース

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [LangChain Documentation](https://python.langchain.com/)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

## まとめ

Infrastructure層は、Clean Architectureの最も外側の層として、すべての技術的詳細を担当します。重要なのは：

1. **依存性逆転の原則を守る**: Domain層がInfrastructure層に依存しない
2. **エンティティとモデルを分離する**: ビジネスロジックとデータベーススキーマを切り離す
3. **ISessionAdapterを使用する**: データベースセッション操作を抽象化
4. **非同期処理を徹底する**: すべてのI/O操作に`async`/`await`を使用
5. **適切な変換を実装する**: Entity ↔ Model変換を確実に行う

これらの原則を守ることで、保守性が高く、テスト可能で、フレームワークに依存しないアーキテクチャを実現できます。
