"""Parliamentary group member extraction agent interface

議員団メンバー抽出エージェントの抽象インターフェース。
Clean Architectureの原則に従い、ドメイン層で定義されています。

Issue #905: [LangGraph+BAML] 議員団メンバー抽出のエージェント化
"""

from abc import ABC, abstractmethod

from src.application.dtos.parliamentary_group_member_dto import (
    ParliamentaryGroupMemberAgentResultDTO,
)


class IParliamentaryGroupMemberExtractionAgent(ABC):
    """議員団メンバー抽出エージェントのインターフェース

    HTMLコンテンツから議員団メンバー情報を抽出するエージェントの
    抽象インターフェースです。LangGraphベースの実装など、
    具体的な実装はインフラストラクチャ層で提供されます。

    依存性逆転の原則に従い、このインターフェースを使用することで、
    アプリケーション層やユースケースは具体的な実装に依存せず、
    テスト時のモック注入が容易になります。
    """

    @abstractmethod
    async def extract_members(
        self, html_content: str, parliamentary_group_name: str
    ) -> ParliamentaryGroupMemberAgentResultDTO:
        """HTMLコンテンツから議員団メンバーを抽出

        Args:
            html_content: 解析対象のHTMLコンテンツ
            parliamentary_group_name: 議員団名（抽出精度向上に使用）

        Returns:
            ParliamentaryGroupMemberAgentResultDTO:
                - members: 抽出されたメンバーのリスト
                  （ExtractedParliamentaryGroupMemberDTO）
                - success: 抽出成功フラグ
                - validation_errors: 検証エラーのリスト
                - error_message: エラーメッセージ（エラー時のみ）

        Note:
            - 実装は非同期で動作する必要があります
            - エラー時はsuccess=Falseとerror_messageを設定して返します
        """
        pass
