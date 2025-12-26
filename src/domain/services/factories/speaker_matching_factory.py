"""Speaker Matching Service Factory

フィーチャーフラグに基づいて適切なSpeakerMatchingService実装を提供します。
"""

import logging
import os

from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.interfaces.llm_service import ILLMService


logger = logging.getLogger(__name__)


class SpeakerMatchingServiceFactory:
    """SpeakerMatchingService factory

    フィーチャーフラグに基づいて、Pydantic実装またはBAML実装を提供します。
    """

    @staticmethod
    def create(
        llm_service: ILLMService,
        speaker_repository: SpeakerRepository,
    ):
        """環境変数に基づいてSpeakerMatchingServiceを作成

        Args:
            llm_service: LLM service instance
            speaker_repository: Speaker repository instance

        Returns:
            SpeakerMatchingService: 適切な実装（標準版 or BAML版）

        Environment Variables:
            USE_BAML_SPEAKER_MATCHING: "true"でBAML実装を使用（デフォルト: false）
        """
        use_baml = os.getenv("USE_BAML_SPEAKER_MATCHING", "false").lower() == "true"

        if use_baml:
            logger.info("Creating BAML SpeakerMatchingService")
            # fmt: off
            from src.domain.services.baml_speaker_matching_service import (  # noqa: E501
                BAMLSpeakerMatchingService,
            )
            # fmt: on

            return BAMLSpeakerMatchingService(llm_service, speaker_repository)

        logger.info("Creating standard SpeakerMatchingService")
        # fmt: off
        from src.domain.services.speaker_matching_service import (  # noqa: E501
            SpeakerMatchingService,
        )
        # fmt: on

        return SpeakerMatchingService(llm_service, speaker_repository)
