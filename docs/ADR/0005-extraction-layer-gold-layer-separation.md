# ADR 0005: 抽出層（Bronze Layer）とGold Layer分離

## Status

Accepted (2025-01-08)

## Context

### 背景

LLMによるデータ抽出と人間による確認・修正を両立させる必要がありました。特に以下の課題がありました：

- **人間の修正が上書きされる問題**: LLMの再実行で人間がレビュー・修正したデータが上書きされる
- **抽出履歴が残らない問題**: 精度分析やデバッグのために抽出履歴が必要だが、上書き型では履歴が失われる
- **複数エンティティタイプへの対応**: Statement、Politician、Speaker、ConferenceMember、ParliamentaryGroupMemberなど、複数のエンティティタイプに同じ課題がある

### 要件

1. **抽出結果の履歴保持**: すべてのLLM抽出結果を履歴として保持し、精度分析を可能にする
2. **人間の修正の保護**: 人間がレビュー・修正したデータはLLM再実行で上書きされない
3. **トレーサビリティ**: いつ、どのパイプラインで、どのような結果が抽出されたか追跡可能
4. **統一的なパターン**: 複数のエンティティタイプで一貫した設計パターンを適用

### 検討した代替案

#### 1. 上書き型（従来の方式）

```python
# ❌ 従来の方式
async def extract_and_update(entity_id: int, llm_result: dict):
    entity = await repo.get(entity_id)
    entity.name = llm_result["name"]
    entity.data = llm_result["data"]
    await repo.save(entity)
```

**問題点**:
- 人間の修正が失われる
- 抽出履歴が残らない
- 精度分析が不可能

#### 2. バージョン管理型

**概要**: エンティティの全バージョンを保持

**問題点**:
- ストレージコストが大きい
- クエリが複雑化
- 「正解」の決定が困難

#### 3. ログファイル出力型

**概要**: 抽出結果をログファイルに出力

**問題点**:
- 構造化クエリが困難
- ログと実データの関連付けが困難
- 分析ツールの別途開発が必要

## Decision

### Bronze Layer / Gold Layer 分離アーキテクチャを採用

2層構造でLLM抽出結果と確定データを分離します。

### 1. Bronze Layer（抽出ログ層）

**責務**: LLM抽出結果の履歴保持、精度分析

**特性**:
- 追記専用（Immutable）: 作成後は更新・削除されない
- 全抽出結果を保存: 成功・失敗問わずすべて記録
- メタデータ付き: パイプラインバージョン、信頼度、トークン数など

**テーブル**: `extraction_logs`

```sql
CREATE TABLE extraction_logs (
    id SERIAL PRIMARY KEY,
    entity_type entity_type NOT NULL,  -- ENUM型
    entity_id INTEGER NOT NULL,
    pipeline_version VARCHAR(100) NOT NULL,
    extracted_data JSONB NOT NULL,
    confidence_score FLOAT,
    extraction_metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Gold Layer（確定データ層）

**責務**: アプリケーションが参照する正解データ

**特性**:
- 人間の修正が最優先
- `is_manually_verified` フラグで保護状態を管理
- `latest_extraction_log_id` で最新抽出ログへの参照

**対象テーブル**:
- `conversations` (Statement)
- `politicians`
- `speakers`
- `politician_affiliations` (ConferenceMember)
- `parliamentary_group_memberships`

### 3. 更新ロジック

```python
class UpdateEntityFromExtractionUseCase:
    async def execute(
        self,
        entity_id: int,
        extraction_result: ExtractionResult,
        pipeline_version: str
    ) -> UpdateEntityResult:
        # 1. Bronze Layer: 抽出ログを必ず保存
        log = ExtractionLog(
            entity_type=self._get_entity_type(),
            entity_id=entity_id,
            pipeline_version=pipeline_version,
            extracted_data=extraction_result.to_dict(),
            ...
        )
        log_id = await self._extraction_log_repo.create(log)

        # 2. Gold Layer: エンティティ取得
        entity = await self._get_entity(entity_id)
        if entity is None:
            return UpdateEntityResult(updated=False, reason="entity_not_found")

        # 3. ガード処理: 人間修正済みならスキップ
        if entity.is_manually_verified:
            return UpdateEntityResult(
                updated=False,
                reason="manually_verified",
                extraction_log_id=log_id
            )

        # 4. Gold Layer: 未検証なら更新
        await self._apply_extraction(entity, extraction_result, log_id)
        await self._save_entity(entity)

        return UpdateEntityResult(updated=True, extraction_log_id=log_id)
```

### 4. VerifiableEntity プロトコル

```python
class VerifiableEntity(Protocol):
    is_manually_verified: bool
    latest_extraction_log_id: int | None

    def mark_as_manually_verified(self) -> None:
        """手動検証済みとしてマーク"""
        ...

    def update_from_extraction_log(self, log_id: int) -> None:
        """抽出ログIDを更新"""
        ...

    def can_be_updated_by_ai(self) -> bool:
        """AI更新可能かどうか"""
        return not self.is_manually_verified
```

### 5. 対象エンティティタイプ

| EntityType | Bronze（抽出ログ） | Gold（確定データ） |
|-----------|-------------------|-------------------|
| STATEMENT | ExtractionLog | Conversation |
| POLITICIAN | ExtractionLog | Politician |
| SPEAKER | ExtractionLog | Speaker |
| CONFERENCE_MEMBER | ExtractionLog | PoliticianAffiliation |
| PARLIAMENTARY_GROUP_MEMBER | ExtractionLog | ParliamentaryGroupMembership |

## Consequences

### メリット

1. **人間の修正が保護される**
   - `is_manually_verified = true` のエンティティはAI再抽出で上書きされない
   - 人間のレビュー作業が無駄にならない

2. **抽出履歴が蓄積され、精度分析が可能**
   - パイプラインバージョン別の精度比較
   - 時系列での精度推移分析
   - 信頼度スコアの統計分析

3. **LLMのバージョンアップがユーザー影響なく実施可能**
   - 新パイプラインをテスト実行しても既存データに影響なし
   - A/Bテストが容易

4. **全エンティティタイプで一貫したパターン**
   - `UpdateEntityFromExtractionUseCase` 基底クラスを継承
   - 新しいエンティティタイプの追加が容易

5. **完全なトレーサビリティ**
   - いつ、どのパイプラインで抽出されたか追跡可能
   - デバッグ・監査に有用

### デメリット

1. **データベースサイズの増加**
   - 抽出ログは追記専用のため蓄積され続ける
   - 対策: 古いログの定期アーカイブ（別ストレージへ移行）

2. **処理の複雑化**
   - UseCase経由での更新が必須
   - 直接DB更新は推奨されない

3. **エンティティごとにUseCase実装が必要**
   - 6つのUpdateUseCaseを実装
   - ただしベースクラスがあるため実装コストは軽減

### トレードオフ

- **ストレージ vs 分析能力**: ログ蓄積によるストレージ増加と引き換えに、詳細な分析・デバッグ能力を獲得
- **実装複雑性 vs 保守性**: 初期実装は複雑だが、長期的な保守性・拡張性が向上

## 実装

### 主要ファイル

**Domain層**:
- `src/domain/entities/extraction_log.py` - ExtractionLogエンティティ
- `src/domain/entities/verifiable_entity.py` - VerifiableEntityプロトコル
- `src/domain/repositories/extraction_log_repository.py` - リポジトリIF

**Application層**:
- `src/application/usecases/base/update_entity_from_extraction_usecase.py` - 基底UseCase
- `src/application/usecases/update_*_from_extraction_usecase.py` - 各エンティティ用UseCase
- `src/application/usecases/mark_entity_as_verified_usecase.py` - 手動検証マークUseCase

**Infrastructure層**:
- `src/infrastructure/persistence/extraction_log_repository_impl.py` - リポジトリ実装

**Database**:
- `database/migrations/038_create_extraction_logs.sql`
- `database/migrations/039_add_verification_fields_to_gold_entities.sql`
- `database/migrations/040_add_extraction_log_fields_to_extracted_members.sql`

### 使用例

#### 新しい抽出処理を追加する場合

```python
class UpdateNewEntityFromExtractionUseCase(UpdateEntityFromExtractionUseCase[NewEntity, NewExtractionResult]):
    def _get_entity_type(self) -> EntityType:
        return EntityType.NEW_ENTITY

    async def _get_entity(self, entity_id: int) -> NewEntity | None:
        return await self._entity_repo.find_by_id(entity_id)

    async def _save_entity(self, entity: NewEntity) -> None:
        await self._entity_repo.save(entity)

    def _to_extracted_data(self, result: NewExtractionResult) -> dict[str, Any]:
        return result.model_dump()

    async def _apply_extraction(
        self, entity: NewEntity, result: NewExtractionResult, log_id: int
    ) -> None:
        entity.name = result.name
        entity.data = result.data
        entity.update_from_extraction_log(log_id)
```

#### 手動検証をマークする場合

```python
# Streamlit UIから
result = await mark_entity_as_verified_usecase.execute(
    MarkEntityAsVerifiedInputDto(
        entity_type=EntityType.POLITICIAN,
        entity_id=politician_id,
        is_verified=True
    )
)
```

## 関連ADR

- [ADR 0001: Clean Architecture採用](0001-clean-architecture-adoption.md)
- [ADR 0003: リポジトリパターン](0003-repository-pattern.md)

## 関連Issue

- Product Goal: [#813](https://github.com/trust-chain-organization/sagebase/issues/813)
- Implementation PBIs: #861〜#872
