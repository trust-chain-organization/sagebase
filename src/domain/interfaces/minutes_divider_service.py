"""議事録分割サービスのインターフェース

議事録を意味のある単位に分割し、発言者と発言内容を抽出する責務を持ちます。
具体的な実装（Pydantic, BAMLなど）はインフラストラクチャ層で提供されます。
"""

from abc import ABC, abstractmethod

from src.minutes_divide_processor.models import (
    AttendeesMapping,
    MinutesBoundary,
    SectionInfoList,
    SectionString,
    SpeakerAndSpeechContentList,
)


class IMinutesDividerService(ABC):
    """議事録分割サービスのインターフェース"""

    @abstractmethod
    def pre_process(self, original_minutes: str) -> str:
        """議事録の前処理を行う

        Args:
            original_minutes: 元の議事録テキスト

        Returns:
            str: 前処理済みの議事録テキスト
        """
        pass

    @abstractmethod
    def section_divide_run(self, minutes: str) -> SectionInfoList:
        """議事録を章に分割してキーワードリストを返す

        Args:
            minutes: 議事録テキスト

        Returns:
            SectionInfoList: 分割されたセクション情報のリスト
        """
        pass

    @abstractmethod
    def detect_attendee_boundary(self, minutes_text: str) -> MinutesBoundary:
        """議事録テキストから出席者情報と発言部分の境界を検出する

        Args:
            minutes_text: 議事録の全文

        Returns:
            MinutesBoundary: 境界検出結果
        """
        pass

    @abstractmethod
    def extract_attendees_mapping(self, attendees_text: str) -> AttendeesMapping:
        """出席者情報から役職と人名のマッピングを抽出する

        Args:
            attendees_text: 出席者情報のテキスト

        Returns:
            AttendeesMapping: 役職と人名のマッピング
        """
        pass

    @abstractmethod
    def speech_divide_run(
        self, section_string: SectionString
    ) -> SpeakerAndSpeechContentList:
        """セクションから発言者と発言内容を抽出する

        Args:
            section_string: セクション情報

        Returns:
            SpeakerAndSpeechContentList: 発言者と発言内容のリスト
        """
        pass
