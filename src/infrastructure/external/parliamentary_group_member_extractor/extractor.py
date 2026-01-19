"""Parliamentary group member extractor that uses LangGraph agent

LangGraph + BAML の二層構造で議員団メンバー抽出を実現。
Issue #905: [LangGraph+BAML] 議員団メンバー抽出のエージェント化

Note:
    このクラスはHTML取得とメンバー抽出のみを担当します。
    エンティティ作成やDB保存はUseCaseで行うべきです（Clean Architecture）。
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.application.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
    ParliamentaryGroupMemberAgentResultDTO,
)
from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
    ParliamentaryGroupMemberExtractorFactory,
)


if TYPE_CHECKING:
    from src.domain.interfaces.parliamentary_group_member_extraction_agent import (
        IParliamentaryGroupMemberExtractionAgent,
    )


logger = logging.getLogger(__name__)


# 定数定義
PAGE_LOAD_TIMEOUT_MS = 30000  # ページ読み込みタイムアウト（ミリ秒）
DYNAMIC_CONTENT_WAIT_MS = 2000  # 動的コンテンツ読み込み待機時間（ミリ秒）
MAX_HTML_LENGTH = 50000  # HTMLの最大長（メモリエラー回避用）


class ParliamentaryGroupMemberExtractor:
    """議員団メンバー情報をURLから抽出するクラス

    LangGraph ReActエージェントを使用して、試行錯誤による高精度な抽出を実現。

    Note:
        このクラスは抽出のみを担当します。
        DB保存やエンティティ作成はPresenterまたはUseCaseで行ってください。
    """

    def __init__(
        self,
        agent: IParliamentaryGroupMemberExtractionAgent | None = None,
    ):
        """初期化する。

        Args:
            agent: 議員団メンバー抽出エージェント（省略時はファクトリから作成）
        """
        self._agent = agent or ParliamentaryGroupMemberExtractorFactory.create_agent()
        logger.info(
            f"ParliamentaryGroupMemberExtractor initialized "
            f"with {type(self._agent).__name__}"
        )

    async def fetch_html(self, url: str) -> str:
        """URLからHTMLを取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(
                    url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS
                )
                await page.wait_for_timeout(DYNAMIC_CONTENT_WAIT_MS)
                content = await page.content()
                return content
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                raise
            finally:
                await browser.close()

    def clean_html(self, html_content: str) -> str:
        """HTMLをクリーニングして不要な要素を削除

        Args:
            html_content: 元のHTMLコンテンツ

        Returns:
            クリーニングされたHTMLコンテンツ
        """
        logger.info(f"Cleaning HTML (original size: {len(html_content)} chars)")

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            unwanted_tags = [
                "script",
                "style",
                "nav",
                "header",
                "footer",
                "aside",
                "iframe",
                "noscript",
                "svg",
                "canvas",
                "video",
                "audio",
                "form",
                "button",
                "input",
                "select",
                "textarea",
            ]

            for tag in unwanted_tags:
                for element in soup.find_all(tag):
                    element.decompose()

            from bs4 import Comment

            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            main_content = soup.find("main")
            if main_content:
                cleaned_html = str(main_content)
            else:
                cleaned_html = str(soup)

            import re

            cleaned_html = re.sub(r"\s+", " ", cleaned_html)
            cleaned_html = re.sub(r">\s+<", "><", cleaned_html)

            logger.info(
                f"HTML cleaned (new size: {len(cleaned_html)} chars, "
                f"reduction: {len(html_content) - len(cleaned_html)} chars, "
                f"{(1 - len(cleaned_html) / len(html_content)) * 100:.1f}%)"
            )

            return cleaned_html

        except MemoryError:
            logger.error(
                f"Memory error while cleaning HTML, truncating to {MAX_HTML_LENGTH}"
            )
            return html_content[:MAX_HTML_LENGTH] + "..."

        except Exception as e:
            logger.warning(
                f"Failed to clean HTML: {type(e).__name__}: {e}, "
                f"using original content (size: {len(html_content)})"
            )
            return html_content

    async def extract_members_with_agent(
        self, html_content: str, parliamentary_group_name: str
    ) -> list[ExtractedParliamentaryGroupMemberDTO]:
        """LangGraphエージェントを使用してHTMLから議員情報を抽出

        ReActエージェントが以下の手順でメンバーを抽出します:
        1. BAMLを使用してHTMLからメンバーを抽出
        2. 抽出結果を検証
        3. 重複メンバーを除去

        Args:
            html_content: HTMLコンテンツ
            parliamentary_group_name: 議員団名

        Returns:
            抽出されたメンバーのリスト
        """
        cleaned_html = self.clean_html(html_content)

        result = await self._agent.extract_members(
            html_content=cleaned_html,
            parliamentary_group_name=parliamentary_group_name,
        )

        if not result.success:
            if result.error_message:
                logger.warning(
                    f"Agent extraction had issues for '{parliamentary_group_name}': "
                    f"{result.error_message}"
                )
            if result.validation_errors:
                logger.warning(
                    f"Validation errors for '{parliamentary_group_name}': "
                    f"{result.validation_errors}"
                )

        return result.members

    async def extract_members_from_url(
        self, url: str, parliamentary_group_name: str
    ) -> ParliamentaryGroupMemberAgentResultDTO:
        """URLから議員団メンバー情報を抽出

        URLからHTMLを取得し、LangGraphエージェントを使用してメンバーを抽出します。

        Args:
            url: 議員団メンバー一覧ページのURL
            parliamentary_group_name: 議員団名

        Returns:
            抽出結果（ParliamentaryGroupMemberAgentResultDTO）

        Note:
            DB保存やエンティティ作成は呼び出し元で行ってください。
        """
        logger.info(
            f"Extracting members from {url} for "
            f"parliamentary group {parliamentary_group_name}"
        )

        try:
            html_content = await self.fetch_html(url)
            members = await self.extract_members_with_agent(
                html_content, parliamentary_group_name
            )

            logger.info(
                f"Extraction complete: {len(members)} members extracted "
                f"from '{parliamentary_group_name}'"
            )

            return ParliamentaryGroupMemberAgentResultDTO(
                members=members,
                success=len(members) > 0,
                validation_errors=[],
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Error extracting parliamentary group members: {e}")
            return ParliamentaryGroupMemberAgentResultDTO(
                members=[],
                success=False,
                validation_errors=[],
                error_message=str(e),
            )
