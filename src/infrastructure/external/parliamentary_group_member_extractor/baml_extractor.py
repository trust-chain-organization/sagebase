"""議員団メンバー抽出器（BAML実装）

議員団のURLから所属議員情報を抽出する。
BAMLを使用してトークン効率とパース精度を向上。
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

import baml_client as b
from src.domain.interfaces.parliamentary_group_member_extractor_service import (
    IParliamentaryGroupMemberExtractorService,
)
from src.parliamentary_group_member_extractor.models import (
    ExtractedMember,
    MemberExtractionResult,
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
    ) -> MemberExtractionResult:
        """議員団URLからメンバー情報を抽出する

        Args:
            parliamentary_group_id: 議員団ID
            url: 議員団メンバー一覧のURL

        Returns:
            抽出結果
        """
        try:
            # HTMLを取得
            html_content = await self._fetch_html(url)
            if not html_content:
                return MemberExtractionResult(
                    parliamentary_group_id=parliamentary_group_id,
                    url=url,
                    extracted_members=[],
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
            members = await self._extract_members_with_baml(text_content, str(soup))

            return MemberExtractionResult(
                parliamentary_group_id=parliamentary_group_id,
                url=url,
                extracted_members=members,
                extraction_date=datetime.now(),
            )

        except Exception as e:
            logger.error(f"BAML extraction error: {e}", exc_info=True)
            return MemberExtractionResult(
                parliamentary_group_id=parliamentary_group_id,
                url=url,
                extracted_members=[],
                error=str(e),
            )

    async def _extract_members_with_baml(
        self, text_content: str, html_content: str
    ) -> list[ExtractedMember]:
        """BAMLを使用して議員情報を抽出する

        Args:
            text_content: テキストコンテンツ
            html_content: HTMLコンテンツ

        Returns:
            抽出された議員リスト
        """
        try:
            # HTMLとテキストが長すぎる場合は切り詰める
            max_text_length = 5000
            max_html_length = 10000

            if len(text_content) > max_text_length:
                logger.warning(
                    f"Text content too long ({len(text_content)} chars), "
                    f"truncating to {max_text_length} chars"
                )
                text_content = text_content[:max_text_length]

            if len(html_content) > max_html_length:
                logger.warning(
                    f"HTML content too long ({len(html_content)} chars), "
                    f"truncating to {max_html_length} chars"
                )
                html_content = html_content[:max_html_length]

            # BAML関数を呼び出し
            logger.info("Calling BAML ExtractParliamentaryGroupMembers")
            result = await b.ExtractParliamentaryGroupMembers(
                html_content, text_content
            )

            # BAMLの結果をPydanticモデルに変換
            members = [
                ExtractedMember(
                    name=m.name,
                    role=m.role,
                    party_name=m.party_name,
                    district=m.district,
                    additional_info=m.additional_info,
                )
                for m in result
            ]

            logger.info(f"BAML extracted {len(members)} members")
            return members

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
