# ADR 0001: Clean Architecture の採用

## Status

Accepted (2024-08-15)

## Context

### 背景

Sagebaseプロジェクトは、日本の政治活動を追跡・分析するアプリケーションであり、以下のような複雑な要件を持っています：

- **多様なデータソース**: 議事録PDF、Web scraping、LLM APIなど
- **複雑なビジネスロジック**: 話者マッチング、政治家名寄せ、議員団メンバー抽出など
- **長期的な保守性**: 継続的な機能追加と改善が必要
- **技術的な変更への対応**: LLMモデルの変更、スクレイピング先の変更など

### 課題

プロジェクト初期には、以下のような保守性とスケーラビリティの問題が顕在化していました：

1. **フレームワークへの強い依存**
   - ビジネスロジックがSQLAlchemyモデルに密結合
   - LangChainの型がドメインロジックに漏洩
   - テストが困難（外部依存のモック化が複雑）

2. **責務の不明確さ**
   - データアクセスロジックがユースケースに混在
   - ビジネスルールがUI層やインフラ層に散在
   - 単一のファイルに複数の責務が混在

3. **変更の影響範囲が広い**
   - データベーススキーマ変更がビジネスロジックに波及
   - LLMプロバイダー変更がドメインロジックに影響
   - UIの変更がビジネスロジックを壊す

4. **テストの困難さ**
   - ビジネスロジックの単体テストが書けない（データベース依存）
   - モックの作成が複雑
   - テストの実行が遅い（外部依存が多い）

### 検討した代替案

#### 1. MVCパターン

**概要**: Model-View-Controller パターンでアプリケーションを構成

**利点**:
- シンプルで理解しやすい
- 多くの開発者に馴染みがある
- フレームワークのサポートが豊富

**欠点**:
- ビジネスロジックの置き場所が曖昧（ModelかControllerか）
- データベース依存が強い（Active Recordパターン）
- テストが困難（Modelがデータベースに依存）
- 長期的に肥大化しやすい（Fat Model/Fat Controller）

#### 2. レイヤードアーキテクチャ

**概要**: Presentation → Business Logic → Data Access の3層構造

**利点**:
- 層の責務が明確
- MVCよりも保守性が高い
- 多くのエンタープライズアプリケーションで実績がある

**欠点**:
- 依存関係が一方向だが、下位層への依存が残る
- フレームワークへの依存を完全には排除できない
- ビジネスロジックがインフラ層に依存する可能性がある

#### 3. Clean Architecture（選択）

**概要**: 4層構造（Domain, Application, Infrastructure, Interface）で依存性逆転の原則を徹底

**利点**:
- ビジネスロジックが完全にフレームワーク非依存
- 依存性逆転の原則により、変更の影響範囲が限定的
- テストが容易（モックの作成が簡単）
- 長期的な保守性が高い

**欠点**:
- 学習コストが高い
- 初期実装のオーバーヘッドが大きい
- 小規模なプロジェクトではオーバーエンジニアリング

## Decision

**Sagebaseプロジェクトでは、Clean Architectureを採用する。**

### 採用理由

1. **ビジネスロジックの独立性**
   - 政治家マッチング、話者名寄せなどの複雑なビジネスロジックをフレームワークから切り離す
   - LLMプロバイダーの変更（Gemini → Claude など）がビジネスロジックに影響しない
   - データベースの変更（PostgreSQL → 別のDB）がビジネスロジックに影響しない

2. **長期的な保守性**
   - 明確な責務分離により、コードの理解が容易
   - 変更の影響範囲が限定的（リポジトリの変更がドメインロジックに波及しない）
   - 新規開発者のオンボーディングが容易

3. **テスト容易性**
   - ドメインロジックの単体テストが簡単（データベース不要）
   - モックの作成が容易（インターフェースベース）
   - テストの実行が高速（外部依存が少ない）

4. **Sagebaseの規模と要件に適合**
   - 複雑なビジネスロジック（LLMマッチング、名寄せ、重複検出）
   - 長期的な運用（継続的な機能追加）
   - 技術的な変更への対応（LLMモデル、スクレイピング先）

### 実装方針

#### 1. 4層構造

```
┌─────────────────────────────────────────────────────────────┐
│ Interface Layer (CLI, Streamlit UI)                         │
│  - ユーザーインターフェース                                   │
│  - エントリーポイント                                          │
└───────────────────────┬─────────────────────────────────────┘
                        │ 依存
┌───────────────────────▼─────────────────────────────────────┐
│ Application Layer (Use Cases, DTOs)                         │
│  - ビジネスフローの調整                                        │
│  - トランザクション管理                                        │
└───────────────────────┬─────────────────────────────────────┘
                        │ 依存
┌───────────────────────▼─────────────────────────────────────┐
│ Domain Layer (Entities, Domain Services, Repositories)      │
│  - ビジネスロジック                                            │
│  - ビジネスルール                                              │
└───────────────────────▲─────────────────────────────────────┘
                        │ 実装
┌───────────────────────┴─────────────────────────────────────┐
│ Infrastructure Layer (Repository Impl, External Services)   │
│  - データベースアクセス                                        │
│  - 外部サービス統合                                            │
└─────────────────────────────────────────────────────────────┘
```

#### 2. 依存性逆転の原則

- **Domain層がすべての中心**: 他の層に依存しない
- **Infrastructure層がDomain層に依存**: リポジトリインターフェースを実装
- **Application層がDomain層に依存**: ユースケースがエンティティを操作
- **Interface層がApplication層に依存**: UIがユースケースを呼び出す

#### 3. 具体的な実装パターン

**エンティティ（Domain層）**:
```python
# src/domain/entities/politician.py
class Politician(BaseEntity):
    """政治家エンティティ（フレームワーク非依存）"""
    def __init__(self, id: int | None, name: str, party_id: int | None):
        super().__init__(id)
        self.name = name
        self.party_id = party_id

    def validate(self) -> bool:
        """ビジネスルール: 名前は必須"""
        return bool(self.name and self.name.strip())
```

**リポジトリインターフェース（Domain層）**:
```python
# src/domain/repositories/politician_repository.py
class PoliticianRepository(BaseRepository[Politician], ABC):
    """政治家リポジトリインターフェース"""
    @abstractmethod
    async def get_by_name_and_party(
        self, name: str, party_id: int | None
    ) -> Politician | None:
        pass
```

**リポジトリ実装（Infrastructure層）**:
```python
# src/infrastructure/persistence/politician_repository_impl.py
class PoliticianRepositoryImpl(
    BaseRepositoryImpl[Politician], PoliticianRepository
):
    """政治家リポジトリ実装（SQLAlchemy依存）"""
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

**ユースケース（Application層）**:
```python
# src/application/usecases/manage_politicians_usecase.py
class ManagePoliticiansUseCase:
    def __init__(self, politician_repository: PoliticianRepository):
        self.politician_repository = politician_repository

    async def create_politician(
        self, input_dto: CreatePoliticianInputDto
    ) -> CreatePoliticianOutputDto:
        # ビジネスロジック: 重複チェック
        existing = await self.politician_repository.get_by_name_and_party(
            input_dto.name, input_dto.party_id
        )
        if existing:
            return CreatePoliticianOutputDto(
                success=False, error_message="同名の政治家が既に存在します"
            )

        # エンティティの作成
        politician = Politician(
            id=None, name=input_dto.name, party_id=input_dto.party_id
        )

        # バリデーション
        if not politician.validate():
            return CreatePoliticianOutputDto(
                success=False, error_message="不正なデータです"
            )

        # 永続化
        created = await self.politician_repository.create(politician)
        return CreatePoliticianOutputDto(success=True, politician_id=created.id)
```

#### 4. 段階的な移行

Clean Architectureへの移行は段階的に実施：

- **Phase 1: 基盤整備** - BaseEntity, BaseRepository, ISessionAdapterの実装
- **Phase 2: Domain層の構築** - エンティティ、リポジトリインターフェース、ドメインサービス
- **Phase 3: Application層の構築** - ユースケース、DTOの実装
- **Phase 4: レガシーコードの移行** - 既存コードをClean Architectureに段階的に移行

詳細は[CLEAN_ARCHITECTURE_MIGRATION.md](../CLEAN_ARCHITECTURE_MIGRATION.md)を参照。

## Consequences

### Positive（利点）

1. **ビジネスロジックの独立性**
   - ✅ LLMプロバイダーの変更が容易（Gemini → Claude → OpenAI）
   - ✅ データベースの変更が容易（PostgreSQL → 別のDB）
   - ✅ フレームワークの変更が容易（LangChain → LlamaIndexなど）

2. **テスト容易性の向上**
   - ✅ ドメインロジックの単体テストが簡単（モック不要）
   - ✅ テストの実行が高速（外部依存が少ない）
   - ✅ テストカバレッジの向上

3. **保守性の向上**
   - ✅ 責務が明確（各層の役割が明確）
   - ✅ 変更の影響範囲が限定的
   - ✅ コードの理解が容易

4. **新規開発者のオンボーディング**
   - ✅ 層の構造が明確で理解しやすい
   - ✅ ドキュメント（各層のガイド）が整備されている
   - ✅ 実装パターンが統一されている

### Negative（欠点・トレードオフ）

1. **学習コスト**
   - ⚠️ Clean Architectureの理解に時間がかかる
   - ⚠️ 依存性逆転の原則の理解が必要
   - ⚠️ 各層の責務の理解が必要
   - **対策**: 包括的なドキュメント整備（DOMAIN_LAYER.md, APPLICATION_LAYER.md など）

2. **初期実装のオーバーヘッド**
   - ⚠️ エンティティとモデルの分離により、変換コードが必要
   - ⚠️ インターフェースと実装の両方を定義する必要がある
   - ⚠️ ファイル数が増加（エンティティ、リポジトリ、実装など）
   - **対策**: BaseRepositoryImplなどの基盤クラスでボイラープレートを削減

3. **コードの行数増加**
   - ⚠️ DTO、エンティティ、モデルなど、複数の型定義が必要
   - ⚠️ 変換ロジック（Entity ↔ Model）が必要
   - **対策**: 必要な複雑さとして受け入れ、長期的な保守性を優先

4. **パフォーマンスのオーバーヘッド（微小）**
   - ⚠️ Entity ↔ Model変換によるわずかなオーバーヘッド
   - **影響**: 実測では無視できるレベル（マイクロ秒単位）

### Risks（リスク）

1. **過度な抽象化**
   - **リスク**: すべてをインターフェース化し、必要以上に複雑になる
   - **対策**: 実用的な抽象化のみを行う（YAGNI原則）

2. **移行の不完全性**
   - **リスク**: レガシーコードとClean Architectureのコードが混在
   - **対策**: 段階的な移行計画（CLEAN_ARCHITECTURE_MIGRATION.md）

3. **一貫性の欠如**
   - **リスク**: 開発者によって実装パターンが異なる
   - **対策**: スキル（clean-architecture-checker）によるレビュー

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [CLEAN_ARCHITECTURE_MIGRATION.md](../CLEAN_ARCHITECTURE_MIGRATION.md) - 移行計画
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) - 全体アーキテクチャ
- [docs/architecture/DOMAIN_LAYER.md](../architecture/DOMAIN_LAYER.md) - Domain層ガイド
- [docs/architecture/APPLICATION_LAYER.md](../architecture/APPLICATION_LAYER.md) - Application層ガイド
- [docs/architecture/INFRASTRUCTURE_LAYER.md](../architecture/INFRASTRUCTURE_LAYER.md) - Infrastructure層ガイド
- [docs/architecture/INTERFACE_LAYER.md](../architecture/INTERFACE_LAYER.md) - Interface層ガイド

## Notes

- Clean Architectureの採用は2024年8月に決定
- 2024年12月時点で、Phase 1-4の移行が完了
- 現在のコードベース: 77 domain files, 37 application files, 63 infrastructure files, 63 interface files
- テストカバレッジ: Domain層 85%、Application層 78%、Infrastructure層 70%
