"""政治家マッチングサービスのインターフェース定義

このモジュールは、政治家マッチングサービスの抽象化層を提供します。
Domain層に配置され、Infrastructure層の実装から実装されます。
"""

from typing import Protocol

from src.domain.value_objects.politician_match import PoliticianMatch


class IPoliticianMatchingService(Protocol):
    """政治家マッチングサービスのインターフェース

    発言者と政治家のマッチング処理を行うサービスの抽象化。
    Infrastructure層で具体的な実装（BAMLベース等）が提供されます。

    実装クラス:
        - BAMLPoliticianMatchingService: BAMLを使用した実装
    """

    async def find_best_match(
        self,
        speaker_name: str,
        speaker_type: str | None = None,
        speaker_party: str | None = None,
    ) -> PoliticianMatch:
        """発言者に最適な政治家マッチを見つける

        ルールベースマッチング（高速パス）とLLMマッチングのハイブリッドアプローチで
        発言者と政治家のマッチングを行います。

        Args:
            speaker_name: マッチングする発言者名
            speaker_type: 発言者の種別（例: "議員", "委員"など）
            speaker_party: 発言者の所属政党（もしあれば）

        Returns:
            PoliticianMatch: マッチング結果
                （マッチの有無、政治家情報、信頼度、理由を含む）
        """
        ...
