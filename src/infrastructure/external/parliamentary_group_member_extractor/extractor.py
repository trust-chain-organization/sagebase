"""Parliamentary group member extractor that uses LangGraph agent

LangGraph + BAML の二層構造で議員団メンバー抽出を実現。
Issue #905: [LangGraph+BAML] 議員団メンバー抽出のエージェント化
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.domain.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
)
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
    ParliamentaryGroupMemberExtractorFactory,
)
from src.infrastructure.persistence.extracted_parliamentary_group_member_repository_impl import (  # noqa: E501
    ExtractedParliamentaryGroupMemberRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


if TYPE_CHECKING:
    from src.application.usecases.update_extracted_parliamentary_group_member_from_extraction_usecase import (  # noqa: E501
        UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase,
    )
    from src.domain.interfaces.parliamentary_group_member_extraction_agent import (
        IParliamentaryGroupMemberExtractionAgent,
    )


logger = logging.getLogger(__name__)


class ParliamentaryGroupMemberExtractor:
    """議員団メンバー情報を抽出してステージングテーブルに保存するクラス

    LangGraph ReActエージェントを使用して、試行錯誤による高精度な抽出を実現。
    会議体メンバー抽出と同様のパターンで実装。
    """

    def __init__(
        self,
        update_usecase: (
            UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase | None
        ) = None,
        agent: IParliamentaryGroupMemberExtractionAgent | None = None,
    ):
        """初期化する。

        Args:
            update_usecase: 抽出ログを記録するためのUseCase（オプション）
            agent: 議員団メンバー抽出エージェント（省略時はファクトリから作成）
        """
        self._agent = agent or ParliamentaryGroupMemberExtractorFactory.create_agent()
        self.repo = RepositoryAdapter(ExtractedParliamentaryGroupMemberRepositoryImpl)
        self._update_usecase = update_usecase
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
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
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
            logger.error("Memory error while cleaning HTML, truncating to 50000 chars")
            return html_content[:50000] + "..."

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

    async def extract_and_save_members(
        self, parliamentary_group_id: int, parliamentary_group_name: str, url: str
    ) -> dict[str, Any]:
        """議員団メンバー情報を抽出してステージングテーブルに保存"""
        logger.info(
            f"Extracting members from {url} for "
            f"parliamentary group {parliamentary_group_name}"
        )

        try:
            html_content = await self.fetch_html(url)
            members = await self.extract_members_with_agent(
                html_content, parliamentary_group_name
            )

            saved_count = 0
            failed_count = 0

            for member in members:
                try:
                    entity = ExtractedParliamentaryGroupMember(
                        parliamentary_group_id=parliamentary_group_id,
                        extracted_name=member.name,
                        source_url=url,
                        extracted_role=member.role,
                        extracted_party_name=member.party_name,
                        extracted_district=member.district,
                        additional_info=member.additional_info,
                    )

                    created_entity = await self.repo.create(entity)

                    if created_entity:
                        saved_count += 1
                        logger.info(
                            f"Saved extracted member: {member.name} "
                            f"(role: {member.role}, party: {member.party_name})"
                        )
                    else:
                        failed_count += 1
                        logger.error(f"Failed to save member: {member.name}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error saving member {member.name}: {e}")

            result: dict[str, Any] = {
                "parliamentary_group_id": parliamentary_group_id,
                "parliamentary_group_name": parliamentary_group_name,
                "url": url,
                "extracted_count": len(members),
                "saved_count": saved_count,
                "failed_count": failed_count,
            }

            logger.info(
                f"Extraction complete: extracted={len(members)}, "
                f"saved={saved_count}, failed={failed_count}"
            )

            return result

        except Exception as e:
            logger.error(f"Error extracting parliamentary group members: {e}")
            return {
                "parliamentary_group_id": parliamentary_group_id,
                "parliamentary_group_name": parliamentary_group_name,
                "url": url,
                "extracted_count": 0,
                "saved_count": 0,
                "failed_count": 0,
                "error": str(e),
            }

    def close(self):
        """リポジトリの接続を閉じる"""
        self.repo.close()
