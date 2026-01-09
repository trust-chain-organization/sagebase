"""Politician matching agent interface

政治家マッチングエージェントの抽象インターフェース。
Clean Architectureの原則に従い、ドメイン層で定義されています。
"""

from abc import ABC, abstractmethod

from src.domain.dtos.politician_matching_dto import PoliticianMatchingAgentResult


class IPoliticianMatchingAgent(ABC):
    """政治家マッチングエージェントのインターフェース

    発言者と政治家のマッチング処理を行うエージェントの
    抽象インターフェースです。LangGraphベースの実装など、
    具体的な実装はインフラストラクチャ層で提供されます。

    依存性逆転の原則に従い、このインターフェースを使用することで、
    アプリケーション層やユースケースは具体的な実装に依存せず、
    テスト時のモック注入が容易になります。

    特徴:
        - ReActパターンによる反復的推論
        - ルールベースマッチング（高速パス）との統合
        - BAMLによるLLM通信の抽象化
    """

    @abstractmethod
    async def match_politician(
        self,
        speaker_name: str,
        speaker_type: str | None = None,
        speaker_party: str | None = None,
    ) -> PoliticianMatchingAgentResult:
        """発言者と政治家をマッチング

        Args:
            speaker_name: マッチングする発言者名
            speaker_type: 発言者の種別（例: "議員", "委員"など）
            speaker_party: 発言者の所属政党（もしあれば）

        Returns:
            PoliticianMatchingAgentResult:
                - matched: マッチング成功フラグ
                - politician_id: マッチした政治家のID
                - politician_name: マッチした政治家の名前
                - political_party_name: マッチした政治家の所属政党
                - confidence: マッチングの信頼度（0.0-1.0）
                - reason: マッチング判定の理由
                - error_message: エラーメッセージ（エラー時のみ）

        Note:
            - 実装は非同期で動作する必要があります
            - エラー時はmatched=Falseとerror_messageを設定して返します
            - 信頼度が0.7未満の場合はmatched=Falseとなります
        """
        pass
