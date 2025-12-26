"""Base scraper class for council minutes extraction"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from .extractors import DateParser
from .models import MinutesData, SpeakerData


class BaseScraper(ABC):
    """議事録スクレーパーの基底クラス"""

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.date_parser = DateParser(logger=self.logger)

    @abstractmethod
    async def fetch_minutes(self, url: str) -> MinutesData | None:
        """指定されたURLから議事録を取得"""
        pass

    @abstractmethod
    async def extract_minutes_text(self, html_content: str) -> str:
        """HTMLから議事録テキストを抽出"""
        pass

    @abstractmethod
    async def extract_speakers(self, html_content: str) -> list[SpeakerData]:
        """HTMLから発言者情報を抽出"""
        pass

    def parse_japanese_date(self, date_str: str) -> datetime | None:
        """日本語の日付文字列をパース"""
        return self.date_parser.parse(date_str)
