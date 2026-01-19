"""BAML-based Role-Name Mapping Service

このモジュールは、BAMLを使用して議事録の出席者情報から
役職と人名の対応マッピングを抽出します。

Clean Architecture準拠:
    - Infrastructure層に配置
    - Domain層のインターフェース（IRoleNameMappingService）を実装
    - Domain層のDTO（RoleNameMappingResultDTO）を戻り値として使用
"""

import logging

from baml_client.async_client import b

from src.application.dtos.role_name_mapping_dto import (
    RoleNameMappingDTO,
    RoleNameMappingResultDTO,
)
from src.domain.interfaces.role_name_mapping_service import IRoleNameMappingService


logger = logging.getLogger(__name__)


class BAMLRoleNameMappingService(IRoleNameMappingService):
    """BAML-based 役職-人名マッピング抽出サービス

    BAMLを使用して議事録の出席者情報から役職と人名の対応を抽出するクラス。
    IRoleNameMappingServiceインターフェースを実装します。

    特徴:
        - LLMを使用した柔軟な抽出
        - 様々な議事録フォーマットに対応
        - 信頼度スコアによる品質評価
    """

    async def extract_role_name_mapping(
        self, attendee_text: str | None
    ) -> RoleNameMappingResultDTO:
        """出席者テキストから役職-人名マッピングを抽出

        Args:
            attendee_text: 議事録の出席者情報テキスト

        Returns:
            RoleNameMappingResultDTO: 抽出された役職-人名マッピング結果

        Note:
            - テキストが空の場合は空の結果を返します
            - テキストが長すぎる場合は自動的に切り詰めます（50000文字）
            - エラー時は空の結果と低い信頼度を返します
        """
        logger.info("=== extract_role_name_mapping started ===")

        # None または空文字列のチェック（len()呼び出し前に実施）
        if attendee_text is None or not attendee_text.strip():
            logger.warning("No attendee text provided (None or empty)")
            return RoleNameMappingResultDTO(
                mappings=[],
                attendee_section_found=False,
                confidence=0.0,
            )

        logger.info(f"Attendee text length: {len(attendee_text)}")

        try:
            # テキストが長すぎる場合は切り詰める
            max_length = 50000
            original_length = len(attendee_text)
            if original_length > max_length:
                logger.warning(
                    f"Attendee text too long ({original_length} chars), "
                    f"truncating to {max_length} chars"
                )
                attendee_text = attendee_text[:max_length] + "..."

            # BAMLを呼び出し
            logger.info("Calling BAML ExtractRoleNameMapping")
            baml_result = await b.ExtractRoleNameMapping(attendee_text)

            # BAML結果をDTOに変換
            mappings = [
                RoleNameMappingDTO(
                    role=m.role,
                    name=m.name,
                    member_number=m.member_number,
                )
                for m in baml_result.mappings
            ]

            result = RoleNameMappingResultDTO(
                mappings=mappings,
                attendee_section_found=baml_result.attendee_section_found,
                confidence=baml_result.confidence,
            )

            logger.info("Role-name mapping extraction result:")
            logger.info(f"  - Mappings count: {len(result.mappings)}")
            logger.info(f"  - Attendee section found: {result.attendee_section_found}")
            logger.info(f"  - Confidence: {result.confidence}")

            if result.mappings:
                first = result.mappings[0]
                logger.debug(f"Sample mapping: {first.role} -> {first.name}")

            return result

        except Exception as e:
            logger.error(f"BAML extract_role_name_mapping failed: {e}", exc_info=True)
            return RoleNameMappingResultDTO(
                mappings=[],
                attendee_section_found=False,
                confidence=0.0,
            )
