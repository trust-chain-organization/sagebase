"""Conference member extractor that saves to staging table"""

import logging

from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.domain.dtos.conference_member_dto import ExtractedMemberDTO
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.infrastructure.external.conference_member_extractor.factory import (
    MemberExtractorFactory,
)
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


logger = logging.getLogger(__name__)


class ConferenceMemberExtractor:
    """会議体メンバー情報を抽出してステージングテーブルに保存するクラス"""

    def __init__(self):
        # ファクトリーからextractorを取得
        self._extractor = MemberExtractorFactory.create()
        self.repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)

    async def fetch_html(self, url: str) -> str:
        """URLからHTMLを取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)  # 動的コンテンツの読み込み待機
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

            # 不要なタグを削除
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

            # コメントを削除
            from bs4 import Comment

            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            # メインコンテンツを抽出（mainタグがあれば優先）
            main_content = soup.find("main")
            if main_content:
                cleaned_html = str(main_content)
            else:
                # mainタグがない場合は全体を使用
                cleaned_html = str(soup)

            # 余分な空白・改行を削除
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
            # メモリ不足の場合は強制的に切り詰める
            logger.error("Memory error while cleaning HTML, truncating to 50000 chars")
            return html_content[:50000] + "..."

        except Exception as e:
            # その他のエラーは元のHTMLを返す（デグレード）
            logger.warning(
                f"Failed to clean HTML: {type(e).__name__}: {e}, "
                f"using original content (size: {len(html_content)})"
            )
            return html_content

    async def extract_members_with_llm(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMemberDTO]:
        """LLMを使用してHTMLから議員情報を抽出

        ファクトリーから取得した実装を使用してメンバー情報を抽出します。
        フィーチャーフラグに応じて、Pydantic、BAML、またはA/Bテスト実装が使用されます。

        Args:
            html_content: HTMLコンテンツ
            conference_name: 会議体名

        Returns:
            抽出されたメンバーのリスト

        Note:
            この関数は非同期です。awaitして呼び出してください。
        """
        # HTMLをクリーニング
        cleaned_html = self.clean_html(html_content)

        # ファクトリーから取得したextractorを使用（非同期）
        # 戻り値は既にExtractedMemberDTOのリスト（型安全性向上）
        return await self._extractor.extract_members(cleaned_html, conference_name)

    async def extract_and_save_members(
        self, conference_id: int, conference_name: str, url: str
    ) -> dict[str, Any]:
        """会議体メンバー情報を抽出してステージングテーブルに保存"""
        logger.info(f"Extracting members from {url} for conference {conference_name}")

        try:
            # HTMLを取得
            html_content = await self.fetch_html(url)

            # LLMで議員情報を抽出
            members = await self.extract_members_with_llm(html_content, conference_name)

            # ステージングテーブルに保存
            saved_count = 0
            failed_count = 0

            for member in members:
                try:
                    # DTOからエンティティを作成
                    entity = ExtractedConferenceMember(
                        conference_id=conference_id,
                        extracted_name=member.name,
                        source_url=url,
                        extracted_role=member.role,
                        extracted_party_name=member.party_name,
                        additional_data=member.additional_info,
                    )

                    # リポジトリのcreate()メソッドを使用（async関数内なのでawait必要）
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
                "conference_id": conference_id,
                "conference_name": conference_name,
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
            logger.error(f"Error extracting conference members: {e}")
            return {
                "conference_id": conference_id,
                "conference_name": conference_name,
                "url": url,
                "extracted_count": 0,
                "saved_count": 0,
                "failed_count": 0,
                "error": str(e),
            }

    def close(self):
        """リポジトリの接続を閉じる"""
        self.repo.close()
