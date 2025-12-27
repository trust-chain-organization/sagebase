"""BAML-based Speaker Matching Service

このモジュールは、BAMLを使用して話者マッチング処理を行います。
既存のPydantic実装と並行して動作し、フィーチャーフラグで切り替え可能です。
"""

import logging
import re

from typing import Any

from pydantic import BaseModel, Field

from baml_client.async_client import b

from src.domain.exceptions import ExternalServiceException
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.interfaces.llm_service import ILLMService


logger = logging.getLogger(__name__)


class SpeakerMatch(BaseModel):
    """マッチング結果のデータモデル"""

    matched: bool = Field(description="マッチングが成功したかどうか")
    speaker_id: int | None = Field(description="マッチしたspeakerのID", default=None)
    speaker_name: str | None = Field(
        description="マッチしたspeakerの名前", default=None
    )
    confidence: float = Field(description="マッチングの信頼度 (0.0-1.0)", default=0.0)
    reason: str = Field(description="マッチング判定の理由")


class BAMLSpeakerMatchingService:
    """BAML-based 発言者名マッチングサービス

    BAMLを使用して発言者マッチング処理を行うクラス。
    既存のSpeakerMatchingServiceと同じインターフェースを持ち、
    トークン効率とパース精度の向上を目指します。
    """

    def __init__(
        self,
        llm_service: ILLMService,  # 互換性のため保持（BAML使用時は不要）
        speaker_repository: SpeakerRepository,
    ):
        """
        Initialize BAML speaker matching service

        Args:
            llm_service: 互換性のためのパラメータ（BAML使用時は不要）
            speaker_repository: Speaker repository instance (domain interface)
        """
        self.llm_service = llm_service
        self.speaker_repository = speaker_repository
        logger.info("BAMLSpeakerMatchingService initialized")

    async def find_best_match(
        self,
        speaker_name: str,
        meeting_date: str | None = None,
        conference_id: int | None = None,
    ) -> SpeakerMatch:
        """
        発言者名に最適なマッチを見つける（会議体所属を考慮）

        Args:
            speaker_name: マッチングする発言者名
            meeting_date: 会議開催日（YYYY-MM-DD形式）
            conference_id: 会議体ID

        Returns:
            SpeakerMatch: マッチング結果
        """
        # 既存の発言者リストを取得
        available_speakers = await self.speaker_repository.get_all_for_matching()

        if not available_speakers:
            return SpeakerMatch(
                matched=False, confidence=0.0, reason="利用可能な発言者リストが空です"
            )

        # 会議体所属情報を取得（利用可能な場合）
        affiliated_speakers: list[dict[str, Any]] = []
        affiliated_speaker_ids: set[int] = set()
        if meeting_date and conference_id:
            affiliated_speakers = await self.speaker_repository.get_affiliated_speakers(
                meeting_date, conference_id
            )
            affiliated_speaker_ids = {s["speaker_id"] for s in affiliated_speakers}

        # まず従来のルールベースマッチングを試行（高速パス）
        rule_based_match = self._rule_based_matching(speaker_name, available_speakers)
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            logger.info(f"Rule-based match found for '{speaker_name}'")
            return rule_based_match

        # BAMLによる高度なマッチング
        try:
            # 候補を絞り込み（パフォーマンス向上のため）
            filtered_speakers = self._filter_candidates(
                speaker_name, available_speakers, affiliated_speaker_ids
            )

            # BAML関数を呼び出し
            baml_result = await b.MatchSpeaker(
                speaker_name=speaker_name,
                available_speakers=self._format_speakers_for_llm(
                    filtered_speakers, affiliated_speaker_ids
                ),
            )

            # BAML結果をPydanticモデルに変換
            match_result = SpeakerMatch(
                matched=baml_result.matched,
                speaker_id=baml_result.speaker_id,
                speaker_name=baml_result.speaker_name,
                confidence=baml_result.confidence,
                reason=baml_result.reason,
            )

            # 信頼度が低い場合はマッチしないとして扱う
            if match_result.confidence < 0.8:
                match_result.matched = False
                match_result.speaker_id = None
                match_result.speaker_name = None

            logger.info(
                f"BAML match result for '{speaker_name}': "
                f"matched={match_result.matched}, confidence={match_result.confidence}"
            )

            return match_result

        except Exception as e:
            logger.error(f"BAML話者マッチング中のエラー: {e}")
            # Wrap errors as ExternalServiceException
            raise ExternalServiceException(
                service_name="BAML",
                operation="speaker_matching",
                reason=f"BAML speaker matching error: {str(e)}",
            ) from e

    def _rule_based_matching(
        self, speaker_name: str, available_speakers: list[dict[str, Any]]
    ) -> SpeakerMatch:
        """従来のルールベースマッチング（高速パス）"""

        # 1. 完全一致
        for speaker in available_speakers:
            if speaker["name"] == speaker_name:
                return SpeakerMatch(
                    matched=True,
                    speaker_id=speaker["id"],
                    speaker_name=speaker["name"],
                    confidence=1.0,
                    reason="完全一致",
                )

        # 2. 括弧内の名前を抽出して検索
        match = re.search(r"\(([^)]+)\)", speaker_name)
        if match:
            extracted_name = match.group(1)
            for speaker in available_speakers:
                if speaker["name"] == extracted_name:
                    return SpeakerMatch(
                        matched=True,
                        speaker_id=speaker["id"],
                        speaker_name=speaker["name"],
                        confidence=0.95,
                        reason=f"括弧内名前一致: {extracted_name}",
                    )

        # 3. 記号除去後の一致
        cleaned_name = re.sub(r"^[◆○◎]", "", speaker_name)
        if cleaned_name != speaker_name:
            return self._rule_based_matching(cleaned_name, available_speakers)

        # 4. 部分一致
        for speaker in available_speakers:
            if speaker["name"] in speaker_name or speaker_name in speaker["name"]:
                return SpeakerMatch(
                    matched=True,
                    speaker_id=speaker["id"],
                    speaker_name=speaker["name"],
                    confidence=0.8,
                    reason=f"部分一致: {speaker['name']}",
                )

        return SpeakerMatch(
            matched=False, confidence=0.0, reason="ルールベースマッチングでは一致なし"
        )

    def _filter_candidates(
        self,
        speaker_name: str,
        available_speakers: list[dict[str, Any]],
        affiliated_speaker_ids: set[int] | None = None,
        max_candidates: int = 10,
    ) -> list[dict[str, Any]]:
        """候補を絞り込む（LLMの処理効率向上のため、会議体所属を優先）"""
        candidates: list[dict[str, Any]] = []

        # 括弧内の名前を抽出
        extracted_name = None
        match = re.search(r"\(([^)]+)\)", speaker_name)
        if match:
            extracted_name = match.group(1)

        # 記号除去
        cleaned_name = re.sub(r"^[◆○◎]", "", speaker_name)

        for speaker in available_speakers:
            score = 0

            # 部分一致スコア
            if speaker["name"] in speaker_name or speaker_name in speaker["name"]:
                score += 3

            # 括弧内名前との一致
            if extracted_name and (
                speaker["name"] == extracted_name or extracted_name in speaker["name"]
            ):
                score += 5

            # 清理された名前との一致
            if speaker["name"] in cleaned_name or cleaned_name in speaker["name"]:
                score += 2

            # 文字列長の類似性
            len_diff = abs(len(speaker["name"]) - len(speaker_name))
            if len_diff <= 3:
                score += 1

            # 会議体所属ボーナス
            if affiliated_speaker_ids and speaker["id"] in affiliated_speaker_ids:
                score += 10  # 大きなボーナスを付与

            if score > 0:
                candidates.append({**speaker, "score": score})

        # スコア順にソート
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 最大候補数に制限
        return (
            candidates[:max_candidates]
            if candidates
            else available_speakers[:max_candidates]
        )

    def _format_speakers_for_llm(
        self,
        speakers: list[dict[str, Any]],
        affiliated_speaker_ids: set[int] | None = None,
    ) -> str:
        """発言者リストをLLM用にフォーマット（会議体所属情報を含む）"""
        formatted: list[str] = []
        for speaker in speakers:
            entry = f"ID: {speaker['id']}, 名前: {speaker['name']}"
            if affiliated_speaker_ids and speaker["id"] in affiliated_speaker_ids:
                entry += " ★【会議体所属議員】"
            formatted.append(entry)
        return "\n".join(formatted)
