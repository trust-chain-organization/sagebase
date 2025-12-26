"""BAML-based Politician Matching Service

このモジュールは、BAMLを使用して政治家マッチング処理を行います。
既存のPydantic実装と並行して動作し、フィーチャーフラグで切り替え可能です。
"""

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from baml_client.async_client import b
from src.domain.exceptions import ExternalServiceException
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.llm_service import ILLMService


logger = logging.getLogger(__name__)


class PoliticianMatch(BaseModel):
    """政治家マッチング結果のデータモデル"""

    matched: bool = Field(description="マッチングが成功したかどうか")
    politician_id: int | None = Field(description="マッチした政治家のID", default=None)
    politician_name: str | None = Field(
        description="マッチした政治家の名前", default=None
    )
    political_party_name: str | None = Field(
        description="マッチした政治家の所属政党", default=None
    )
    confidence: float = Field(description="マッチングの信頼度 (0.0-1.0)", default=0.0)
    reason: str = Field(description="マッチング判定の理由")


class BAMLPoliticianMatchingService:
    """BAML-based 発言者-政治家マッチングサービス

    BAMLを使用して政治家マッチング処理を行うクラス。
    既存のPoliticianMatchingServiceと同じインターフェースを持ち、
    トークン効率とパース精度の向上を目指します。
    """

    def __init__(
        self,
        llm_service: ILLMService,  # 互換性のため保持（BAML使用時は不要）
        politician_repository: PoliticianRepository,
    ):
        """
        Initialize BAML politician matching service

        Args:
            llm_service: 互換性のためのパラメータ（BAML使用時は不要）
            politician_repository: Politician repository instance (domain interface)
        """
        self.llm_service = llm_service
        self.politician_repository = politician_repository
        logger.info("BAMLPoliticianMatchingService initialized")

    async def find_best_match(
        self,
        speaker_name: str,
        speaker_type: str | None = None,
        speaker_party: str | None = None,
    ) -> PoliticianMatch:
        """
        発言者に最適な政治家マッチを見つける

        Args:
            speaker_name: マッチングする発言者名
            speaker_type: 発言者の種別
            speaker_party: 発言者の所属政党（もしあれば）

        Returns:
            PoliticianMatch: マッチング結果
        """
        # 既存の政治家リストを取得
        available_politicians = await self.politician_repository.get_all_for_matching()

        if not available_politicians:
            return PoliticianMatch(
                matched=False, confidence=0.0, reason="利用可能な政治家リストが空です"
            )

        # まず従来のルールベースマッチングを試行（高速パス）
        rule_based_match = self._rule_based_matching(
            speaker_name, speaker_party, available_politicians
        )
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            logger.info(f"Rule-based match found for '{speaker_name}'")
            return rule_based_match

        # BAMLによる高度なマッチング
        try:
            # 候補を絞り込み（パフォーマンス向上のため）
            filtered_politicians = self._filter_candidates(
                speaker_name, speaker_party, available_politicians
            )

            # BAML関数を呼び出し
            baml_result = await b.MatchPolitician(
                speaker_name=speaker_name,
                speaker_type=speaker_type or "不明",
                speaker_party=speaker_party or "不明",
                available_politicians=self._format_politicians_for_llm(
                    filtered_politicians
                ),
            )

            # BAML結果をPydanticモデルに変換
            match_result = PoliticianMatch(
                matched=baml_result.matched,
                politician_id=baml_result.politician_id,
                politician_name=baml_result.politician_name,
                political_party_name=baml_result.political_party_name,
                confidence=baml_result.confidence,
                reason=baml_result.reason,
            )

            # 信頼度が低い場合はマッチしないとして扱う
            if match_result.confidence < 0.7:
                match_result.matched = False
                match_result.politician_id = None
                match_result.politician_name = None
                match_result.political_party_name = None

            logger.info(
                f"BAML match result for '{speaker_name}': "
                f"matched={match_result.matched}, confidence={match_result.confidence}"
            )

            return match_result

        except Exception as e:
            logger.error(f"BAML政治家マッチング中のエラー: {e}")
            # Wrap errors as ExternalServiceException
            raise ExternalServiceException(
                service_name="BAML",
                operation="politician_matching",
                reason=f"BAML politician matching error: {str(e)}",
            ) from e

    def _rule_based_matching(
        self,
        speaker_name: str,
        speaker_party: str | None,
        available_politicians: list[dict[str, Any]],
    ) -> PoliticianMatch:
        """従来のルールベースマッチング（高速パス）"""

        # 1. 完全一致（名前と政党）
        if speaker_party:
            for politician in available_politicians:
                if (
                    politician["name"] == speaker_name
                    and politician["party_name"] == speaker_party
                ):
                    return PoliticianMatch(
                        matched=True,
                        politician_id=politician["id"],
                        politician_name=politician["name"],
                        political_party_name=politician["party_name"],
                        confidence=1.0,
                        reason="名前と政党が完全一致",
                    )

        # 2. 名前のみ完全一致
        exact_matches = [p for p in available_politicians if p["name"] == speaker_name]
        if len(exact_matches) == 1:
            politician = exact_matches[0]
            return PoliticianMatch(
                matched=True,
                politician_id=politician["id"],
                politician_name=politician["name"],
                political_party_name=politician["party_name"],
                confidence=0.9,
                reason="名前が完全一致（唯一の候補）",
            )

        # 3. 敬称を除去して検索
        cleaned_name = re.sub(r"(議員|氏|さん|様|先生)$", "", speaker_name)
        if cleaned_name != speaker_name:
            for politician in available_politicians:
                if politician["name"] == cleaned_name:
                    return PoliticianMatch(
                        matched=True,
                        politician_id=politician["id"],
                        politician_name=politician["name"],
                        political_party_name=politician["party_name"],
                        confidence=0.85,
                        reason=f"敬称除去後に一致: {speaker_name} → {cleaned_name}",
                    )

        return PoliticianMatch(
            matched=False, confidence=0.0, reason="ルールベースマッチングでは一致なし"
        )

    def _filter_candidates(
        self,
        speaker_name: str,
        speaker_party: str | None,
        available_politicians: list[dict[str, Any]],
        max_candidates: int = 20,
    ) -> list[dict[str, Any]]:
        """候補を絞り込む（LLMの処理効率向上のため）"""
        candidates: list[dict[str, Any]] = []

        # 敬称を除去
        cleaned_name = re.sub(r"(議員|氏|さん|様|先生)$", "", speaker_name)

        for politician in available_politicians:
            score = 0

            # 完全一致
            if politician["name"] == speaker_name:
                score += 10

            # 敬称除去後の一致
            if politician["name"] == cleaned_name:
                score += 8

            # 部分一致
            if politician["name"] in speaker_name or speaker_name in politician["name"]:
                score += 5

            # 政党一致
            if speaker_party and politician["party_name"] == speaker_party:
                score += 3

            # 姓または名の一致（スペースで分割）
            speaker_parts = speaker_name.split()
            politician_parts = politician["name"].split()
            for sp in speaker_parts:
                if sp in politician_parts:
                    score += 2

            # 文字列長の類似性
            len_diff = abs(len(politician["name"]) - len(speaker_name))
            if len_diff <= 2:
                score += 1

            if score > 0:
                candidates.append({**politician, "score": score})

        # スコア順にソート
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 最大候補数に制限
        return candidates[:max_candidates]

    def _format_politicians_for_llm(self, politicians: list[dict[str, Any]]) -> str:
        """政治家リストをLLM用にフォーマット"""
        formatted: list[str] = []
        for p in politicians:
            info = f"ID: {p['id']}, 名前: {p['name']}"
            if p.get("party_name"):
                info += f", 政党: {p['party_name']}"
            if p.get("position"):
                info += f", 役職: {p['position']}"
            if p.get("prefecture"):
                info += f", 都道府県: {p['prefecture']}"
            if p.get("electoral_district"):
                info += f", 選挙区: {p['electoral_district']}"
            formatted.append(info)
        return "\n".join(formatted)
