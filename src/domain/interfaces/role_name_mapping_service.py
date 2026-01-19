"""Role-Name Mapping service interface

役職-人名マッピング抽出サービスの抽象インターフェース。
Clean Architectureの原則に従い、ドメイン層で定義されています。
"""

from abc import ABC, abstractmethod

from src.application.dtos.role_name_mapping_dto import RoleNameMappingResultDTO


class IRoleNameMappingService(ABC):
    """役職-人名マッピング抽出サービスのインターフェース

    議事録の出席者情報から役職と人名の対応を抽出する責務を持ちます。
    具体的な実装（BAML、ルールベースなど）はインフラストラクチャ層で提供されます。

    IMinutesDividerService.extract_attendees_mapping()との違い:
        - 本サービスは役職を持つ人物のみを抽出します
        - 一般出席者（役職なし）は含みません
        - 政治家マッチングで役職のみの発言者を解決するために使用されます
        - IMinutesDividerServiceは議事録分割処理の一部として、
          一般出席者リスト（regular_attendees）も含む全ての出席者を抽出します
    """

    @abstractmethod
    async def extract_role_name_mapping(
        self, attendee_text: str | None
    ) -> RoleNameMappingResultDTO:
        """出席者テキストから役職-人名マッピングを抽出

        Args:
            attendee_text: 議事録の出席者情報テキスト（Noneも許容）

        Returns:
            RoleNameMappingResultDTO: 抽出された役職-人名マッピング結果

        Note:
            - 実装は非同期で動作する必要があります
            - attendee_textがNoneまたは空の場合は空の結果を返します
            - エラー時は空のマッピングと低い信頼度を返します
        """
        pass
