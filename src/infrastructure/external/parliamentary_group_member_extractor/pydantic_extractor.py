"""議員団メンバー抽出器（Pydantic実装）

議員団のURLから所属議員情報を抽出する。
LLMを使用してさまざまな形式のWebページに対応可能。
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from src.domain.interfaces.parliamentary_group_member_extractor_service import (
    IParliamentaryGroupMemberExtractorService,
)
from src.domain.services.interfaces.llm_service import ILLMService
from src.infrastructure.external.llm_service import GeminiLLMService
from src.parliamentary_group_member_extractor.models import (
    ExtractedMember,
    ExtractedMemberList,
    MemberExtractionResult,
)
from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher

logger = logging.getLogger(__name__)


class PydanticParliamentaryGroupMemberExtractor(
    IParliamentaryGroupMemberExtractorService
):
    """議員団メンバー抽出器（Pydantic実装）

    PydanticOutputParserを使用してLLMから構造化データを抽出します。
    """

    def __init__(self, llm_service: GeminiLLMService | ILLMService | None = None):
        """初期化

        Args:
            llm_service: LLMサービスインスタンス
        """
        self.llm_service = llm_service or GeminiLLMService()

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
            text = "\n".join(chunk for chunk in chunks if chunk)

            # LLMで議員情報を抽出
            members = await self._extract_members_with_llm(text, str(soup))

            return MemberExtractionResult(
                parliamentary_group_id=parliamentary_group_id,
                url=url,
                extracted_members=members,
                extraction_date=datetime.now(),
            )

        except Exception as e:
            return MemberExtractionResult(
                parliamentary_group_id=parliamentary_group_id,
                url=url,
                extracted_members=[],
                error=str(e),
            )

    async def _extract_members_with_llm(
        self, text_content: str, html_content: str
    ) -> list[ExtractedMember]:
        """LLMを使用して議員情報を抽出する

        Args:
            text_content: テキストコンテンツ
            html_content: HTMLコンテンツ

        Returns:
            抽出された議員リスト
        """
        # 出力パーサーの設定
        output_parser = PydanticOutputParser(pydantic_object=ExtractedMemberList)

        # プロンプトテンプレートの作成
        prompt = PromptTemplate(
            template="""以下のWebページから議員団に所属する議員の情報を抽出してください。

membersフィールドに議員のリストを格納してください。各議員について以下の情報を抽出:
- name: 議員の氏名（必須）
- role: 議員団内での役職（団長、幹事長、政調会長など）
- party_name: 所属政党名（議員団名とは異なる場合）
- district: 選挙区
- additional_info: その他の重要な情報

注意事項:
- 議員団（会派）のメンバー一覧を抽出してください
- 役職者だけでなく、一般のメンバーも含めて全員を抽出してください
- 名前の表記は元のページの表記を維持してください
- 議員団名と政党名は異なる場合があります（例：「○○会派」と「△△党」）

テキストコンテンツ:
{text_content}

HTMLコンテンツ（構造の参考用）:
{html_content}

{format_instructions}
""",
            input_variables=["text_content", "html_content"],
            partial_variables={
                "format_instructions": output_parser.get_format_instructions()
            },
        )

        # LLMチェーンの実行 - GeminiLLMServiceの適切なメソッドを使用
        try:
            # HTMLが長すぎる場合は最初の部分のみを使用
            truncated_html = (
                html_content[:10000] if len(html_content) > 10000 else html_content
            )

            # プロンプトを作成
            formatted_prompt = prompt.format(
                text_content=text_content[:5000],
                html_content=truncated_html,
            )

            # GeminiLLMServiceのget_structured_llmを使って構造化された出力を取得
            structured_llm = self.llm_service.get_structured_llm(ExtractedMemberList)
            result = await structured_llm.ainvoke(formatted_prompt)

            # resultがExtractedMemberListであることを確認し、membersを返す
            if isinstance(result, ExtractedMemberList):
                return result.members
            else:
                return []

        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            # エラー時は空のリストを返す
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
