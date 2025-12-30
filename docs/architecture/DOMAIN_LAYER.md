# Domain層 実装ガイド

## 目次

- [概要](#概要)
- [層の責務と境界](#層の責務と境界)
- [エンティティ（Entities）](#エンティティentities)
- [リポジトリインターフェース（Repository Interfaces）](#リポジトリインターフェースrepository-interfaces)
- [ドメインサービス（Domain Services）](#ドメインサービスdomain-services)
- [よくある落とし穴と回避方法](#よくある落とし穴と回避方法)
- [実装チェックリスト](#実装チェックリスト)
- [参考資料](#参考資料)

## 概要

Domain層はClean Architectureの中核であり、ビジネスロジックとビジネスルールを実装する層です。この層は**他のどの層にも依存しない**という特徴があり、アプリケーションの本質的な価値を表現します。

### Domain層の位置づけ

```
┌─────────────────────────────────────────┐
│ Interfaces Layer (CLI, Web UI)         │
│  ↓ 依存                                  │
├─────────────────────────────────────────┤
│ Application Layer (Use Cases, DTOs)    │
│  ↓ 依存                                  │
├─────────────────────────────────────────┤
│ Infrastructure Layer (Implementations)  │
│  ↓ 依存                                  │
├─────────────────────────────────────────┤
│ ✨ Domain Layer ✨                       │
│ (Entities, Repository IFs, Services)   │
│ ← すべての層がこの層に依存               │
└─────────────────────────────────────────┘
```

### Domain層に含まれるコンポーネント

```
src/domain/
├── entities/           # エンティティ（25個）
│   ├── base.py         # BaseEntity
│   ├── politician.py   # 政治家エンティティ
│   ├── speaker.py      # 発言者エンティティ
│   ├── meeting.py      # 会議エンティティ
│   └── ...
├── repositories/       # リポジトリインターフェース（25個）
│   ├── base.py         # BaseRepository[T]
│   ├── politician_repository.py
│   ├── speaker_repository.py
│   └── ...
└── services/          # ドメインサービス（18個）
    ├── politician_domain_service.py
    ├── speaker_domain_service.py
    └── ...
```

## 層の責務と境界

### 責務

Domain層の責務は以下の通りです：

1. **ビジネスルールの実装**: エンティティに業務ロジックを実装
2. **データ構造の定義**: ビジネスオブジェクトの構造を定義
3. **インターフェースの定義**: リポジトリなどの抽象化を提供
4. **ドメインロジックの実装**: 複数エンティティにまたがるロジックをサービスで実装

### 境界と制約

**✅ Domain層が行うこと：**
- エンティティの定義とビジネスルールの実装
- リポジトリインターフェースの定義
- ドメインサービスによるビジネスロジックの実装
- 値オブジェクトの定義

**❌ Domain層が行わないこと：**
- データベースアクセス（Infrastructure層の責務）
- 外部APIの呼び出し（Infrastructure層の責務）
- UIの表示ロジック（Interface層の責務）
- ユースケースの調整（Application層の責務）

## エンティティ（Entities）

エンティティはビジネスオブジェクトを表現し、ビジネスルールを実装します。

### BaseEntity パターン

すべてのエンティティは`BaseEntity`を継承します。これにより、共通の機能（ID管理、等価性比較、ハッシュ化）を提供します。

**実装例: src/domain/entities/base.py**

```python
"""Base entity for domain model."""

from datetime import datetime


class BaseEntity:
    """Base class for all domain entities."""

    def __init__(self, id: int | None = None) -> None:
        self.id = id
        self.created_at: datetime | None = None
        self.updated_at: datetime | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
```

**設計上の重要ポイント：**
- `id`はオプショナル（新規作成時は`None`、永続化後にIDが付与される）
- `created_at`と`updated_at`はタイムスタンプ管理用
- `__eq__`は同一性をIDで判定（エンティティの本質的な特徴）
- `__hash__`はセットや辞書のキーとして使用可能にする

### エンティティの実装例

**実装例: src/domain/entities/politician.py**

```python
"""Politician entity."""

from src.domain.entities.base import BaseEntity


class Politician(BaseEntity):
    """政治家を表すエンティティ."""

    def __init__(
        self,
        name: str,
        political_party_id: int | None = None,
        furigana: str | None = None,
        district: str | None = None,
        profile_page_url: str | None = None,
        party_position: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.political_party_id = political_party_id
        self.furigana = furigana
        self.district = district
        self.profile_page_url = profile_page_url
        self.party_position = party_position

    def __str__(self) -> str:
        return self.name
```

**設計のポイント：**
1. **不変性の保持**: 可能な限り、作成後に値を変更しない設計を推奨
2. **必須フィールドの明示**: `name`は必須、他はオプショナル
3. **ビジネスルールの実装**: エンティティ内にビジネスロジックを実装可能

### エンティティにビジネスルールを実装する

エンティティにはビジネスロジックを実装できます：

```python
class Politician(BaseEntity):
    # ... 既存の実装 ...

    def is_party_leader(self) -> bool:
        """党首・代表かどうかを判定."""
        leadership_positions = ["党首", "代表", "委員長"]
        return self.party_position in leadership_positions if self.party_position else False

    def has_complete_profile(self) -> bool:
        """プロフィールが完全に記入されているか判定."""
        return all([
            self.name,
            self.political_party_id,
            self.furigana,
            self.district,
            self.profile_page_url
        ])

    def validate(self) -> list[str]:
        """エンティティの妥当性を検証し、問題のリストを返す."""
        issues = []

        if not self.name or not self.name.strip():
            issues.append("名前は必須です")

        if self.name and len(self.name) > 50:
            issues.append("名前が長すぎます（50文字以内）")

        return issues
```

**ビジネスルールの実装指針：**
- **エンティティ自身の状態に関するロジック**をエンティティに実装
- **複数のエンティティにまたがるロジック**はドメインサービスに実装
- **データベースアクセスを必要とするロジック**はドメインサービスまたはユースケースに実装

## リポジトリインターフェース（Repository Interfaces）

リポジトリインターフェースは、データアクセスを抽象化します。Domain層ではインターフェースのみを定義し、実装はInfrastructure層で行います。

### BaseRepository[T] パターン

すべてのリポジトリインターフェースは`BaseRepository[T]`を継承します。

**実装例: src/domain/repositories/base.py**

```python
"""Base repository interface."""

from abc import ABC, abstractmethod

from src.domain.entities.base import BaseEntity


class BaseRepository[T: BaseEntity](ABC):
    """Base repository interface for all repositories."""

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

**設計のポイント：**
1. **ジェネリック型の使用**: `T: BaseEntity`で型安全性を確保
2. **非同期メソッド**: すべてのメソッドは`async`（I/O処理を想定）
3. **共通CRUD操作**: 基本的なCRUD操作を定義

### エンティティ固有のリポジトリインターフェース

各エンティティに特化したクエリメソッドを追加します。

**実装例: src/domain/repositories/politician_repository.py**

```python
"""Politician repository interface."""

from abc import abstractmethod
from typing import Any

from src.domain.entities.politician import Politician
from src.domain.repositories.base import BaseRepository


class PoliticianRepository(BaseRepository[Politician]):
    """Repository interface for politicians."""

    @abstractmethod
    async def get_by_name_and_party(
        self, name: str, political_party_id: int | None = None
    ) -> Politician | None:
        """Get politician by name and political party."""
        pass

    @abstractmethod
    async def get_by_party(self, political_party_id: int) -> list[Politician]:
        """Get all politicians for a political party."""
        pass

    @abstractmethod
    async def search_by_name(self, name_pattern: str) -> list[Politician]:
        """Search politicians by name pattern."""
        pass

    @abstractmethod
    async def upsert(self, politician: Politician) -> Politician:
        """Insert or update politician (upsert)."""
        pass

    @abstractmethod
    async def bulk_create_politicians(
        self, politicians_data: list[dict[str, Any]]
    ) -> dict[str, list[Politician] | list[dict[str, Any]]]:
        """Bulk create or update politicians."""
        pass

    @abstractmethod
    async def count_by_party(self, political_party_id: int) -> int:
        """Count politicians in a political party."""
        pass
```

**カスタムメソッドの指針：**
- **ビジネス要件に基づいたクエリ**を定義
- **複雑なクエリ**はカスタムメソッドとして明示的に定義
- **メソッド名**は意図が明確になるように命名（`get_by_*`, `search_by_*`, `count_by_*`）

### ISessionAdapter パターン

リポジトリはセッション管理の抽象化（`ISessionAdapter`）を使用します。これにより、テスト時のモック化が容易になります。

```python
from typing import Protocol, Any


class ISessionAdapter(Protocol):
    """Session adapter interface for database operations."""

    async def get(self, model_class: type, entity_id: int) -> Any: ...
    async def execute(self, query: Any) -> Any: ...
    async def flush(self) -> None: ...
    async def refresh(self, instance: Any) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

## ドメインサービス（Domain Services）

ドメインサービスは、**複数のエンティティにまたがるビジネスロジック**や、**特定のエンティティに属さないロジック**を実装します。

### ドメインサービスの使いどころ

**エンティティに実装すべきロジック：**
```python
# ✅ Good: エンティティ自身の状態に関するロジック
class Politician(BaseEntity):
    def is_party_leader(self) -> bool:
        return self.party_position in ["党首", "代表", "委員長"]
```

**ドメインサービスに実装すべきロジック：**
```python
# ✅ Good: 複数エンティティの比較・重複検出
class PoliticianDomainService:
    def is_duplicate_politician(
        self, new_politician: Politician, existing_politicians: list[Politician]
    ) -> Politician | None:
        # 複数の政治家を比較するロジック
        pass
```

### ドメインサービスの実装例

**実装例: src/domain/services/politician_domain_service.py**

```python
"""Politician domain service for handling politician-related business logic."""

from src.domain.entities.politician import Politician


class PoliticianDomainService:
    """Domain service for politician-related business logic."""

    def normalize_politician_name(self, name: str) -> str:
        """Normalize politician name for comparison."""
        # Remove spaces and convert to consistent format
        normalized = name.strip().replace(" ", "").replace("　", "")
        return normalized

    def extract_surname(self, full_name: str) -> str:
        """Extract surname from full name."""
        # Japanese names typically have surname first
        name_parts = full_name.strip().split()
        if name_parts:
            return name_parts[0]
        return full_name

    def is_duplicate_politician(
        self, new_politician: Politician, existing_politicians: list[Politician]
    ) -> Politician | None:
        """Check if politician already exists based on name and party."""
        normalized_new = self.normalize_politician_name(new_politician.name)

        for existing in existing_politicians:
            normalized_existing = self.normalize_politician_name(existing.name)

            # Exact match
            if normalized_new == normalized_existing:
                # Same party or no party info
                if (
                    new_politician.political_party_id == existing.political_party_id
                    or new_politician.political_party_id is None
                    or existing.political_party_id is None
                ):
                    return existing

        return None

    def merge_politician_info(
        self, existing: Politician, new_info: Politician
    ) -> Politician:
        """Merge new politician information with existing record."""
        # Keep existing ID
        merged = Politician(
            name=existing.name,  # Keep original name format
            political_party_id=new_info.political_party_id
            or existing.political_party_id,
            furigana=new_info.furigana or existing.furigana,
            district=new_info.district or existing.district,
            profile_page_url=new_info.profile_page_url or existing.profile_page_url,
            id=existing.id,
        )
        return merged

    def validate_politician_data(self, politician: Politician) -> list[str]:
        """Validate politician data and return list of issues."""
        issues: list[str] = []

        if not politician.name or not politician.name.strip():
            issues.append("Name is required")

        # Check for suspicious data
        if politician.name and len(politician.name) > 50:
            issues.append("Name is unusually long")

        if politician.district and len(politician.district) > 100:
            issues.append("District name is unusually long")

        return issues

    def group_politicians_by_party(
        self, politicians: list[Politician]
    ) -> dict[int | None, list[Politician]]:
        """Group politicians by their political party."""
        grouped: dict[int | None, list[Politician]] = {}

        for politician in politicians:
            party_id = politician.political_party_id
            if party_id not in grouped:
                grouped[party_id] = []
            grouped[party_id].append(politician)

        return grouped
```

**ドメインサービスの設計指針：**
1. **ステートレス**: ドメインサービスは状態を持たない（メソッドのみ）
2. **純粋な関数**: 副作用を最小限に（外部APIアクセスなし）
3. **ビジネスロジックの集約**: 複雑なビジネスルールをカプセル化
4. **再利用性**: 複数のユースケースから呼び出される

### ドメインサービスの命名規則

```python
# ✅ Good: 動詞 + 名詞の形式
normalize_politician_name()
extract_surname()
is_duplicate_politician()
merge_politician_info()
validate_politician_data()

# ❌ Bad: 曖昧な命名
process()
handle()
do_something()
```

## よくある落とし穴と回避方法

### 落とし穴 1: エンティティにデータベースロジックを含める

**❌ 悪い例:**
```python
class Politician(BaseEntity):
    def save_to_database(self, session):
        # データベースアクセスをエンティティに実装
        session.add(self)
        session.commit()
```

**✅ 良い例:**
```python
# Domain層: エンティティはビジネスロジックのみ
class Politician(BaseEntity):
    def validate(self) -> list[str]:
        # ビジネスルールの検証
        pass

# Infrastructure層: リポジトリがデータベースアクセスを担当
class PoliticianRepositoryImpl(PoliticianRepository):
    async def create(self, politician: Politician) -> Politician:
        # データベースアクセス
        pass
```

### 落とし穴 2: 循環依存

**❌ 悪い例:**
```python
# src/domain/entities/politician.py
from src.domain.entities.political_party import PoliticalParty

class Politician(BaseEntity):
    party: PoliticalParty  # 循環依存の可能性

# src/domain/entities/political_party.py
from src.domain.entities.politician import Politician

class PoliticalParty(BaseEntity):
    members: list[Politician]  # 循環依存発生!
```

**✅ 良い例:**
```python
# 外部キーのIDのみを保持
class Politician(BaseEntity):
    political_party_id: int | None  # IDのみ

# 必要に応じて型ヒントにTYPE_CHECKINGを使用
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.political_party import PoliticalParty

class Politician(BaseEntity):
    political_party_id: int | None

    # 型ヒントのみで使用（実行時には評価されない）
    def get_party(self) -> "PoliticalParty | None":
        pass
```

### 落とし穴 3: ビジネスロジックの漏洩

**❌ 悪い例:**
```python
# Application層でビジネスロジックを実装
class ManagePoliticiansUseCase:
    async def execute(self, name: str):
        # ❌ ビジネスロジックがユースケースに漏洩
        normalized = name.strip().replace(" ", "").replace("　", "")
        # ...
```

**✅ 良い例:**
```python
# Domain層でビジネスロジックを実装
class PoliticianDomainService:
    def normalize_politician_name(self, name: str) -> str:
        return name.strip().replace(" ", "").replace("　", "")

# Application層ではドメインサービスを使用
class ManagePoliticiansUseCase:
    def __init__(self, domain_service: PoliticianDomainService):
        self.domain_service = domain_service

    async def execute(self, name: str):
        # ✅ ドメインサービスを使用
        normalized = self.domain_service.normalize_politician_name(name)
        # ...
```

### 落とし穴 4: フレームワークへの依存

**❌ 悪い例:**
```python
from sqlalchemy.orm import Session

class Politician(BaseEntity):
    # ❌ SQLAlchemyに依存
    def load_from_session(self, session: Session):
        pass
```

**✅ 良い例:**
```python
# ✅ フレームワークに依存しない純粋なドメインモデル
class Politician(BaseEntity):
    def __init__(self, name: str, ...):
        super().__init__()
        self.name = name
```

### 落とし穴 5: 過度な抽象化

**❌ 悪い例:**
```python
# 不要な抽象化レイヤー
class PoliticianFactory:
    def create_politician_from_dict(self, data: dict): ...
    def create_politician_from_json(self, json_str: str): ...
    def create_politician_from_xml(self, xml: str): ...
    # ... 10個以上のファクトリメソッド
```

**✅ 良い例:**
```python
# シンプルなコンストラクタで十分
class Politician(BaseEntity):
    def __init__(self, name: str, ...):
        super().__init__()
        self.name = name

# 必要に応じてシンプルなヘルパー関数
def politician_from_dict(data: dict) -> Politician:
    return Politician(name=data["name"], ...)
```

## 実装チェックリスト

新しいDomain層のコンポーネントを実装する際は、以下をチェックしてください：

### エンティティ

- [ ] `BaseEntity`を継承している
- [ ] 必須フィールドがコンストラクタで明示されている
- [ ] ビジネスルールがエンティティ内に実装されている
- [ ] データベース関連のコードが含まれていない
- [ ] 他の層（Infrastructure、Application）に依存していない
- [ ] `__str__`メソッドが適切に実装されている
- [ ] 型ヒントが完全に記述されている

### リポジトリインターフェース

- [ ] `BaseRepository[T]`を継承している（該当する場合）
- [ ] すべてのメソッドが`async`である
- [ ] すべてのメソッドが`@abstractmethod`でマークされている
- [ ] メソッドは抽象的な操作のみを定義（実装を含まない）
- [ ] カスタムクエリメソッドの命名が明確（`get_by_*`, `search_by_*`など）
- [ ] 戻り値の型ヒントが明確（`T | None`, `list[T]`など）
- [ ] ドキュメント文字列が各メソッドに記述されている

### ドメインサービス

- [ ] ステートレス（状態を持たない）
- [ ] ビジネスロジックのみを実装（データベースアクセスなし）
- [ ] 複数エンティティにまたがるロジックを実装
- [ ] メソッド名が明確（動詞 + 名詞）
- [ ] 純粋な関数として実装（副作用を最小限に）
- [ ] 他のドメインサービスやエンティティを使用可能
- [ ] 外部サービス（LLM、API）に直接依存していない

### 全般

- [ ] すべてのインポートが`src.domain`内またはPython標準ライブラリのみ
- [ ] 循環依存が発生していない
- [ ] ドキュメント文字列（docstring）が記述されている
- [ ] 型ヒントが完全に記述されている
- [ ] テストが作成されている（`tests/domain/`）

## 参考資料

### 関連ドキュメント

- [アーキテクチャ概要](../ARCHITECTURE.md)
- [Clean Architecture実装詳細](./clean-architecture.md)
- [Application層ガイド](./APPLICATION_LAYER.md)
- [Infrastructure層ガイド](./INFRASTRUCTURE_LAYER.md)
- [開発者ガイド](../DEVELOPMENT_GUIDE.md)

### ADR（Architecture Decision Records）

- [ADR-001: Clean Architecture採用](../ADR/0001-clean-architecture-adoption.md)
- [ADR-003: リポジトリパターン](../ADR/0003-repository-pattern.md)

### 実装例

- **エンティティ**: `src/domain/entities/`
  - `politician.py` - 政治家エンティティ
  - `speaker.py` - 発言者エンティティ
  - `meeting.py` - 会議エンティティ
  - `conference.py` - 会議体エンティティ

- **リポジトリ**: `src/domain/repositories/`
  - `base.py` - BaseRepository[T]
  - `politician_repository.py` - 政治家リポジトリIF
  - `speaker_repository.py` - 発言者リポジトリIF

- **ドメインサービス**: `src/domain/services/`
  - `politician_domain_service.py` - 政治家ドメインサービス
  - `speaker_domain_service.py` - 発言者ドメインサービス

### 外部リソース

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design by Eric Evans](https://domainlanguage.com/ddd/)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

---

**次のステップ**: [Application層ガイド](./APPLICATION_LAYER.md)で、ユースケースとDTOの実装方法を学びましょう。
