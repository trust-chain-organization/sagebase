"""議員団メンバー抽出サービスのインターフェース

議員団のWebページからメンバー情報を抽出する責務を持ちます。
具体的な実装（Pydantic, BAMLなど）はインフラストラクチャ層で提供されます。
"""

from abc import ABC, abstractmethod

from src.application.dtos.parliamentary_group_member_dto import (
    ParliamentaryGroupMemberExtractionResultDTO,
)


class IParliamentaryGroupMemberExtractorService(ABC):
    """議員団メンバー抽出サービスのインターフェース"""

    @abstractmethod
    async def extract_members(
        self, parliamentary_group_id: int, url: str
    ) -> ParliamentaryGroupMemberExtractionResultDTO:
        """議員団URLからメンバー情報を抽出する

        Args:
            parliamentary_group_id: 議員団ID
            url: 議員団メンバー一覧のURL

        Returns:
            MemberExtractionResult: 抽出結果

        Note:
            - 実装は非同期で動作する必要があります
            - エラー時はerrorフィールドにエラーメッセージを設定してください
            - HTMLの取得とLLMによる抽出を含む完全な処理を実行します
        """
        pass
