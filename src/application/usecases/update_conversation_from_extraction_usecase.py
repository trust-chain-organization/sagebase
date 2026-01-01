"""発言（会話）エンティティをAI抽出結果から更新するUseCase。"""

import logging

from typing import Any

from src.application.dtos.extraction_result.conversation_extraction_result import (
    ConversationExtractionResult,
)
from src.application.usecases.base.update_entity_from_extraction_usecase import (
    UpdateEntityFromExtractionUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.extraction_log import EntityType
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.extraction_log_repository import ExtractionLogRepository
from src.domain.repositories.session_adapter import ISessionAdapter


logger = logging.getLogger(__name__)


class UpdateConversationFromExtractionUseCase(
    UpdateEntityFromExtractionUseCase[Conversation, ConversationExtractionResult]
):
    """発言（会話）エンティティをAI抽出結果から更新するUseCase。

    人間による手動修正を保護しつつ、AI抽出結果で発言エンティティを更新する。

    Attributes:
        _conversation_repo: 発言リポジトリ
        _extraction_log_repo: 抽出ログリポジトリ
        _session: セッションアダプター
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        extraction_log_repo: ExtractionLogRepository,
        session_adapter: ISessionAdapter,
    ) -> None:
        """UseCaseを初期化する。

        Args:
            conversation_repo: 発言リポジトリ
            extraction_log_repo: 抽出ログリポジトリ
            session_adapter: セッションアダプター
        """
        super().__init__(extraction_log_repo, session_adapter)
        self._conversation_repo = conversation_repo

    def _get_entity_type(self) -> EntityType:
        """エンティティタイプを返す。

        Returns:
            EntityType.STATEMENT（Conversationに対応）
        """
        # Note: ExtractionLogのEntityTypeにはSTATEMENTが定義されている
        # Conversationエンティティは発言を表すため、STATEMENTを使用する
        return EntityType.STATEMENT

    async def _get_entity(self, entity_id: int) -> Conversation | None:
        """発言エンティティを取得する。

        Args:
            entity_id: 発言ID

        Returns:
            発言エンティティ、存在しない場合はNone
        """
        return await self._conversation_repo.get_by_id(entity_id)

    async def _save_entity(self, entity: Conversation) -> None:
        """発言エンティティを保存する。

        Args:
            entity: 保存する発言エンティティ
        """
        await self._conversation_repo.update(entity)

    def _to_extracted_data(
        self, result: ConversationExtractionResult
    ) -> dict[str, Any]:  # type: ignore[override]
        """抽出結果をdictに変換する。

        Args:
            result: 発言抽出結果

        Returns:
            抽出データのdict表現
        """
        return result.to_dict()

    async def _apply_extraction(
        self, entity: Conversation, result: ConversationExtractionResult, log_id: int
    ) -> None:
        """抽出結果を発言エンティティに適用する。

        Args:
            entity: 更新対象の発言エンティティ
            result: 抽出結果
            log_id: 抽出ログID
        """
        # 抽出結果を各フィールドに反映
        entity.comment = result.comment
        entity.sequence_number = result.sequence_number
        if result.speaker_name is not None:
            entity.speaker_name = result.speaker_name
        if result.speaker_id is not None:
            entity.speaker_id = result.speaker_id
        if result.chapter_number is not None:
            entity.chapter_number = result.chapter_number
        if result.sub_chapter_number is not None:
            entity.sub_chapter_number = result.sub_chapter_number
        if result.minutes_id is not None:
            entity.minutes_id = result.minutes_id

        # 抽出ログIDを更新
        entity.update_from_extraction_log(log_id)

        logger.debug(
            f"Applied extraction to Conversation id={entity.id}, log_id={log_id}"
        )
