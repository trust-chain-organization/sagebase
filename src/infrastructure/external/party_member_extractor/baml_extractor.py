"""政党メンバー抽出器（BAML実装）

政党のURLから所属議員情報を抽出する。
BAMLを使用してトークン効率とパース精度を向上。
"""

import logging
import re
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from baml_client.async_client import b
from src.domain.dtos.party_member_dto import (
    ExtractedPartyMemberDTO,
    PartyMemberExtractionResultDTO,
)
from src.domain.interfaces.party_member_extractor_service import (
    IPartyMemberExtractorService,
)
from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher
from src.party_member_extractor.models import (
    PartyMemberInfo,
    PartyMemberList,
    WebPageContent,
)


logger = logging.getLogger(__name__)


class BAMLPartyMemberExtractor(IPartyMemberExtractorService):
    """政党メンバー抽出器（BAML実装）

    BAMLを使用して政党メンバー情報を抽出するクラス。
    Pydantic実装と比較して、トークン効率とパース精度の向上を目指します。
    """

    async def extract_members(
        self, party_id: int, url: str
    ) -> PartyMemberExtractionResultDTO:
        """政党URLからメンバー情報を抽出する

        Args:
            party_id: 政党ID
            url: 政党メンバー一覧のURL

        Returns:
            抽出結果（DTO）
        """
        try:
            # HTMLを取得
            html_content = await self._fetch_html(url)
            if not html_content:
                return PartyMemberExtractionResultDTO(
                    party_id=party_id,
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

            # メインコンテンツを抽出
            main_content = self._extract_main_content(soup)

            if not main_content:
                logger.warning(f"No main content found in {url}")
                return PartyMemberExtractionResultDTO(
                    party_id=party_id,
                    url=url,
                    extracted_members=[],
                    extraction_date=None,
                    error="メインコンテンツを抽出できませんでした",
                )

            # コンテンツが長すぎる場合は切り詰める
            max_length = 50000
            if len(main_content) > max_length:
                logger.warning(
                    f"Content too long ({len(main_content)} chars), "
                    f"truncating to {max_length} chars"
                )
                main_content = main_content[:max_length] + "..."

            # LLMで議員情報を抽出（BAML使用）
            members_dto = await self._extract_members_with_baml(main_content, url)

            return PartyMemberExtractionResultDTO(
                party_id=party_id,
                url=url,
                extracted_members=members_dto,
                extraction_date=datetime.now(),
                error=None,
            )

        except Exception as e:
            logger.error(f"BAML extraction error: {e}", exc_info=True)
            return PartyMemberExtractionResultDTO(
                party_id=party_id,
                url=url,
                extracted_members=[],
                extraction_date=None,
                error=str(e),
            )

    async def _extract_members_with_baml(
        self, main_content: str, url: str
    ) -> list[ExtractedPartyMemberDTO]:
        """BAMLを使用して議員情報を抽出する

        Args:
            main_content: メインコンテンツのテキスト
            url: 元のURL

        Returns:
            抽出された議員リスト（DTO）
        """
        try:
            # ベースURLを取得
            base_url = self._get_base_url(url)

            # 政党名を仮設定（URLから推測）
            party_name = "政党"  # 実際の実装では、党IDから名前を取得すべき

            # BAML関数を呼び出し
            logger.info(f"Calling BAML ExtractPartyMembers for '{party_name}'")
            baml_result = await b.ExtractPartyMembers(
                main_content, party_name, base_url
            )

            # BAMLの結果をDTOに変換
            members_dto = []
            for m in baml_result:
                # URLを絶対URLに変換
                profile_url = m.profile_url
                if profile_url and not profile_url.startswith("http"):
                    profile_url = base_url + profile_url.lstrip("/")

                members_dto.append(
                    ExtractedPartyMemberDTO(
                        name=m.name,
                        position=m.position,
                        electoral_district=m.electoral_district,
                        prefecture=m.prefecture,
                        profile_url=profile_url,
                        party_position=m.party_position,
                    )
                )

            logger.info(f"BAML extracted {len(members_dto)} members")
            return members_dto

        except Exception as e:
            logger.error(f"BAML extraction failed: {e}", exc_info=True)
            return []

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """メインコンテンツを抽出

        Args:
            soup: BeautifulSoupオブジェクト

        Returns:
            str: メインコンテンツのテキスト
        """
        # メインコンテンツの候補セレクタ
        main_selectors = [
            "main",
            '[role="main"]',
            "#main",
            "#content",
            ".main-content",
            ".content",
            "article",
            ".container",
            ".wrapper",
        ]

        for selector in main_selectors:
            main = soup.select_one(selector)
            if main:
                content = self._clean_text(main.get_text(separator="\n", strip=True))
                # コンテンツが短すぎる場合はスキップ
                if len(content) > 500:  # 最低500文字以上
                    logger.info(
                        f"Found main content with '{selector}': {len(content)} chars"
                    )
                    return content

        # 見つからない場合はbody全体
        body = soup.find("body")
        if body and isinstance(body, Tag):
            # ヘッダーとフッターを除外
            for tag in body.find_all(["header", "footer", "nav", "aside"]):
                if isinstance(tag, Tag):
                    tag.decompose()

            content = self._clean_text(body.get_text(separator="\n", strip=True))
            logger.info(f"Using body content: {len(content)} chars")
            return content

        # bodyタグも見つからない場合は全体
        content = self._clean_text(soup.get_text(separator="\n", strip=True))
        logger.info(f"Using full page content: {len(content)} chars")
        return content

    def _clean_text(self, text: str) -> str:
        """テキストをクリーンアップ

        Args:
            text: クリーンアップするテキスト

        Returns:
            str: クリーンアップされたテキスト
        """
        # 複数の空行を1つに
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        # 行頭行末の空白を削除
        lines = [line.strip() for line in text.split("\n")]
        # 空行でない行だけを残す
        lines = [line for line in lines if line]
        return "\n".join(lines)

    def _get_base_url(self, url: str) -> str:
        """URLからベースURLを取得

        Args:
            url: URL

        Returns:
            str: ベースURL
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/"

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

    async def extract_from_html(
        self, html_content: str, source_url: str, party_name: str
    ) -> PartyMemberExtractionResultDTO:
        """HTMLコンテンツから直接メンバー情報を抽出する（互換性メソッド）

        Args:
            html_content: HTMLコンテンツ
            source_url: 元のURL
            party_name: 政党名

        Returns:
            抽出結果（DTO）
        """
        try:
            # BeautifulSoupでHTMLを解析
            soup = BeautifulSoup(html_content, "html.parser")

            # スクリプトとスタイルを削除
            for script in soup(["script", "style"]):
                script.decompose()

            # メインコンテンツを抽出
            main_content = self._extract_main_content(soup)

            if not main_content:
                logger.warning(f"No main content found in {source_url}")
                return PartyMemberExtractionResultDTO(
                    party_id=0,  # party_idは呼び出し側で設定
                    url=source_url,
                    extracted_members=[],
                    extraction_date=None,
                    error="メインコンテンツを抽出できませんでした",
                )

            # コンテンツが長すぎる場合は切り詰める
            max_length = 50000
            if len(main_content) > max_length:
                logger.warning(
                    f"Content too long ({len(main_content)} chars), "
                    f"truncating to {max_length} chars"
                )
                main_content = main_content[:max_length] + "..."

            # LLMで議員情報を抽出（BAML使用）
            members_dto = await self._extract_members_with_baml_for_party(
                main_content, source_url, party_name
            )

            return PartyMemberExtractionResultDTO(
                party_id=0,  # party_idは呼び出し側で設定
                url=source_url,
                extracted_members=members_dto,
                extraction_date=datetime.now(),
                error=None,
            )

        except Exception as e:
            logger.error(f"BAML extraction error: {e}", exc_info=True)
            return PartyMemberExtractionResultDTO(
                party_id=0,
                url=source_url,
                extracted_members=[],
                extraction_date=None,
                error=str(e),
            )

    async def _extract_members_with_baml_for_party(
        self, main_content: str, url: str, party_name: str
    ) -> list[ExtractedPartyMemberDTO]:
        """BAMLを使用して議員情報を抽出する（政党名指定版）

        Args:
            main_content: メインコンテンツのテキスト
            url: 元のURL
            party_name: 政党名

        Returns:
            抽出された議員リスト（DTO）
        """
        try:
            # ベースURLを取得
            base_url = self._get_base_url(url)

            # BAML関数を呼び出し
            logger.info(f"Calling BAML ExtractPartyMembers for '{party_name}'")
            baml_result = await b.ExtractPartyMembers(
                main_content, party_name, base_url
            )

            # BAMLの結果をDTOに変換
            members_dto = []
            for m in baml_result:
                # URLを絶対URLに変換
                profile_url = m.profile_url
                if profile_url and not profile_url.startswith("http"):
                    profile_url = base_url + profile_url.lstrip("/")

                members_dto.append(
                    ExtractedPartyMemberDTO(
                        name=m.name,
                        position=m.position,
                        electoral_district=m.electoral_district,
                        prefecture=m.prefecture,
                        profile_url=profile_url,
                        party_position=m.party_position,
                    )
                )

            logger.info(f"BAML extracted {len(members_dto)} members")
            return members_dto

        except Exception as e:
            logger.error(f"BAML extraction failed: {e}", exc_info=True)
            return []

    async def extract_from_pages(
        self, pages: list[WebPageContent], party_name: str
    ) -> PartyMemberList:
        """複数ページから議員情報を抽出（後方互換性メソッド）

        Args:
            pages: WebPageContentのリスト
            party_name: 政党名

        Returns:
            PartyMemberList: 抽出されたメンバー情報
        """
        # 非同期関数を直接呼び出し
        return await self._extract_from_pages_async(pages, party_name)

    async def _extract_from_pages_async(
        self, pages: list[WebPageContent], party_name: str
    ) -> PartyMemberList:
        """複数ページから議員情報を抽出（非同期）

        Args:
            pages: WebPageContentのリスト
            party_name: 政党名

        Returns:
            PartyMemberList: 抽出されたメンバー情報
        """
        all_members: list[PartyMemberInfo] = []

        logger.info(
            f"Starting BAML extraction from {len(pages)} pages for {party_name}"
        )

        for page in pages:
            logger.info(f"Extracting from page {page.page_number}: {page.url}")

            # extract_from_htmlを使用して各ページを処理
            result_dto = await self.extract_from_html(
                page.html_content, page.url, party_name
            )

            if result_dto.error:
                logger.warning(
                    f"Error extracting from page {page.page_number}: {result_dto.error}"
                )
                continue

            if result_dto.extracted_members:
                member_count = len(result_dto.extracted_members)
                logger.info(
                    f"Extracted {member_count} members from page {page.page_number}"
                )

                # DTOをPartyMemberInfoに変換し、重複チェック
                existing_names: set[str] = {m.name for m in all_members}
                new_members_count = 0

                for member_dto in result_dto.extracted_members:
                    if member_dto.name not in existing_names:
                        # DTOからPartyMemberInfoに変換
                        member_info = PartyMemberInfo(
                            name=member_dto.name,
                            position=member_dto.position,
                            electoral_district=member_dto.electoral_district,
                            prefecture=member_dto.prefecture,
                            profile_url=member_dto.profile_url,
                            party_position=member_dto.party_position,
                        )
                        all_members.append(member_info)
                        existing_names.add(member_dto.name)
                        new_members_count += 1
                        logger.debug(f"Added member: {member_dto.name}")

                if new_members_count < member_count:
                    skipped = member_count - new_members_count
                    logger.info(f"Skipped {skipped} duplicate members")
            else:
                logger.warning(f"No members extracted from page {page.page_number}")

        result = PartyMemberList(
            members=all_members, total_count=len(all_members), party_name=party_name
        )

        logger.info(f"Total extracted members: {len(all_members)}")
        if all_members:
            logger.info(
                f"Members: {', '.join([m.name for m in all_members[:10]])}"
                + (
                    f"... and {len(all_members) - 10} more"
                    if len(all_members) > 10
                    else ""
                )
            )
        return result
