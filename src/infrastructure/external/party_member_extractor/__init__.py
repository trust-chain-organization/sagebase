"""政党メンバー抽出器

BAML実装のみを提供します（Pydantic実装は削除済み）。
"""

from .baml_extractor import BAMLPartyMemberExtractor


__all__ = ["BAMLPartyMemberExtractor"]
