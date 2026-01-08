"""政治家マッチングサービスの実装パッケージ

このパッケージは、政治家マッチングサービスのInfrastructure層実装を提供します。
"""

from src.infrastructure.external.politician_matching.baml_politician_matching_service import (  # noqa: E501
    BAMLPoliticianMatchingService,
)


__all__ = [
    "BAMLPoliticianMatchingService",
]
