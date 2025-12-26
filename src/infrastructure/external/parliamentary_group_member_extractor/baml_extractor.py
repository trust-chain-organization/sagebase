"""議員団メンバー抽出器（BAML実装）

議員団のURLから所属議員情報を抽出する。
BAMLを使用してトークン効率とパース精度を向上。
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from baml_client.async_client import b
from src.domain.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
    ParliamentaryGroupMemberExtractionResultDTO,
)
from src.domain.interfaces.parliamentary_group_member_extractor_service import (
    IParliamentaryGroupMemberExtractorService,
)
from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher


logger = logging.getLogger(__name__)


class BAMLParliamentaryGroupMemberExtractor(IParliamentaryGroupMemberExtractorService):
    """議員団メンバー抽出器（BAML実装）

    BAMLを使用して議員団メンバー情報を抽出するクラス。
    Pydantic実装と比較して、トークン効率とパース精度の向上を目指します。
    """

    async def extract_members(
        self, parliamentary_group_id: int, url: str
    ) -> ParliamentaryGroupMemberExtractionResultDTO:
        """議員団URLからメンバー情報を抽出する

        Args:
            parliamentary_group_id: 議員団ID
            url: 議員団メンバー一覧のURL

        Returns:
            抽出結果（DTO）
        """
        try:
            # HTMLを取得
            html_content = await self._fetch_html(url)
            if not html_content:
                return ParliamentaryGroupMemberExtractionResultDTO(
                    parliamentary_group_id=parliamentary_group_id,
                    url=url,
                    extracted_members=[],
                    extraction_date=None,
                    error="URLからコンテンツを取得できませんでした。URLが正しいか、またはPlaywrightが正しくインストールされているか確認してください。",
                )

            # BeautifulSoupでHTMLを解析
            soup = BeautifulSoup(html_content, "html.parser")

            # スクリプトとスタイルを削除
            for script in soup(["script", "style"]):
                script.decompose()

            # テキストを抽出
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = "\n".join(chunk for chunk in chunks if chunk)

            # LLMで議員情報を抽出（BAML使用）
            members_dto = await self._extract_members_with_baml(text_content, str(soup))

            return ParliamentaryGroupMemberExtractionResultDTO(
                parliamentary_group_id=parliamentary_group_id,
                url=url,
                extracted_members=members_dto,
                extraction_date=datetime.now(),
                error=None,
            )

        except Exception as e:
            logger.error(f"BAML extraction error: {e}", exc_info=True)
            return ParliamentaryGroupMemberExtractionResultDTO(
                parliamentary_group_id=parliamentary_group_id,
                url=url,
                extracted_members=[],
                extraction_date=None,
                error=str(e),
            )

    async def _extract_members_with_baml(
        self, text_content: str, html_content: str
    ) -> list[ExtractedParliamentaryGroupMemberDTO]:
        """BAMLを使用して議員情報を抽出する

        Args:
            text_content: テキストコンテンツ
            html_content: HTMLコンテンツ

        Returns:
            抽出された議員リスト（DTO）
        """
        try:
            logger.info(
                f"Starting BAML parliamentary group member extraction "
                f"(Text size: {len(text_content)} chars, "
                f"HTML size: {len(html_content)} chars)"
            )

            # HTMLとテキストが長すぎる場合は切り詰める
            max_text_length = 5000
            max_html_length = 10000

            original_text_length = len(text_content)
            original_html_length = len(html_content)

            if original_text_length > max_text_length:
                logger.warning(
                    f"Text content too long ({original_text_length} chars), "
                    f"truncating to {max_text_length} chars "
                    f"(reduction: {original_text_length - max_text_length} chars, "
                    f"{(1 - max_text_length / original_text_length) * 100:.1f}%)"
                )
                text_content = text_content[:max_text_length]

            if original_html_length > max_html_length:
                logger.warning(
                    f"HTML content too long ({original_html_length} chars), "
                    f"truncating to {max_html_length} chars "
                    f"(reduction: {original_html_length - max_html_length} chars, "
                    f"{(1 - max_html_length / original_html_length) * 100:.1f}%)"
                )
                html_content = html_content[:max_html_length]

            # BAML関数を呼び出し
            logger.info(
                f"Calling BAML ExtractParliamentaryGroupMembers "
                f"(text: {len(text_content)} chars, html: {len(html_content)} chars)"
            )
            result = await b.ExtractParliamentaryGroupMembers(
                html_content, text_content
            )
            logger.debug(f"BAML returned {len(result)} raw results")

            # BAMLの結果をDTOに変換
            members_dto = [
                ExtractedParliamentaryGroupMemberDTO(
                    name=m.name,
                    role=m.role,
                    party_name=m.party_name,
                    district=m.district,
                    additional_info=m.additional_info,
                )
                for m in result
            ]

            logger.info(
                f"BAML extraction completed: {len(members_dto)} members extracted"
            )
            if members_dto:
                logger.debug(
                    f"Sample member: {members_dto[0].name} "
                    f"(role: {members_dto[0].role}, "
                    f"party: {members_dto[0].party_name}, "
                    f"district: {members_dto[0].district})"
                )

            return members_dto

        except Exception as e:
            logger.error(f"BAML extraction failed: {e}", exc_info=True)
            return []

    async def _fetch_html(self, url: str) -> str | None:
        """URLからHTMLを取得する

        Args:
            url: 取得するURL

        Returns:
            HTMLコンテンツ、エラー時はNone
        """
        try:
            async with PartyMemberPageFetcher() as fetcher:
                pages = await fetcher.fetch_all_pages(url, max_pages=1)
                if pages:
                    return pages[0].html_content
                logger.warning(f"No pages fetched from URL: {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching HTML from {url}: {str(e)}")
            # より詳細なエラー情報を提供
            if "playwright" in str(e).lower():
                logger.error(
                    "Playwright error - browser may not be properly installed. "
                    "Run: docker compose exec sagebase uv run playwright install"
                )
            return None
