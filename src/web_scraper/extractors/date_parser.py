"""Japanese date parsing utilities"""

import logging
import re
from datetime import datetime
from re import Pattern


class DateParser:
    """日本語の日付解析ユーティリティ"""

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

        # 日付パターンのコンパイル
        self._patterns = self._compile_patterns()

    def _compile_patterns(self) -> list[Pattern[str]]:
        """日付パターンをコンパイル"""
        patterns = [
            # 令和6年12月20日
            re.compile(r"令和(\d+)年(\d+)月(\d+)日"),
            # 平成31年4月1日
            re.compile(r"平成(\d+)年(\d+)月(\d+)日"),
            # 2024年12月20日
            re.compile(r"(\d{4})年(\d+)月(\d+)日"),
            # 令和６年１２月２０日（全角数字）
            re.compile(r"令和([０-９]+)年([０-９]+)月([０-９]+)日"),
            # 平成３１年４月１日（全角数字）
            re.compile(r"平成([０-９]+)年([０-９]+)月([０-９]+)日"),
            # ２０２４年１２月２０日（全角数字）
            re.compile(r"([０-９]{4})年([０-９]+)月([０-９]+)日"),
        ]
        return patterns

    def parse(self, date_str: str) -> datetime | None:
        """日本語の日付文字列をパース

        Args:
            date_str: 日付文字列

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None

        # 全角数字を半角に変換
        date_str = self._normalize_numbers(date_str)

        # 令和パターン
        match = self._patterns[0].search(date_str)
        if match:
            reiwa_year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            year = 2018 + reiwa_year  # 令和元年 = 2019
            return self._create_datetime(year, month, day)

        # 平成パターン
        match = self._patterns[1].search(date_str)
        if match:
            heisei_year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            year = 1988 + heisei_year  # 平成元年 = 1989
            return self._create_datetime(year, month, day)

        # 西暦パターン
        match = self._patterns[2].search(date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return self._create_datetime(year, month, day)

        # ISO形式の日付も試す
        try:
            return datetime.fromisoformat(date_str.strip())
        except (ValueError, AttributeError):
            pass

        self.logger.debug(f"Failed to parse date: {date_str}")
        return None

    def _normalize_numbers(self, text: str) -> str:
        """全角数字を半角に変換"""
        # 全角から半角への変換テーブル
        zen_to_han = str.maketrans("０１２３４５６７８９", "0123456789")
        return text.translate(zen_to_han)

    def _create_datetime(self, year: int, month: int, day: int) -> datetime | None:
        """datetime オブジェクトを作成"""
        try:
            return datetime(year, month, day)
        except ValueError as e:
            self.logger.warning(
                f"Invalid date: year={year}, month={month}, day={day}. Error: {e}"
            )
            return None

    def extract_from_text(self, text: str) -> datetime | None:
        """テキストから最初に見つかった日付を抽出

        Args:
            text: 検索対象のテキスト

        Returns:
            最初に見つかった日付 or None
        """
        # 全ての日付パターンを探す
        for pattern in self._patterns[:6]:  # 正規化前のパターンも含む
            match = pattern.search(text)
            if match:
                date_str = match.group(0)
                parsed_date = self.parse(date_str)
                if parsed_date:
                    return parsed_date

        return None

    def extract_all_from_text(self, text: str) -> list[datetime]:
        """テキストから全ての日付を抽出

        Args:
            text: 検索対象のテキスト

        Returns:
            見つかった日付のリスト
        """
        dates: list[datetime] = []

        for pattern in self._patterns[:6]:
            for match in pattern.finditer(text):
                date_str = match.group(0)
                parsed_date = self.parse(date_str)
                if parsed_date and parsed_date not in dates:
                    dates.append(parsed_date)

        # 日付順にソート
        return sorted(dates)
