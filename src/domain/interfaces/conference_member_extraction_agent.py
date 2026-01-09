"""Conference member extraction agent interface

会議体メンバー抽出エージェントの抽象インターフェース。
Clean Architectureの原則に従い、ドメイン層で定義されています。
"""

from abc import ABC, abstractmethod

from src.domain.dtos.conference_member_dto import ConferenceMemberExtractionResult


class IConferenceMemberExtractionAgent(ABC):
    """会議体メンバー抽出エージェントのインターフェース

    HTMLコンテンツから会議体メンバー情報を抽出するエージェントの
    抽象インターフェースです。LangGraphベースの実装など、
    具体的な実装はインフラストラクチャ層で提供されます。

    依存性逆転の原則に従い、このインターフェースを使用することで、
    アプリケーション層やユースケースは具体的な実装に依存せず、
    テスト時のモック注入が容易になります。
    """

    @abstractmethod
    async def extract_members(
        self, html_content: str, conference_name: str
    ) -> ConferenceMemberExtractionResult:
        """HTMLコンテンツから会議体メンバーを抽出

        Args:
            html_content: 解析対象のHTMLコンテンツ
            conference_name: 会議体名（抽出精度向上に使用）

        Returns:
            ConferenceMemberExtractionResult:
                - members: 抽出されたメンバーのリスト（ExtractedMemberDTO）
                - success: 抽出成功フラグ
                - validation_errors: 検証エラーのリスト
                - error_message: エラーメッセージ（エラー時のみ）

        Note:
            - 実装は非同期で動作する必要があります
            - エラー時はsuccess=Falseとerror_messageを設定して返します
        """
        pass
