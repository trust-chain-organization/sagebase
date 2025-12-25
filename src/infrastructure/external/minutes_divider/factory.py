"""MinutesDivider factory

BAML実装のMinutesDividerを提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging
from typing import Any

from src.domain.interfaces.minutes_divider_service import IMinutesDividerService

logger = logging.getLogger(__name__)


class MinutesDividerFactory:
    """MinutesDivider factory

    BAML実装を提供します。
    """

    @staticmethod
    def create(llm_service: Any | None = None, k: int = 5) -> IMinutesDividerService:
        """BAML MinutesDividerを作成

        Args:
            llm_service: LLMService instance (optional)
            k: Number of sections (default 5)

        Returns:
            BAMLMinutesDivider: BAML実装のMinutesDivider
        """
        logger.info("Creating BAML MinutesDivider")
        # fmt: off
        from src.infrastructure.external.minutes_divider.baml_minutes_divider import (  # noqa: E501
            BAMLMinutesDivider,
        )
        # fmt: on

        return BAMLMinutesDivider(llm_service=llm_service, k=k)
