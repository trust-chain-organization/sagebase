# Application層 実装ガイド

## 目次

- [概要](#概要)
- [層の責務と境界](#層の責務と境界)
- [ユースケース（Use Cases）](#ユースケースuse-cases)
- [DTO（Data Transfer Objects）](#dtodata-transfer-objects)
- [エラーハンドリングとロギング](#エラーハンドリングとロギング)
- [トランザクション管理](#トランザクション管理)
- [よくある落とし穴と回避方法](#よくある落とし穴と回避方法)
- [実装チェックリスト](#実装チェックリスト)
- [参考資料](#参考資料)

## 概要

Application層は、ユースケースの実装とビジネスフローの調整を担当します。この層はDomain層に依存しますが、Infrastructure層やInterface層には依存しません。

### Application層の位置づけ

```
┌──────────────────────────────────────┐
│ Interfaces Layer (CLI, Web UI)      │
│  ↓ 依存                               │
├──────────────────────────────────────┤
│ ✨ Application Layer ✨              │
│ (Use Cases, DTOs)                   │
│  ↓ 依存                               │
├──────────────────────────────────────┤
│ Domain Layer                         │
│ (Entities, Repository IFs, Services)│
│  ↑ 実装提供                           │
├──────────────────────────────────────┤
│ Infrastructure Layer                 │
│ (Repository Implementations)         │
└──────────────────────────────────────┘
```

### Application層に含まれるコンポーネント

```
src/application/
├── usecases/              # ユースケース（29個）
│   ├── manage_politicians_usecase.py
│   ├── process_minutes_usecase.py
│   ├── match_speakers_usecase.py
│   └── ...
└── dtos/                  # データ転送オブジェクト（16個）
    ├── politician_dto.py
    ├── minutes_dto.py
    └── ...
```

## 層の責務と境界

### 責務

Application層の責務は以下の通りです：

1. **ユースケースの実装**: ビジネスフローの調整とワークフローの実行
2. **DTOによるデータ変換**: 外部層（Interface層）とDomain層の間でデータを変換
3. **トランザクション管理**: ビジネストランザクションの境界を定義
4. **複数のドメインサービスの調整**: 複数のドメインサービスやリポジトリを組み合わせて使用

### 境界と制約

**✅ Application層が行うこと：**
- ユースケースの実装（ビジネスフローの調整）
- DTOの定義と使用
- トランザクション境界の定義
- ドメインサービスとリポジトリの調整
- エラーハンドリングとロギング

**❌ Application層が行わないこと：**
- ビジネスルールの実装（Domain層の責務）
- データベースアクセスの実装（Infrastructure層の責務）
- UIロジックの実装（Interface層の責務）
- 外部サービスとの連携の実装（Infrastructure層の責務）

## ユースケース（Use Cases）

ユースケースは、アプリケーション固有のビジネスフローを実装します。

### ユースケースの設計原則

1. **単一責任の原則**: 1つのユースケース = 1つのユーザーストーリー
2. **依存性注入**: コンストラクタでリポジトリとサービスを受け取る
3. **DTOの使用**: 入力と出力にDTOを使用
4. **execute()メソッド**: ユースケースの実行はexecute()メソッドで統一
5. **非同期処理**: すべてのユースケースメソッドは`async`

### 基本的なユースケースの実装パターン

**実装例: src/application/usecases/manage_politicians_usecase.py**

```python
"""Use case for managing politicians."""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities import Politician
from src.domain.repositories.politician_repository import PoliticianRepository


logger = get_logger(__name__)


@dataclass
class CreatePoliticianInputDto:
    """Input DTO for creating a politician."""

    name: str
    party_id: int | None = None
    district: str | None = None
    profile_url: str | None = None


@dataclass
class CreatePoliticianOutputDto:
    """Output DTO for creating a politician."""

    success: bool
    politician_id: int | None = None
    error_message: str | None = None


class ManagePoliticiansUseCase:
    """Use case for managing politicians."""

    def __init__(self, politician_repository: PoliticianRepository):
        """Initialize the use case.

        Args:
            politician_repository: Repository instance (can be sync or async)
        """
        self.politician_repository = politician_repository

    async def create_politician(
        self, input_dto: CreatePoliticianInputDto
    ) -> CreatePoliticianOutputDto:
        """Create a new politician.

        Args:
            input_dto: 作成する政治家の情報

        Returns:
            CreatePoliticianOutputDto: 作成結果
        """
        try:
            # 1. 重複チェック
            existing = await self.politician_repository.get_by_name_and_party(
                input_dto.name, input_dto.party_id
            )
            if existing:
                return CreatePoliticianOutputDto(
                    success=False,
                    error_message="同じ名前と政党の政治家が既に存在します。",
                )

            # 2. エンティティの作成
            politician = Politician(
                id=0,  # Will be assigned by database
                name=input_dto.name,
                political_party_id=input_dto.party_id,
                district=input_dto.district,
                profile_page_url=input_dto.profile_url,
            )

            # 3. 永続化
            created = await self.politician_repository.create(politician)

            # 4. 結果の返却
            return CreatePoliticianOutputDto(
                success=True,
                politician_id=created.id
            )

        except Exception as e:
            logger.error(f"Failed to create politician: {e}")
            return CreatePoliticianOutputDto(
                success=False,
                error_message=str(e)
            )
```

**実装のポイント：**
1. **DTOの使用**: 入力と出力にDTOを使用（エンティティを直接公開しない）
2. **エラーハンドリング**: try-exceptでエラーをキャッチし、適切なレスポンスを返す
3. **ロギング**: エラー発生時にログを記録
4. **ビジネスロジックの呼び出し**: リポジトリとドメインサービスを使用

### 複雑なユースケースの実装例

複数のリポジトリとサービスを組み合わせた、より複雑なユースケースの例：

**実装例: src/application/usecases/process_minutes_usecase.py**

```python
"""Use case for processing meeting minutes."""

from datetime import datetime

from src.application.dtos.minutes_dto import (
    ExtractedSpeechDTO,
    MinutesProcessingResultDTO,
    ProcessMinutesDTO,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.minutes_domain_service import MinutesDomainService
from src.domain.services.speaker_domain_service import SpeakerDomainService


class ProcessMinutesUseCase:
    """議事録処理ユースケース

    議事録PDFまたはテキストを処理し、発言を抽出して
    データベースに保存します。
    """

    def __init__(
        self,
        meeting_repository: MeetingRepository,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
        minutes_domain_service: MinutesDomainService,
        speaker_domain_service: SpeakerDomainService,
    ):
        """議事録処理ユースケースを初期化する

        Args:
            meeting_repository: 会議リポジトリの実装
            minutes_repository: 議事録リポジトリの実装
            conversation_repository: 発言リポジトリの実装
            speaker_repository: 発言者リポジトリの実装
            minutes_domain_service: 議事録ドメインサービス
            speaker_domain_service: 発言者ドメインサービス
        """
        self.meeting_repo = meeting_repository
        self.minutes_repo = minutes_repository
        self.conversation_repo = conversation_repository
        self.speaker_repo = speaker_repository
        self.minutes_service = minutes_domain_service
        self.speaker_service = speaker_domain_service

    async def execute(
        self, request: ProcessMinutesDTO
    ) -> MinutesProcessingResultDTO:
        """議事録を処理する

        以下の手順で議事録を処理します：
        1. 会議情報の取得
        2. 既存処理のチェック
        3. PDFまたはテキストからの発言抽出
        4. 発言データの保存
        5. 発言者情報の抽出と作成

        Args:
            request: 処理リクエストDTO

        Returns:
            MinutesProcessingResultDTO: 処理結果
        """
        start_time = datetime.now()

        try:
            # 1. 会議情報の取得
            meeting = await self.meeting_repo.get_by_id(request.meeting_id)
            if not meeting:
                raise ValueError(f"会議ID {request.meeting_id} が見つかりません")

            # 2. 既存処理のチェック
            if not request.force_reprocess:
                existing = await self.minutes_repo.find_by_meeting_id(
                    request.meeting_id
                )
                if existing:
                    return MinutesProcessingResultDTO(
                        success=True,
                        message="既に処理済みです",
                        minutes_id=existing.id,
                        total_conversations=0,
                    )

            # 3. PDFまたはテキストからの発言抽出
            extracted_speeches = await self.minutes_service.extract_speeches(
                meeting=meeting,
                pdf_url=request.pdf_url,
                text_content=request.text_content,
            )

            # 4. 発言データの保存
            conversations = []
            for speech_dto in extracted_speeches:
                # 発言者の取得または作成
                speaker = await self.speaker_service.get_or_create_speaker(
                    name=speech_dto.speaker_name,
                    conference_id=meeting.conference_id,
                )

                # 発言の作成
                conversation = Conversation(
                    meeting_id=meeting.id,
                    speaker_id=speaker.id if speaker else None,
                    content=speech_dto.content,
                    order_in_meeting=speech_dto.order,
                )
                saved_conversation = await self.conversation_repo.create(
                    conversation
                )
                conversations.append(saved_conversation)

            # 5. 処理時間の計算
            processing_time = (datetime.now() - start_time).total_seconds()

            return MinutesProcessingResultDTO(
                success=True,
                message=f"{len(conversations)}件の発言を抽出しました",
                minutes_id=meeting.id,
                total_conversations=len(conversations),
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            logger.error(f"議事録処理中にエラーが発生しました: {e}")
            return MinutesProcessingResultDTO(
                success=False,
                error_message=str(e),
                minutes_id=None,
                total_conversations=0,
            )
```

**複雑なユースケースの実装ポイント：**
1. **複数リポジトリの調整**: 会議、議事録、発言、発言者の4つのリポジトリを使用
2. **ドメインサービスの活用**: 議事録処理と発言者管理のドメインロジックを使用
3. **ワークフローの明確化**: コメントで処理ステップを明示
4. **処理時間の記録**: パフォーマンス監視のために処理時間を計測

## DTO（Data Transfer Objects）

DTOは、Application層とInterface層の間でデータを転送するために使用します。

### DTOの設計原則

1. **InputDTO / OutputDTOペア**: 入力と出力で別々のDTOを定義
2. **不変性**: DTOは変更不可能にする（dataclassのfrozen=Trueは推奨）
3. **バリデーション**: 必要に応じてバリデーションロジックを追加
4. **エンティティとの分離**: DTOはエンティティではない（ID不要）

### DTOの実装例

**基本的なDTO：**

```python
from dataclasses import dataclass


@dataclass
class PoliticianListInputDto:
    """Input DTO for listing politicians."""

    party_id: int | None = None
    search_name: str | None = None


@dataclass
class PoliticianListOutputDto:
    """Output DTO for listing politicians."""

    politicians: list[Politician]
```

**CRUD操作のDTOパターン：**

```python
from dataclasses import dataclass


# Create
@dataclass
class CreatePoliticianInputDto:
    """Input DTO for creating a politician."""

    name: str
    party_id: int | None = None
    district: str | None = None
    profile_url: str | None = None


@dataclass
class CreatePoliticianOutputDto:
    """Output DTO for creating a politician."""

    success: bool
    politician_id: int | None = None
    error_message: str | None = None


# Update
@dataclass
class UpdatePoliticianInputDto:
    """Input DTO for updating a politician."""

    id: int
    name: str
    party_id: int | None = None
    district: str | None = None


@dataclass
class UpdatePoliticianOutputDto:
    """Output DTO for updating a politician."""

    success: bool
    error_message: str | None = None


# Delete
@dataclass
class DeletePoliticianInputDto:
    """Input DTO for deleting a politician."""

    id: int


@dataclass
class DeletePoliticianOutputDto:
    """Output DTO for deleting a politician."""

    success: bool
    error_message: str | None = None
```

**DTOの命名規則：**
- **InputDTO**: `<操作><エンティティ名>InputDto`
  - 例: `CreatePoliticianInputDto`, `UpdatePoliticianInputDto`
- **OutputDTO**: `<操作><エンティティ名>OutputDto`
  - 例: `CreatePoliticianOutputDto`, `DeletePoliticianOutputDto`

### DTOとエンティティの変換

DTOとエンティティは別物です。必要に応じて変換します：

```python
# ✅ Good: DTOからエンティティへの変換
def dto_to_entity(dto: CreatePoliticianInputDto) -> Politician:
    return Politician(
        name=dto.name,
        political_party_id=dto.party_id,
        district=dto.district,
        profile_page_url=dto.profile_url,
    )


# ✅ Good: エンティティからDTOへの変換
def entity_to_dto(politician: Politician) -> PoliticianOutputDto:
    return PoliticianOutputDto(
        id=politician.id,
        name=politician.name,
        party_id=politician.political_party_id,
        district=politician.district,
    )
```

## エラーハンドリングとロギング

### エラーハンドリングの原則

1. **try-exceptの使用**: すべてのユースケースメソッドでエラーをキャッチ
2. **OutputDTOでのエラー返却**: 例外を投げるのではなく、OutputDTOでエラー情報を返す
3. **ロギング**: エラー発生時には詳細をログに記録
4. **ユーザーフレンドリーなメッセージ**: エラーメッセージは日本語で明確に

### エラーハンドリングの実装例

```python
from src.common.logging import get_logger

logger = get_logger(__name__)


class ManagePoliticiansUseCase:
    async def create_politician(
        self, input_dto: CreatePoliticianInputDto
    ) -> CreatePoliticianOutputDto:
        """Create a new politician."""
        try:
            # ビジネスロジックの実行
            # ...

            return CreatePoliticianOutputDto(
                success=True,
                politician_id=created.id
            )

        except ValueError as e:
            # ビジネスルール違反（ユーザー起因のエラー）
            logger.warning(f"バリデーションエラー: {e}")
            return CreatePoliticianOutputDto(
                success=False,
                error_message=f"入力エラー: {e}",
            )

        except Exception as e:
            # システムエラー
            logger.error(f"政治家作成中に予期しないエラーが発生: {e}", exc_info=True)
            return CreatePoliticianOutputDto(
                success=False,
                error_message="システムエラーが発生しました。管理者に連絡してください。",
            )
```

**エラーハンドリングのポイント：**
1. **エラーの種類を区別**: ビジネスルール違反（WARNING）とシステムエラー（ERROR）
2. **詳細なログ**: `exc_info=True`でスタックトレースを記録
3. **ユーザーへの配慮**: システムエラーの詳細は隠し、一般的なメッセージを返す

### カスタム例外の定義

必要に応じて、カスタム例外を定義します：

```python
# src/application/exceptions.py

class ApplicationException(Exception):
    """Application層の基底例外."""

    pass


class EntityNotFoundException(ApplicationException):
    """エンティティが見つからない例外."""

    def __init__(self, entity_name: str, entity_id: int):
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} (ID: {entity_id}) が見つかりません")


class DuplicateEntityException(ApplicationException):
    """エンティティが重複している例外."""

    def __init__(self, entity_name: str, details: str = ""):
        self.entity_name = entity_name
        super().__init__(f"{entity_name} が既に存在します: {details}")


class ValidationException(ApplicationException):
    """バリデーションエラー."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"バリデーションエラー: {', '.join(errors)}")
```

## トランザクション管理

Application層は、トランザクションの境界を定義します。

### トランザクション管理の原則

1. **ユースケース単位**: 1つのユースケースメソッド = 1つのトランザクション
2. **セッション管理**: Infrastructure層から受け取ったセッションを使用
3. **コミット/ロールバック**: Infrastructure層が責任を持つ

### トランザクション管理の実装例

Application層のユースケースは、トランザクション管理を直接行いません。代わりに、Infrastructure層で提供されるセッションを使用します：

```python
# ✅ Good: ユースケースはセッションを受け取るだけ
class ProcessMinutesUseCase:
    def __init__(
        self,
        meeting_repository: MeetingRepository,
        # ... 他のリポジトリ
    ):
        # リポジトリは既にセッションを持っている
        self.meeting_repo = meeting_repository

    async def execute(self, request: ProcessMinutesDTO):
        # リポジトリ経由でデータアクセス
        meeting = await self.meeting_repo.get_by_id(request.meeting_id)
        # ...
        # トランザクションはInfrastructure層で管理される
```

トランザクション管理は、Interface層やInfrastructure層で行います：

```python
# Interface層（CLIコマンド）でのトランザクション管理
async def process_minutes_command(meeting_id: int):
    async with get_db_session() as session:
        # セッションを使ってリポジトリを作成
        meeting_repo = MeetingRepositoryImpl(session)
        # ... 他のリポジトリ

        # ユースケースを実行
        use_case = ProcessMinutesUseCase(meeting_repo, ...)
        result = await use_case.execute(ProcessMinutesDTO(meeting_id=meeting_id))

        if result.success:
            await session.commit()  # コミット
        else:
            await session.rollback()  # ロールバック
```

## よくある落とし穴と回避方法

### 落とし穴 1: ユースケースの肥大化

**❌ 悪い例:**
```python
class MegaUseCase:
    async def do_everything(self):
        # 政治家の作成
        # 会議の作成
        # 議事録の処理
        # 発言者のマッチング
        # 統計の計算
        # ... 500行のコード
        pass
```

**✅ 良い例:**
```python
# 単一責任の原則に従って分割
class CreatePoliticianUseCase: ...
class ProcessMinutesUseCase: ...
class MatchSpeakersUseCase: ...
class CalculateStatisticsUseCase: ...
```

### 落とし穴 2: ドメインロジックの漏洩

**❌ 悪い例:**
```python
class ManagePoliticiansUseCase:
    async def create_politician(self, input_dto):
        # ❌ ビジネスロジックがユースケースに漏洩
        normalized_name = input_dto.name.strip().replace(" ", "").replace("　", "")
        # ...
```

**✅ 良い例:**
```python
class ManagePoliticiansUseCase:
    def __init__(
        self,
        politician_repository: PoliticianRepository,
        politician_service: PoliticianDomainService,  # ドメインサービスを使用
    ):
        self.politician_repo = politician_repository
        self.politician_service = politician_service

    async def create_politician(self, input_dto):
        # ✅ ドメインサービスに委譲
        normalized_name = self.politician_service.normalize_politician_name(
            input_dto.name
        )
        # ...
```

### 落とし穴 3: DTOとエンティティの混同

**❌ 悪い例:**
```python
# DTOをエンティティのように使用
@dataclass
class PoliticianDto(BaseEntity):  # ❌ エンティティを継承
    name: str

    def save(self):  # ❌ DTOにビジネスロジック
        pass
```

**✅ 良い例:**
```python
# DTOは単なるデータコンテナ
@dataclass
class CreatePoliticianInputDto:
    name: str
    party_id: int | None = None


# エンティティは別
class Politician(BaseEntity):
    def __init__(self, name: str, ...):
        super().__init__()
        self.name = name
```

### 落とし穴 4: Infrastructure層への直接依存

**❌ 悪い例:**
```python
from sqlalchemy.orm import Session  # ❌ SQLAlchemyに直接依存

class ManagePoliticiansUseCase:
    def __init__(self, session: Session):  # ❌
        self.session = session
```

**✅ 良い例:**
```python
# ✅ リポジトリインターフェースに依存
class ManagePoliticiansUseCase:
    def __init__(self, politician_repository: PoliticianRepository):
        self.politician_repo = politician_repository
```

### 落とし穴 5: 過度な try-except

**❌ 悪い例:**
```python
async def create_politician(self, input_dto):
    try:
        try:
            try:
                # ネストしたtry-except
                pass
            except:
                pass
        except:
            pass
    except:
        pass
```

**✅ 良い例:**
```python
async def create_politician(self, input_dto):
    try:
        # ビジネスロジック
        pass
    except ValueError as e:
        # 特定の例外を個別にハンドル
        logger.warning(f"バリデーションエラー: {e}")
        return CreatePoliticianOutputDto(success=False, error_message=str(e))
    except Exception as e:
        # その他のエラー
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        return CreatePoliticianOutputDto(
            success=False, error_message="システムエラーが発生しました"
        )
```

## 実装チェックリスト

新しいApplication層のコンポーネントを実装する際は、以下をチェックしてください：

### ユースケース

- [ ] 単一責任の原則に従っている
- [ ] コンストラクタで依存性を注入している
- [ ] メソッド名が明確（`execute()`, `create_*()`, `update_*()` など）
- [ ] すべてのメソッドが`async`である
- [ ] InputDTOとOutputDTOを使用している
- [ ] エンティティを直接返していない
- [ ] エラーハンドリングが実装されている
- [ ] ロギングが適切に実装されている
- [ ] Domain層のみに依存している（Infrastructure層に依存していない）
- [ ] ドキュメント文字列が記述されている

### DTO

- [ ] `@dataclass`デコレータを使用している
- [ ] InputDTOとOutputDTOが分離されている
- [ ] 命名規則に従っている（`<操作><エンティティ名>InputDto`）
- [ ] エンティティではない（`BaseEntity`を継承していない）
- [ ] 型ヒントが完全に記述されている
- [ ] ドキュメント文字列が記述されている
- [ ] 必要に応じてバリデーションロジックを含む

### エラーハンドリング

- [ ] すべてのユースケースメソッドでtry-exceptを使用
- [ ] エラーをOutputDTOで返している
- [ ] ログが適切に記録されている
- [ ] ユーザーフレンドリーなエラーメッセージ
- [ ] システムエラーの詳細を隠している

### 全般

- [ ] Domain層のみに依存（Infrastructure層に依存していない）
- [ ] テストが作成されている（`tests/application/`）
- [ ] ドキュメントが最新である

## 参考資料

### 関連ドキュメント

- [アーキテクチャ概要](../ARCHITECTURE.md)
- [Domain層ガイド](./DOMAIN_LAYER.md)
- [Infrastructure層ガイド](./INFRASTRUCTURE_LAYER.md)
- [Interface層ガイド](./INTERFACE_LAYER.md)
- [開発者ガイド](../DEVELOPMENT_GUIDE.md)

### ADR（Architecture Decision Records）

- [ADR-001: Clean Architecture採用](../ADR/0001-clean-architecture-adoption.md)

### 実装例

- **ユースケース**: `src/application/usecases/`
  - `manage_politicians_usecase.py` - 政治家管理ユースケース
  - `process_minutes_usecase.py` - 議事録処理ユースケース
  - `match_speakers_usecase.py` - 発言者マッチングユースケース

- **DTO**: `src/application/dtos/`（一部はユースケースファイルに含まれる）
  - `politician_dto.py`
  - `minutes_dto.py`

### 外部リソース

- [Use Case Pattern](https://martinfowler.com/eaaCatalog/useCase.html)
- [DTO Pattern](https://martinfowler.com/eaaCatalog/dataTransferObject.html)

---

**次のステップ**: [Infrastructure層ガイド](./INFRASTRUCTURE_LAYER.md)で、リポジトリ実装と外部サービス統合の方法を学びましょう。
