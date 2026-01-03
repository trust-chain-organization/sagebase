"""政治家の抽出結果を表すDTO。"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PoliticianExtractionResult:
    """政治家のAI抽出結果を表すDTO。

    スクレイピング処理とマッチング処理の両方に対応。

    スクレイピング処理用のフィールド:
        name: 政治家名
        furigana: ふりがな
        political_party_id: 所属政党ID
        district: 選挙区
        profile_page_url: プロフィールページURL
        party_position: 党内役職

    マッチング処理用のフィールド:
        matched_from_speaker_id: マッチング元の発言者ID
        match_confidence: マッチングの信頼度 (0.0-1.0)
        match_reason: マッチングの理由

    共通フィールド:
        confidence_score: 抽出またはマッチングの信頼度 (0.0-1.0)
    """

    # スクレイピング処理用フィールド
    name: str | None = None
    furigana: str | None = None
    political_party_id: int | None = None
    district: str | None = None
    profile_page_url: str | None = None
    party_position: str | None = None

    # マッチング処理用フィールド
    matched_from_speaker_id: int | None = None
    match_confidence: float | None = None
    match_reason: str | None = None

    # 共通フィールド
    confidence_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Returns:
            抽出データのdict表現
        """
        return asdict(self)
