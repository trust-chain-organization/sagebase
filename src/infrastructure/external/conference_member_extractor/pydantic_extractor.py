"""Pydantic-based conference member extractor

Pydantic + LangChainを使用した従来のメンバー抽出実装。
"""

import logging
from typing import Any, cast

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from src.domain.dtos.conference_member_dto import ExtractedMemberDTO
from src.domain.interfaces.member_extractor_service import IMemberExtractorService
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class PydanticMemberExtractor(IMemberExtractorService):
    """Pydantic-based member extractor

    LangChain + PydanticOutputParserを使用する従来の実装。
    """

    def __init__(self):
        self.llm_service = LLMService()

    async def extract_members(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMemberDTO]:
        """Extract members using Pydantic + LangChain

        Args:
            html_content: HTMLコンテンツ
            conference_name: 会議体名

        Returns:
            抽出されたメンバー情報のリスト（ExtractedMemberDTO）
        """

        # リストを扱うためのラッパークラス
        class ExtractedMemberList(BaseModel):
            members: list[ExtractedMemberDTO] = Field(
                description="抽出された議員リスト"
            )

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
            # 注: HTMLは事前にクリーニングされているため、通常はこの制限に達しない
            max_length = 100000
            if len(html_content) > max_length:
                logger.warning(
                    f"HTML content too long ({len(html_content)} chars), "
                    f"truncating to {max_length} chars"
                )
                html_content = html_content[:max_length] + "..."

            logger.info(f"Calling Pydantic extractor for '{conference_name}'")
            result = chain.invoke(  # type: ignore
                {"html_content": html_content, "conference_name": conference_name}
            )

            # DTOリストを直接返す（型安全性向上）
            members = cast(Any, result).members
            logger.info(f"Pydantic extracted {len(members)} members")
            return members

        except Exception as e:
            logger.error(f"Error extracting members with Pydantic: {e}", exc_info=True)
            return []
