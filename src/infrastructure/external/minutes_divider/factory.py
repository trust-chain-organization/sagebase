"""MinutesDivider factory

フィーチャーフラグに基づいて適切なMinutesDivider実装を提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging
import os
from typing import Any

from src.domain.interfaces.minutes_divider_service import IMinutesDividerService

logger = logging.getLogger(__name__)


class MinutesDividerFactory:
    """MinutesDivider factory

    フィーチャーフラグに基づいて、Pydantic実装またはBAML実装を提供します。
    """

    @staticmethod
    def create(llm_service: Any | None = None, k: int = 5) -> IMinutesDividerService:
        """フィーチャーフラグに基づいてMinutesDividerを作成

        Args:
            llm_service: LLMService instance (Pydantic実装でのみ使用)
            k: Number of sections (default 5)

        Returns:
            MinutesDivider: 適切な実装（MinutesDivider or BAMLMinutesDivider）

        Environment Variables:
            USE_BAML_MINUTES_DIVIDER: "false"でPydantic実装を使用（デフォルトはBAML）
        """
        use_baml = os.getenv("USE_BAML_MINUTES_DIVIDER", "true").lower() == "true"

        if use_baml:
            logger.info("Creating BAML MinutesDivider")
            # fmt: off
            from src.infrastructure.external.minutes_divider.baml_minutes_divider import (  # noqa: E501
                BAMLMinutesDivider,
            )
            # fmt: on

            return BAMLMinutesDivider(llm_service=llm_service, k=k)

        logger.info("Creating Pydantic MinutesDivider")
        # fmt: off
        from src.infrastructure.external.minutes_divider.pydantic_minutes_divider import (  # noqa: E501
            MinutesDivider,
        )
        # fmt: on

        return MinutesDivider(llm_service=llm_service, k=k)
