"""BAML-based conference member extractor

このモジュールは、BAMLを使用して会議体メンバー情報を抽出します。
既存のPydantic実装と並行して動作し、フィーチャーフラグで切り替え可能です。
"""

import logging

from baml_client import b
from src.conference_member_extractor.models import ExtractedMember

logger = logging.getLogger(__name__)


class BAMLMemberExtractor:
    """BAML-based member extractor for PoC

    BAMLを使用して会議体メンバー情報を抽出するクラス。
    既存のPydanticモデルとの互換性を保ちつつ、
    トークン効率とパース精度の向上を目指します。
    """

    async def extract_members(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMember]:
        """Extract members using BAML

        Args:
            html_content: HTMLコンテンツ
            conference_name: 会議体名

        Returns:
            抽出されたメンバーのリスト（既存のPydanticモデルと互換）

        Note:
            - HTMLが長すぎる場合は自動的に切り詰めます（50000文字）
            - エラー時は空のリストを返します
            - BAML呼び出しは非同期で実行されます
        """
        try:
            # HTMLが長すぎる場合は切り詰める（既存実装と同じ制限）
            max_length = 50000
            if len(html_content) > max_length:
                logger.warning(
                    f"HTML content too long ({len(html_content)} chars), "
                    f"truncating to {max_length} chars"
                )
                html_content = html_content[:max_length] + "..."

            # BAML関数を呼び出し
            logger.info(f"Calling BAML ExtractMembers for '{conference_name}'")
            result = await b.ExtractMembers(html_content, conference_name)

            # 既存のPydanticモデルに変換（互換性確保）
            members = [
                ExtractedMember(
                    name=m.name,
                    role=m.role,
                    party_name=m.party_name,
                    additional_info=m.additional_info,
                )
                for m in result
            ]

            logger.info(f"BAML extracted {len(members)} members")
            return members

        except Exception as e:
            logger.error(f"BAML extraction failed: {e}", exc_info=True)
            return []
