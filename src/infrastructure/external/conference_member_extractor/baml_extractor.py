"""BAML-based conference member extractor

このモジュールは、BAMLを使用して会議体メンバー情報を抽出します。
既存のPydantic実装と並行して動作し、フィーチャーフラグで切り替え可能です。
"""

import logging

from baml_client.async_client import b
from src.domain.dtos.conference_member_dto import ExtractedMemberDTO
from src.domain.interfaces.member_extractor_service import IMemberExtractorService

logger = logging.getLogger(__name__)


class BAMLMemberExtractor(IMemberExtractorService):
    """BAML-based member extractor for PoC

    BAMLを使用して会議体メンバー情報を抽出するクラス。
    既存のPydanticモデルとの互換性を保ちつつ、
    トークン効率とパース精度の向上を目指します。
    """

    async def extract_members(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMemberDTO]:
        """Extract members using BAML

        Args:
            html_content: HTMLコンテンツ
            conference_name: 会議体名

        Returns:
            抽出されたメンバー情報のリスト（ExtractedMemberDTO）

        Note:
            - HTMLが長すぎる場合は自動的に切り詰めます（50000文字）
            - エラー時は空のリストを返します
            - BAML呼び出しは非同期で実行されます
        """
        try:
            logger.info(
                f"Starting BAML member extraction for '{conference_name}' "
                f"(HTML size: {len(html_content)} chars)"
            )

            # HTMLが長すぎる場合は切り詰める（既存実装と同じ制限）
            max_length = 50000
            original_length = len(html_content)
            if original_length > max_length:
                logger.warning(
                    f"HTML content too long ({original_length} chars), "
                    f"truncating to {max_length} chars "
                    f"(reduction: {original_length - max_length} chars, "
                    f"{(1 - max_length / original_length) * 100:.1f}%)"
                )
                html_content = html_content[:max_length] + "..."

            # BAML関数を呼び出し
            logger.info(
                f"Calling BAML ExtractMembers for '{conference_name}' "
                f"(input size: {len(html_content)} chars)"
            )
            result = await b.ExtractMembers(html_content, conference_name)
            logger.debug(f"BAML returned {len(result)} raw results")

            # DTOに変換して直接返す（型安全性向上）
            members = [
                ExtractedMemberDTO(
                    name=m.name,
                    role=m.role,
                    party_name=m.party_name,
                    additional_info=m.additional_info,
                )
                for m in result
            ]

            logger.info(
                f"BAML extraction completed: {len(members)} members extracted "
                f"from '{conference_name}'"
            )
            if members:
                logger.debug(
                    f"Sample member: {members[0].name} "
                    f"(role: {members[0].role}, party: {members[0].party_name})"
                )

            return members

        except Exception as e:
            logger.error(
                f"BAML extraction failed for '{conference_name}': {e}", exc_info=True
            )
            return []
