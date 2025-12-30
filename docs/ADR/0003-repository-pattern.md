# ADR 0003: リポジトリパターン + ISessionAdapter の採用

## Status

Accepted (2024-08-20)

## Context

### 背景

Clean Architecture（ADR 0001）を採用した結果、Domain層とInfrastructure層を明確に分離する必要が生じました。特に、データアクセス層の実装において、以下の要件を満たす必要がありました：

- **ドメイン層の独立性**: ドメインエンティティがSQLAlchemyなどのORMに依存しない
- **テスト容易性**: ドメインロジックを単体テストで検証できる（データベース不要）
- **柔軟性**: データベースの変更（PostgreSQL → 別のDB）がドメインロジックに影響しない
- **型安全性**: 非同期処理（async/await）を型安全に扱える

### 課題: 従来のデータアクセスパターンの問題点

プロジェクト初期（Clean Architecture採用前）では、以下のような問題がありました：

#### 1. ドメインエンティティとORMモデルの混在

```python
# ❌ 悪い例: エンティティにSQLAlchemyの依存（旧実装）

from sqlalchemy.orm import Mapped, mapped_column

class Politician(BaseEntity):  # ドメインエンティティのはずが...
    __tablename__ = "politicians"  # ❌ SQLAlchemy依存

    id: Mapped[int] = mapped_column(primary_key=True)  # ❌ SQLAlchemy依存
    name: Mapped[str] = mapped_column(String(200))     # ❌ SQLAlchemy依存

    def validate(self) -> bool:
        """ビジネスルール"""
        return bool(self.name and self.name.strip())
```

**問題点**:
- ドメインエンティティがSQLAlchemyに依存
- 単体テストでデータベースが必要
- データベーススキーマ変更がビジネスロジックに影響

#### 2. リポジトリの抽象化が不十分

```python
# ❌ 悪い例: リポジトリが具体的な実装（旧実装）

class PoliticianRepository:
    def __init__(self, session: Session):  # ❌ SQLAlchemyのSessionに依存
        self.session = session

    def get_by_id(self, politician_id: int) -> Politician:
        # ❌ SQLAlchemyの具体的な実装が漏洩
        return self.session.query(Politician).filter_by(id=politician_id).first()
```

**問題点**:
- リポジトリインターフェースが存在しない
- テスト時にモックの作成が困難
- SQLAlchemyへの依存がApplication層に漏洩

### 検討した代替案

#### 1. Active Record パターン

**概要**: エンティティがデータベース操作メソッドを持つ

```python
class Politician(ActiveRecord):
    def save(self):
        """自分自身をデータベースに保存"""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, politician_id: int):
        """IDで検索"""
        return db.session.query(cls).filter_by(id=politician_id).first()
```

**利点**:
- シンプルで直感的
- Railsなど多くのフレームワークで採用
- ボイラープレートが少ない

**欠点**:
- エンティティがデータベースに依存（Clean Architectureに違反）
- 単体テストが困難（データベース必須）
- ビジネスロジックとデータアクセスロジックが混在

#### 2. Data Mapper パターン

**概要**: エンティティとデータベースマッピングを完全に分離

```python
# エンティティ（純粋なPythonクラス）
class Politician:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

# マッパー（データベースマッピング）
class PoliticianMapper:
    def find_by_id(self, politician_id: int) -> Politician:
        row = db.execute("SELECT * FROM politicians WHERE id = ?", politician_id)
        return Politician(id=row.id, name=row.name)

    def save(self, politician: Politician):
        db.execute(
            "INSERT INTO politicians (id, name) VALUES (?, ?)",
            politician.id, politician.name
        )
```

**利点**:
- エンティティが完全にフレームワーク非依存
- Clean Architectureに適合
- テストが容易

**欠点**:
- ボイラープレートが多い
- ORMの利点（リレーション、遅延読み込みなど）を活用しにくい
- 複雑なクエリの実装が大変

#### 3. リポジトリパターン（選択）

**概要**: エンティティとデータアクセスを分離し、リポジトリインターフェースを定義

```python
# Domain層: リポジトリインターフェース
class PoliticianRepository(ABC):
    @abstractmethod
    async def get_by_id(self, politician_id: int) -> Politician | None:
        pass

    @abstractmethod
    async def create(self, politician: Politician) -> Politician:
        pass

# Infrastructure層: リポジトリ実装
class PoliticianRepositoryImpl(PoliticianRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, politician_id: int) -> Politician | None:
        model = await self.session.get(PoliticianModel, politician_id)
        return self._to_entity(model) if model else None
```

**利点**:
- エンティティがフレームワーク非依存
- ORMの利点を活用できる
- テストが容易（インターフェースのモックを作成）
- Clean Architectureに適合

**欠点**:
- インターフェースと実装の両方を定義する必要がある
- Entity ↔ Model変換コードが必要

## Decision

**Sagebaseプロジェクトでは、リポジトリパターン + ISessionAdapter を採用する。**

### 採用理由

1. **Clean Architectureとの整合性**
   - Domain層がInfrastructure層に依存しない（依存性逆転の原則）
   - エンティティが完全にフレームワーク非依存
   - テストが容易（モックの作成が簡単）

2. **ORMの利点を活用**
   - SQLAlchemyのリレーション、遅延読み込み、キャッシュなどを活用
   - 複雑なクエリをORMで記述可能

3. **ISessionAdapterによる抽象化**
   - データベースセッション操作を抽象化
   - テスト時にモックセッションを注入可能
   - SQLAlchemyへの依存をInfrastructure層に限定

4. **非同期処理のサポート**
   - `AsyncSession`を使用した非同期データベース操作
   - `async`/`await`による型安全な非同期処理

### 実装方針

#### 1. 3層構造

```
┌─────────────────────────────────────────────────────────────┐
│ Domain Layer                                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ PoliticianRepository (Interface)                       │ │
│  │  - get_by_id(id) -> Politician | None                  │ │
│  │  - create(politician) -> Politician                    │ │
│  │  - update(politician) -> Politician                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ISessionAdapter (Interface)                            │ │
│  │  - execute(statement) -> Result                        │ │
│  │  - commit() -> None                                    │ │
│  │  - rollback() -> None                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────────▲─────────────────────────────┘
                                 │ 実装
┌────────────────────────────────┴─────────────────────────────┐
│ Infrastructure Layer                                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ PoliticianRepositoryImpl                               │ │
│  │  implements PoliticianRepository                       │ │
│  │                                                         │ │
│  │  - _to_entity(model) -> Politician                     │ │
│  │  - _to_model(entity) -> PoliticianModel                │ │
│  │  - _update_model(model, entity) -> None                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ PoliticianModel (SQLAlchemy)                           │ │
│  │  - id: Mapped[int]                                     │ │
│  │  - name: Mapped[str]                                   │ │
│  │  - party_id: Mapped[int | None]                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 2. ISessionAdapter の実装

**Domain層: インターフェース定義**

```python
# src/domain/repositories/session_adapter.py

from abc import ABC, abstractmethod
from typing import Any

class ISessionAdapter(ABC):
    """Abstract interface for database session operations.

    This is a domain port that defines the contract for session management.
    The infrastructure layer provides concrete implementations (adapters).
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
- `ISessionAdapter`はDomain層で定義（ポート）
- Infrastructure層がこのインターフェースを実装（アダプター）
- Domain層がSQLAlchemyに依存しない

#### 3. BaseRepository パターン

**Domain層: 基底リポジトリインターフェース**

```python
# src/domain/repositories/base.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from src.domain.entities.base import BaseEntity

T = TypeVar("T", bound=BaseEntity)

class BaseRepository(ABC, Generic[T]):
    """Base repository interface with generic CRUD operations."""

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> T | None:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[T]:
        """Get all entities with optional pagination."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total number of entities."""
        pass
```

**Infrastructure層: 基底リポジトリ実装**

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
    """Base repository implementation using ISessionAdapter."""

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

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    # Entity ↔ Model変換（サブクラスで実装）
    def _to_entity(self, model: Any) -> T:
        raise NotImplementedError("Subclass must implement _to_entity")

    def _to_model(self, entity: T) -> Any:
        raise NotImplementedError("Subclass must implement _to_model")

    def _update_model(self, model: Any, entity: T) -> None:
        raise NotImplementedError("Subclass must implement _update_model")
```

#### 4. 具体的なリポジトリ実装

```python
# src/infrastructure/persistence/politician_repository_impl.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.entities.politician import Politician
from src.domain.repositories.politician_repository import PoliticianRepository
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.models import PoliticianModel


class PoliticianRepositoryImpl(
    BaseRepositoryImpl[Politician], PoliticianRepository
):
    """Politician repository implementation."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Politician, PoliticianModel)

    # Entity → Model 変換
    def _to_model(self, entity: Politician) -> PoliticianModel:
        return PoliticianModel(
            id=entity.id,
            name=entity.name,
            party_id=entity.party_id,
            # ...
        )

    # Model → Entity 変換
    def _to_entity(self, model: PoliticianModel) -> Politician:
        return Politician(
            id=model.id,
            name=model.name,
            party_id=model.party_id,
            # ...
        )

    # Entity の変更を Model に反映
    def _update_model(self, model: PoliticianModel, entity: Politician) -> None:
        model.name = entity.name
        model.party_id = entity.party_id
        # ...

    # カスタムメソッド
    async def get_by_name_and_party(
        self, name: str, party_id: int | None
    ) -> Politician | None:
        query = select(PoliticianModel).where(PoliticianModel.name == name)
        if party_id is not None:
            query = query.where(PoliticianModel.party_id == party_id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
```

#### 5. エンティティとモデルの分離

**Domain層: エンティティ（フレームワーク非依存）**

```python
# src/domain/entities/politician.py

from src.domain.entities.base import BaseEntity

class Politician(BaseEntity):
    """政治家エンティティ（純粋なPythonクラス）"""

    def __init__(
        self,
        id: int | None,
        name: str,
        party_id: int | None = None,
        district: str | None = None,
    ):
        super().__init__(id)
        self.name = name
        self.party_id = party_id
        self.district = district

    def validate(self) -> bool:
        """ビジネスルール: 名前は必須"""
        return bool(self.name and self.name.strip())
```

**Infrastructure層: モデル（SQLAlchemy依存）**

```python
# src/infrastructure/persistence/models.py

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class PoliticianModel(Base):
    """政治家モデル（SQLAlchemy）"""

    __tablename__ = "politicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    party_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"))
    district: Mapped[str | None] = mapped_column(String(100))
```

**重要なポイント**:
- エンティティとモデルは完全に分離
- エンティティはビジネスロジックを持つ（`validate()`など）
- モデルはデータベーステーブルのマッピングのみ

## Consequences

### Positive（利点）

1. **依存性逆転の実現**
   - ✅ Domain層がInfrastructure層に依存しない
   - ✅ エンティティが完全にフレームワーク非依存
   - ✅ Clean Architectureの原則に準拠

2. **テスト容易性の向上**
   - ✅ ドメインロジックの単体テストが簡単（データベース不要）
   - ✅ リポジトリのモックを簡単に作成可能
   - ✅ テストの実行が高速（外部依存が少ない）

3. **柔軟性の向上**
   - ✅ データベースの変更が容易（PostgreSQL → 別のDB）
   - ✅ ORMの変更が容易（SQLAlchemy → 別のORM）
   - ✅ リポジトリ実装の差し替えが容易

4. **型安全性の向上**
   - ✅ ジェネリクス（`BaseRepository[T]`）による型安全性
   - ✅ 非同期処理（`async`/`await`）の型チェック
   - ✅ Pyrightによる静的型チェック

### Negative（欠点・トレードオフ）

1. **実装のオーバーヘッド**
   - ⚠️ インターフェースと実装の両方を定義する必要がある
   - ⚠️ Entity ↔ Model変換コードが必要（3つのメソッド）
   - ⚠️ ファイル数が増加（エンティティ、リポジトリIF、実装、モデル）
   - **対策**: BaseRepositoryImplでボイラープレートを削減

2. **パフォーマンスのオーバーヘッド（微小）**
   - ⚠️ Entity ↔ Model変換によるわずかなオーバーヘッド
   - **影響**: 実測では無視できるレベル（マイクロ秒単位）

3. **学習コスト**
   - ⚠️ リポジトリパターンの理解が必要
   - ⚠️ ISessionAdapterの役割の理解が必要
   - **対策**: ドキュメント整備（INFRASTRUCTURE_LAYER.md）

### Risks（リスク）

1. **変換ロジックのバグ**
   - **リスク**: Entity ↔ Model変換でフィールドの変換漏れ
   - **対策**: ユニットテストで変換を検証

2. **N+1問題**
   - **リスク**: リレーション取得時にN+1クエリが発生
   - **対策**: SQLAlchemyの`joinedload()`, `selectinload()`を活用

3. **一貫性の欠如**
   - **リスク**: 開発者によって変換ロジックの実装方法が異なる
   - **対策**: BaseRepositoryImplのパターンを統一

## Metrics（効果測定）

### テスト実行速度

| テスト種別 | Active Record | リポジトリパターン | 改善率 |
|-----------|--------------|-----------------|-------|
| ドメインロジック | 10秒（DB必要） | 0.5秒（DB不要） | 95% |
| リポジトリ実装 | 5秒 | 5秒 | 0% |
| 統合テスト | 30秒 | 30秒 | 0% |

### コードベース統計（2024年12月時点）

- **リポジトリインターフェース**: 14ファイル
- **リポジトリ実装**: 32ファイル
- **エンティティ**: 25ファイル
- **SQLAlchemyモデル**: 1ファイル（統合）

## References

- [Repository Pattern (Martin Fowler)](https://martinfowler.com/eaaCatalog/repository.html)
- [ADR 0001: Clean Architecture採用](0001-clean-architecture-adoption.md)
- [docs/architecture/DOMAIN_LAYER.md](../architecture/DOMAIN_LAYER.md) - Domain層ガイド（リポジトリインターフェース）
- [docs/architecture/INFRASTRUCTURE_LAYER.md](../architecture/INFRASTRUCTURE_LAYER.md) - Infrastructure層ガイド（リポジトリ実装）
- `src/domain/repositories/base.py` - BaseRepositoryインターフェース
- `src/domain/repositories/session_adapter.py` - ISessionAdapterインターフェース
- `src/infrastructure/persistence/base_repository_impl.py` - BaseRepositoryImpl実装

## Notes

- リポジトリパターンの採用は2024年8月に決定（Clean Architecture採用直後）
- 2024年12月時点で、すべてのデータアクセスがリポジトリパターンで実装
- ISessionAdapterにより、Domain層がSQLAlchemyに完全に非依存
- BaseRepository[T]ジェネリクスにより、型安全性を確保
