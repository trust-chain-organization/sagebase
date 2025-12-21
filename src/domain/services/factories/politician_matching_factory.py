"""Politician Matching Service Factory

フィーチャーフラグに基づいて適切なPoliticianMatchingService実装を提供します。
"""

import logging
import os

from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.llm_service import ILLMService

logger = logging.getLogger(__name__)


class PoliticianMatchingServiceFactory:
    """PoliticianMatchingService factory

    フィーチャーフラグに基づいて、Pydantic実装またはBAML実装を提供します。
    """

    @staticmethod
    def create(
        llm_service: ILLMService,
        politician_repository: PoliticianRepository,
    ):
        """環境変数に基づいてPoliticianMatchingServiceを作成

        Args:
            llm_service: LLM service instance
            politician_repository: Politician repository instance

        Returns:
            PoliticianMatchingService: 適切な実装（標準版 or BAML版）

        Environment Variables:
            USE_BAML_POLITICIAN_MATCHING: "true"でBAML実装を使用（デフォルト: false）
        """
        use_baml = os.getenv("USE_BAML_POLITICIAN_MATCHING", "false").lower() == "true"

        if use_baml:
            logger.info("Creating BAML PoliticianMatchingService")
            # fmt: off
            from src.domain.services.baml_politician_matching_service import (  # noqa: E501
                BAMLPoliticianMatchingService,
            )
            # fmt: on

            return BAMLPoliticianMatchingService(llm_service, politician_repository)

        logger.info("Creating standard PoliticianMatchingService")
        # fmt: off
        from src.domain.services.politician_matching_service import (  # noqa: E501
            PoliticianMatchingService,
        )
        # fmt: on

        return PoliticianMatchingService(llm_service, politician_repository)
