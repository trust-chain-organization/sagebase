"""Conference member extractor that saves to staging table"""

import asyncio
import logging
import os
from typing import Any, cast

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from playwright.async_api import async_playwright

from src.conference_member_extractor.models import ExtractedMember
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# フィーチャーフラグ
USE_BAML = os.getenv("USE_BAML_MEMBER_EXTRACTION", "false").lower() == "true"
ENABLE_AB_TEST = (
    os.getenv("ENABLE_MEMBER_EXTRACTION_AB_TEST", "false").lower() == "true"
)


class ConferenceMemberExtractor:
    """会議体メンバー情報を抽出してステージングテーブルに保存するクラス"""

    def __init__(self):
        # BAML extractorの条件付き初期化
        if USE_BAML or ENABLE_AB_TEST:
            from src.conference_member_extractor.baml_extractor import (
                BAMLMemberExtractor,
            )

            logger.info("Initializing BAML member extractor")
            self._baml_extractor = BAMLMemberExtractor()
        else:
            self._baml_extractor = None

        self.llm_service = LLMService()
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

    def extract_members_with_llm(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMember]:
        """LLMを使用してHTMLから議員情報を抽出

        フィーチャーフラグに基づいて、PydanticまたはBAML実装を使用します。
        A/Bテストモードが有効な場合は、両方の実装を実行して比較します。

        Args:
            html_content: HTMLコンテンツ
            conference_name: 会議体名

        Returns:
            抽出されたメンバーのリスト
        """
        # A/Bテストモード
        if ENABLE_AB_TEST:
            return self._extract_with_comparison(html_content, conference_name)

        # 本番モード
        if USE_BAML:
            logger.info("Using BAML implementation")
            return asyncio.run(
                self._baml_extractor.extract_members(html_content, conference_name)  # type: ignore
            )
        else:
            logger.info("Using Pydantic implementation")
            return self._extract_with_pydantic(html_content, conference_name)

    def _extract_with_pydantic(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMember]:
        """既存のPydantic実装（変更なし）"""
        from pydantic import BaseModel, Field

        # リストを扱うためのラッパークラス
        class ExtractedMemberList(BaseModel):
            members: list[ExtractedMember] = Field(description="抽出された議員リスト")

        # パーサーの設定
        parser = PydanticOutputParser(pydantic_object=ExtractedMemberList)

        # プロンプトテンプレート
        prompt = PromptTemplate(
            template="""以下のHTMLから{conference_name}の議員メンバー情報を抽出してください。

重要: このページに複数の委員会や議会の情報が含まれている場合、
必ず「{conference_name}」に所属する議員のみを抽出してください。
他の委員会や議会のメンバーは抽出しないでください。

HTMLコンテンツ:
{html_content}

抽出する情報:
1. 議員名（フルネーム）
2. 役職（議長、副議長、委員長、副委員長、委員など）
3. 所属政党名（わかる場合）
4. その他の重要な情報

注意事項:
- 議員名は姓名を正確に抽出してください
- 敬称（議員、氏、先生など）は除外してください
- 役職がない場合は「委員」としてください
- 議長、副議長、委員長などの役職者は必ず役職を明記してください
- 複数の役職がある場合は主要な役職を選択してください
- 所属政党が明記されていない場合はnullとしてください
- 必ず指定された「{conference_name}」に関連する議員のみを抽出し、
  他の委員会や議会のメンバーは含めないでください

{format_instructions}""",
            input_variables=["html_content", "conference_name"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        # LLMチェーンの実行
        chain = prompt | self.llm_service.llm | parser  # type: ignore

        try:
            # HTMLが長すぎる場合は切り詰める
            max_length = 50000
            if len(html_content) > max_length:
                html_content = html_content[:max_length] + "..."

            result = chain.invoke(  # type: ignore
                {"html_content": html_content, "conference_name": conference_name}
            )
            return cast(Any, result).members
        except Exception as e:
            logger.error(f"Error extracting members with LLM: {e}")
            return []

    def _extract_with_comparison(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMember]:
        """A/Bテストモード：両方の実装を実行して比較"""
        logger.info("=== A/B Test Mode Enabled ===")

        # Pydantic実装
        logger.info("Executing Pydantic implementation...")
        pydantic_result = self._extract_with_pydantic(html_content, conference_name)

        # BAML実装
        logger.info("Executing BAML implementation...")
        baml_result = asyncio.run(
            self._baml_extractor.extract_members(html_content, conference_name)  # type: ignore
        )

        # 比較ログ
        logger.info("=== Comparison Results ===")
        logger.info(f"Pydantic: {len(pydantic_result)} members")
        logger.info(f"BAML: {len(baml_result)} members")

        # 詳細な差分記録
        self._log_comparison_details(pydantic_result, baml_result)

        # デフォルトはPydantic結果を返す（安全側）
        logger.info("Returning Pydantic results (default in A/B test mode)")
        return pydantic_result

    def _log_comparison_details(
        self, pydantic_result: list[ExtractedMember], baml_result: list[ExtractedMember]
    ) -> None:
        """比較の詳細をログに記録"""
        logger.info("Pydantic names: " + ", ".join([m.name for m in pydantic_result]))
        logger.info("BAML names: " + ", ".join([m.name for m in baml_result]))

        # 名前の差分を検出
        pydantic_names = {m.name for m in pydantic_result}
        baml_names = {m.name for m in baml_result}

        only_in_pydantic = pydantic_names - baml_names
        only_in_baml = baml_names - pydantic_names

        if only_in_pydantic:
            logger.info(f"Only in Pydantic: {only_in_pydantic}")
        if only_in_baml:
            logger.info(f"Only in BAML: {only_in_baml}")

        # TODO: トークン数、レイテンシなどのメトリクスを追加

    async def extract_and_save_members(
        self, conference_id: int, conference_name: str, url: str
    ) -> dict[str, Any]:
        """会議体メンバー情報を抽出してステージングテーブルに保存"""
        logger.info(f"Extracting members from {url} for conference {conference_name}")

        try:
            # HTMLを取得
            html_content = await self.fetch_html(url)

            # LLMで議員情報を抽出
            members = self.extract_members_with_llm(html_content, conference_name)

            # ステージングテーブルに保存
            saved_count = 0
            failed_count = 0

            for member in members:
                member_id = self.repo.create_extracted_member(
                    conference_id=conference_id,
                    extracted_name=member.name,
                    source_url=url,
                    extracted_role=member.role,
                    extracted_party_name=member.party_name,
                    additional_info=member.additional_info,
                )

                if member_id:
                    saved_count += 1
                    logger.info(
                        f"Saved extracted member: {member.name} "
                        f"(role: {member.role}, party: {member.party_name})"
                    )
                else:
                    failed_count += 1
                    logger.error(f"Failed to save member: {member.name}")

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
