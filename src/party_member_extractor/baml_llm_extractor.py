"""BAML-based party member extractor

このモジュールは、BAMLを使用して政党メンバー情報を抽出します。
既存のPydantic実装と並行して動作し、フィーチャーフラグで切り替え可能です。
"""

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urlparse

import nest_asyncio
from bs4 import BeautifulSoup, Tag

from baml_client.async_client import b

from ..infrastructure.persistence.llm_history_helper import SyncLLMHistoryHelper
from .models import PartyMemberInfo, PartyMemberList, WebPageContent


# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

logger = logging.getLogger(__name__)


class BAMLPartyMemberExtractor:
    """BAML-based party member extractor

    BAMLを使用して政党メンバー情報を抽出するクラス。
    既存のPydanticモデルとの互換性を保ちつつ、
    トークン効率とパース精度の向上を目指します。
    """

    def __init__(
        self,
        llm_service: Any | None = None,
        party_id: int | None = None,
        proc_logger: Any = None,
    ):
        """Initialize BAMLPartyMemberExtractor

        Args:
            llm_service: LLMService instance (not used in BAML implementation)
            party_id: ID of the party being processed (for history tracking)
            proc_logger: ProcessingLogger instance (optional)
        """
        self.party_id = party_id
        self.history_helper = SyncLLMHistoryHelper()
        self.proc_logger = proc_logger
        if party_id is not None:
            self.log_key = party_id

    def extract_from_pages(
        self, pages: list[WebPageContent], party_name: str
    ) -> PartyMemberList:
        """複数ページから議員情報を抽出

        Args:
            pages: WebPageContentのリスト
            party_name: 政党名

        Returns:
            PartyMemberList: 抽出されたメンバー情報
        """
        # 非同期関数を同期的に実行
        return asyncio.run(self._extract_from_pages_async(pages, party_name))

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
            members = await self._extract_from_single_page(page, party_name)

            if members and members.members:
                member_count = len(members.members)
                logger.info(
                    f"Extracted {member_count} members from page {page.page_number}"
                )
                # 重複チェック
                existing_names: set[str] = {m.name for m in all_members}
                new_members_count = 0
                for member in members.members:
                    if member.name not in existing_names:
                        all_members.append(member)
                        existing_names.add(member.name)
                        new_members_count += 1
                        logger.debug(f"Added member: {member.name}")
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

    async def _extract_from_single_page(
        self, page: WebPageContent, party_name: str
    ) -> PartyMemberList | None:
        """単一ページから議員情報を抽出

        Args:
            page: WebPageContent
            party_name: 政党名

        Returns:
            PartyMemberList | None: 抽出されたメンバー情報（エラー時はNone）
        """
        try:
            # HTMLをテキストに変換（構造を保持）
            soup = BeautifulSoup(page.html_content, "html.parser")

            # スクリプトとスタイルを削除
            for script in soup(["script", "style"]):
                script.decompose()

            # メインコンテンツを抽出
            main_content = self._extract_main_content(soup)

            if not main_content:
                logger.warning(f"No main content found in {page.url}")
                return None

            # コンテンツが長すぎる場合は切り詰める
            max_length = 50000
            if len(main_content) > max_length:
                logger.warning(
                    f"Content too long ({len(main_content)} chars), "
                    f"truncating to {max_length} chars"
                )
                main_content = main_content[:max_length] + "..."

            # Record history before extraction if party_id is available
            if self.party_id is not None:
                self._record_extraction_to_history(
                    party_name=party_name,
                    page_url=page.url,
                    content_length=len(main_content),
                    status="started",
                )

            # BAML関数を呼び出し
            base_url = self._get_base_url(page.url)
            logger.info(
                f"Calling BAML ExtractPartyMembers for '{party_name}' "
                f"(base_url: {base_url})"
            )
            baml_result = await b.ExtractPartyMembers(
                main_content, party_name, base_url
            )

            # PartyMemberInfoに変換
            members = []
            for m in baml_result:
                # URLを絶対URLに変換
                profile_url = m.profile_url
                if profile_url and not profile_url.startswith("http"):
                    profile_url = base_url + profile_url.lstrip("/")

                members.append(
                    PartyMemberInfo(
                        name=m.name,
                        position=m.position,
                        electoral_district=m.electoral_district,
                        prefecture=m.prefecture,
                        profile_url=profile_url,
                        party_position=m.party_position,
                    )
                )

            result = PartyMemberList(
                members=members, total_count=len(members), party_name=party_name
            )

            # Record successful extraction
            if self.party_id is not None:
                self._record_extraction_to_history(
                    party_name=party_name,
                    page_url=page.url,
                    content_length=len(main_content),
                    status="completed",
                    members_count=len(members),
                )

            logger.info(f"BAML extracted {len(members)} members")
            return result

        except Exception as e:
            logger.error(f"BAML extraction failed: {e}", exc_info=True)
            if self.proc_logger:
                self.proc_logger.add_log(
                    self.log_key, f"❌ BAML抽出エラー: {str(e)[:200]}", "error"
                )
            return None

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

    def _record_extraction_to_history(
        self,
        party_name: str,
        page_url: str,
        content_length: int,
        status: str,
        members_count: int = 0,
    ) -> None:
        """Record extraction to LLM history

        Args:
            party_name: 政党名
            page_url: ページURL
            content_length: コンテンツ長
            status: ステータス（"started" or "completed"）
            members_count: 抽出されたメンバー数
        """
        try:
            if status == "started":
                logger.debug(
                    f"Starting BAML extraction for {party_name} from {page_url} "
                    f"(content_length: {content_length})"
                )
            elif status == "completed":
                # Record using the history helper's method
                self.history_helper.record_politician_extraction(
                    party_name=party_name,
                    page_url=page_url,
                    extracted_count=members_count,
                    party_id=self.party_id,
                    model_name="gemini-2.0-flash-exp",  # BAML uses Gemini2Flash
                    prompt_template="party_member_extract_baml",
                )
                logger.debug(
                    f"Completed BAML extraction for {party_name}: "
                    f"{members_count} members"
                )
        except Exception as e:
            logger.error(f"Failed to record extraction history: {e}")
