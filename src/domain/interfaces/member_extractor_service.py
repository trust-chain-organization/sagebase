"""Member extractor service interface

会議体メンバー抽出サービスの抽象インターフェース。
Clean Architectureの原則に従い、ドメイン層で定義されています。
"""

from abc import ABC, abstractmethod

from src.application.dtos.conference_member_extraction_dto import ExtractedMemberDTO


class IMemberExtractorService(ABC):
    """会議体メンバー抽出サービスのインターフェース

    HTMLコンテンツから会議体メンバー情報を抽出する責務を持ちます。
    具体的な実装（Pydantic, BAMLなど）はインフラストラクチャ層で提供されます。
    """

    @abstractmethod
    async def extract_members(
        self, html_content: str, conference_name: str
    ) -> list[ExtractedMemberDTO]:
        """HTMLコンテンツからメンバー情報を抽出

        Args:
            html_content: 解析対象のHTMLコンテンツ
            conference_name: 会議体名（抽出の精度向上に使用）

        Returns:
            抽出されたメンバー情報のリスト（ExtractedMemberDTO）

        Note:
            - 実装は非同期で動作する必要があります
            - エラー時は空リストを返すか、適切な例外を投げてください
        """
        pass
