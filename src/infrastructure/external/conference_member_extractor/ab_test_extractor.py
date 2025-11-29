"""A/B test member extractor

PydanticとBAMLの両実装を実行して比較するextractor。
"""

import logging

from src.domain.dtos.conference_member_dto import ExtractedMemberDTO
from src.domain.interfaces.member_extractor_service import IMemberExtractorService
from src.infrastructure.external.conference_member_extractor.baml_extractor import (
    BAMLMemberExtractor,
)
from src.infrastructure.external.conference_member_extractor.pydantic_extractor import (
    PydanticMemberExtractor,
)

logger = logging.getLogger(__name__)


class ABTestMemberExtractor(IMemberExtractorService):
    """A/B test member extractor

    PydanticとBAMLの両実装を実行し、結果を比較してログに記録します。
    デフォルトではPydanticの結果を返します（安全側）。
    """

    def __init__(self):
        self.pydantic_extractor = PydanticMemberExtractor()
        self.baml_extractor = BAMLMemberExtractor()

    async def extract_members(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMemberDTO]:
        """両実装を実行して比較（エラーハンドリング付き）

        Args:
            html_content: HTMLコンテンツ
            conference_name: 会議体名

        Returns:
            抽出されたメンバー情報のリスト（ExtractedMemberDTO）
            優先順位: Pydantic > BAML

        Note:
            両方の実装が失敗した場合は空リストを返します。
            片方が失敗した場合は成功した方の結果を返します。
        """
        logger.info("=== A/B Test Mode Enabled ===")

        # Pydantic実装
        pydantic_result: list[ExtractedMemberDTO] = []
        pydantic_error: Exception | None = None
        try:
            logger.info("Executing Pydantic implementation...")
            pydantic_result = await self.pydantic_extractor.extract_members(
                html_content, conference_name
            )
        except Exception as e:
            logger.error(f"Pydantic implementation failed: {e}", exc_info=True)
            pydantic_error = e

        # BAML実装
        baml_result: list[ExtractedMemberDTO] = []
        baml_error: Exception | None = None
        try:
            logger.info("Executing BAML implementation...")
            baml_result = await self.baml_extractor.extract_members(
                html_content, conference_name
            )
        except Exception as e:
            logger.error(f"BAML implementation failed: {e}", exc_info=True)
            baml_error = e

        # 比較ログ
        logger.info("=== Comparison Results ===")
        logger.info(
            f"Pydantic: {len(pydantic_result)} members "
            f"(error: {pydantic_error is not None})"
        )
        logger.info(
            f"BAML: {len(baml_result)} members (error: {baml_error is not None})"
        )

        # エラー処理
        if pydantic_error and baml_error:
            logger.error("Both implementations failed!")
            return []  # 両方失敗したら空リスト

        # 詳細な差分記録（少なくとも片方が成功している場合）
        if pydantic_result or baml_result:
            self._log_comparison_details(pydantic_result, baml_result)

        # 優先順位: Pydantic > BAML（安全側）
        if pydantic_result:
            logger.info("Returning Pydantic results (default in A/B test mode)")
            return pydantic_result
        else:
            logger.warning("Pydantic failed, falling back to BAML results")
            return baml_result

    def _log_comparison_details(
        self,
        pydantic_result: list[ExtractedMemberDTO],
        baml_result: list[ExtractedMemberDTO],
    ) -> None:
        """比較の詳細をログに記録（エラーセーフ）

        Args:
            pydantic_result: Pydantic実装の結果
            baml_result: BAML実装の結果
        """
        try:
            # DTOから名前を安全に抽出
            pydantic_names = [m.name for m in pydantic_result]
            baml_names = [m.name for m in baml_result]

            logger.info("Pydantic names: " + ", ".join(pydantic_names))
            logger.info("BAML names: " + ", ".join(baml_names))

            # 名前の差分を検出
            pydantic_name_set = set(pydantic_names)
            baml_name_set = set(baml_names)

            only_in_pydantic = pydantic_name_set - baml_name_set
            only_in_baml = baml_name_set - pydantic_name_set

            if only_in_pydantic:
                logger.info(f"Only in Pydantic: {only_in_pydantic}")
            if only_in_baml:
                logger.info(f"Only in BAML: {only_in_baml}")

            # TODO: トークン数、レイテンシなどのメトリクスを追加

        except Exception as e:
            logger.error(f"Failed to log comparison details: {e}", exc_info=True)
            # ログ失敗でもA/Bテストは続行
