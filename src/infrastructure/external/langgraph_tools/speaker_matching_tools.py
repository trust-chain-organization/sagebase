"""LangGraph tools for speaker matching (名寄せ) use cases.

This module provides LangGraph @tool wrappers for speaker-politician matching.
The tools support the name resolution agent (名寄せAgent) in performing
high-accuracy matching between speakers and politicians.

Tools:
- evaluate_matching_candidates: Evaluate and score politician candidates for a speaker
- search_additional_info: Search additional information about politicians/speakers
- judge_confidence: Judge the confidence level of a matching candidate (BAML-powered)
"""

import json
import logging

from typing import Any

from langchain_core.tools import tool

from baml_client.async_client import b

from src.domain.repositories.politician_affiliation_repository import (
    PoliticianAffiliationRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.infrastructure.di.container import get_container


logger = logging.getLogger(__name__)


def create_speaker_matching_tools(
    speaker_repo: SpeakerRepository | None = None,
    politician_repo: PoliticianRepository | None = None,
    affiliation_repo: PoliticianAffiliationRepository | None = None,
) -> list[Any]:
    """Create LangGraph tools for speaker matching.

    Args:
        speaker_repo: Optional SpeakerRepository instance.
                     If not provided, will be fetched from DI container.
        politician_repo: Optional PoliticianRepository instance.
                        If not provided, will be fetched from DI container.
        affiliation_repo: Optional PoliticianAffiliationRepository instance.
                         If not provided, will be fetched from DI container.

    Returns:
        List of LangGraph tools for speaker matching
    """
    # Fetch repositories from DI container if not provided
    if speaker_repo is None or politician_repo is None or affiliation_repo is None:
        container = get_container()
        if speaker_repo is None:
            speaker_repo = container.repositories.speaker_repository()
        if politician_repo is None:
            politician_repo = container.repositories.politician_repository()
        if affiliation_repo is None:
            affiliation_repo = (
                container.repositories.politician_affiliation_repository()
            )

    # Assert repositories are not None for type checking
    assert speaker_repo is not None, "Failed to initialize SpeakerRepository"
    assert politician_repo is not None, "Failed to initialize PoliticianRepository"
    assert affiliation_repo is not None, (
        "Failed to initialize PoliticianAffiliationRepository"
    )

    @tool
    async def evaluate_matching_candidates(
        speaker_name: str,
        meeting_date: str | None = None,
        conference_id: int | None = None,
        max_candidates: int = 10,
    ) -> dict[str, Any]:
        """Evaluate politician candidates for a speaker name.

        発言者名に対する政治家候補のリストを評価・スコアリングします。
        名前の類似度、所属の一致などを考慮して、上位候補を返します。

        Args:
            speaker_name: 発言者名（マッチング対象）
            meeting_date: 会議開催日（YYYY-MM-DD形式、オプション）
            conference_id: 会議体ID（オプション）
            max_candidates: 返す最大候補数（デフォルト: 10）

        Returns:
            Dictionary with:
            - candidates: スコア付き候補リスト
              - politician_id: 政治家ID
              - politician_name: 政治家名
              - party: 政党名
              - score: スコア（0.0-1.0）
              - match_type: マッチタイプ（"exact", "partial", "fuzzy"）
              - is_affiliated: 会議体所属かどうか
            - total_candidates: 候補総数
            - evaluation_criteria: 評価基準
              - name_similarity_weight: 名前類似度の重み
              - affiliation_weight: 所属の重み
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> result = await evaluate_matching_candidates(
            ...     speaker_name="田中太郎",
            ...     meeting_date="2024-01-15",
            ...     conference_id=1
            ... )
            >>> print(result["candidates"][0])
            {
                "politician_id": 123,
                "politician_name": "田中太郎",
                "party": "○○党",
                "score": 0.95,
                "match_type": "exact",
                "is_affiliated": True
            }
        """
        try:
            # Input validation
            if not speaker_name or not speaker_name.strip():
                return {
                    "candidates": [],
                    "total_candidates": 0,
                    "evaluation_criteria": {},
                    "error": "発言者名が空です",
                }

            speaker_name = speaker_name.strip()

            # Get all politicians for matching
            all_politicians = await politician_repo.get_all_for_matching()

            if not all_politicians:
                return {
                    "candidates": [],
                    "total_candidates": 0,
                    "evaluation_criteria": {},
                    "error": "利用可能な政治家リストが空です",
                }

            # Get affiliated speakers if meeting_date and conference_id are provided
            # (For future enhancement: use affiliated info to boost scores)
            _affiliated_speaker_ids: set[int] = set()
            if meeting_date and conference_id:
                try:
                    affiliated_speakers = await speaker_repo.get_affiliated_speakers(
                        meeting_date, conference_id
                    )
                    _affiliated_speaker_ids = {
                        s["speaker_id"] for s in affiliated_speakers
                    }
                except Exception as e:
                    logger.warning(
                        f"Failed to get affiliated speakers: {e}. "
                        f"Continuing without affiliation info."
                    )

            # Score each politician
            candidates = []
            for politician in all_politicians:
                pol_name = politician.get("name", "")
                pol_id = politician.get("id")
                pol_party = politician.get("party")

                if not pol_name or pol_id is None:
                    continue

                # Calculate name similarity score
                score, match_type = _calculate_name_similarity(speaker_name, pol_name)

                # Check if politician is affiliated with the conference
                # (This would require linking politician to speaker first,
                # so we'll skip this for now and focus on name matching)
                is_affiliated = False  # Placeholder

                # Boost score if affiliated (future enhancement)
                # if is_affiliated:
                #     score = min(1.0, score + 0.1)

                candidates.append(
                    {
                        "politician_id": pol_id,
                        "politician_name": pol_name,
                        "party": pol_party,
                        "score": score,
                        "match_type": match_type,
                        "is_affiliated": is_affiliated,
                    }
                )

            # Sort by score descending
            candidates.sort(key=lambda x: x["score"], reverse=True)

            # Return top N candidates
            top_candidates = candidates[:max_candidates]

            return {
                "candidates": top_candidates,
                "total_candidates": len(candidates),
                "evaluation_criteria": {
                    "name_similarity_weight": 1.0,
                    "affiliation_weight": 0.1,
                },
            }

        except Exception as e:
            logger.error(f"Error evaluating matching candidates: {e}", exc_info=True)
            return {
                "candidates": [],
                "total_candidates": 0,
                "evaluation_criteria": {},
                "error": str(e),
            }

    @tool
    async def search_additional_info(
        entity_type: str,
        entity_id: int,
        info_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search additional information about a politician or speaker.

        政治家または発言者に関する追加情報を検索します。
        所属情報、政党情報、発言履歴などを取得できます。

        Args:
            entity_type: エンティティタイプ（"politician" または "speaker"）
            entity_id: エンティティID
            info_types: 取得する情報タイプのリスト（オプション）
                       指定可能な値: ["affiliation", "party", "history"]
                       未指定の場合はすべて取得

        Returns:
            Dictionary with:
            - entity_type: エンティティタイプ
            - entity_id: エンティティID
            - entity_name: エンティティ名
            - info: 情報の辞書
              - affiliation: 所属情報のリスト（指定時）
                - conference_id: 会議体ID
                - conference_name: 会議体名
                - start_date: 開始日
                - end_date: 終了日
              - party: 政党情報（指定時）
                - party_id: 政党ID
                - party_name: 政党名
              - history: 履歴情報（指定時）
                - total_speeches: 総発言数（speaker のみ）
                - first_appearance: 初出現日
                - last_appearance: 最終出現日
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> result = await search_additional_info(
            ...     entity_type="politician",
            ...     entity_id=123,
            ...     info_types=["affiliation", "party"]
            ... )
            >>> print(result["info"]["party"])
            {"party_id": 1, "party_name": "○○党"}
        """
        try:
            # Input validation
            if entity_type not in ("politician", "speaker"):
                return {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "entity_name": "",
                    "info": {},
                    "error": f"無効なentity_type: {entity_type}。"
                    f"'politician' または 'speaker' を指定してください",
                }

            # Default to all info types if not specified
            if info_types is None:
                info_types = ["affiliation", "party", "history"]

            info: dict[str, Any] = {}
            entity_name = ""

            if entity_type == "politician":
                # Get politician information
                politicians = await politician_repo.get_all_for_matching()
                politician = next(
                    (p for p in politicians if p.get("id") == entity_id), None
                )

                if politician is None:
                    return {
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "entity_name": "",
                        "info": {},
                        "error": f"政治家ID {entity_id} が見つかりません",
                    }

                entity_name = politician.get("name", "")

                # Get affiliation info
                if "affiliation" in info_types:
                    try:
                        affiliations = await affiliation_repo.get_by_politician(
                            entity_id
                        )
                        info["affiliation"] = [
                            {
                                "conference_id": aff.conference_id,
                                "conference_name": getattr(aff.conference, "name", "")
                                if hasattr(aff, "conference")
                                else "",
                                "start_date": (
                                    aff.start_date.isoformat()
                                    if aff.start_date
                                    else None
                                ),
                                "end_date": (
                                    aff.end_date.isoformat() if aff.end_date else None
                                ),
                            }
                            for aff in affiliations
                        ]
                    except Exception as e:
                        logger.warning(f"Failed to get affiliation info: {e}")
                        info["affiliation"] = []

                # Get party info
                if "party" in info_types:
                    party_name = politician.get("party")
                    if party_name:
                        info["party"] = {
                            # Party ID not available from get_all_for_matching
                            "party_id": None,
                            "party_name": party_name,
                        }
                    else:
                        info["party"] = None

                # History info (placeholder for politician)
                if "history" in info_types:
                    info["history"] = {
                        "note": "政治家の履歴情報は現在サポートされていません"
                    }

            elif entity_type == "speaker":
                # Get speaker information
                speakers = await speaker_repo.get_all_for_matching()
                speaker = next((s for s in speakers if s.get("id") == entity_id), None)

                if speaker is None:
                    return {
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "entity_name": "",
                        "info": {},
                        "error": f"発言者ID {entity_id} が見つかりません",
                    }

                entity_name = speaker.get("name", "")

                # Get affiliation info (through matched politician)
                if "affiliation" in info_types:
                    politician_id = speaker.get("matched_politician_id")
                    if politician_id:
                        try:
                            affiliations = await affiliation_repo.get_by_politician(
                                politician_id
                            )
                            info["affiliation"] = [
                                {
                                    "conference_id": aff.conference_id,
                                    "conference_name": getattr(
                                        aff.conference, "name", ""
                                    )
                                    if hasattr(aff, "conference")
                                    else "",
                                    "start_date": (
                                        aff.start_date.isoformat()
                                        if aff.start_date
                                        else None
                                    ),
                                    "end_date": (
                                        aff.end_date.isoformat()
                                        if aff.end_date
                                        else None
                                    ),
                                }
                                for aff in affiliations
                            ]
                        except Exception as e:
                            logger.warning(f"Failed to get affiliation info: {e}")
                            info["affiliation"] = []
                    else:
                        info["affiliation"] = []

                # Get party info (through matched politician)
                if "party" in info_types:
                    party_name = speaker.get("party")
                    if party_name:
                        info["party"] = {
                            "party_id": None,
                            "party_name": party_name,
                        }
                    else:
                        info["party"] = None

                # History info (placeholder)
                if "history" in info_types:
                    info["history"] = {
                        "note": "発言者の履歴情報は現在サポートされていません"
                    }

            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "entity_name": entity_name,
                "info": info,
            }

        except Exception as e:
            logger.error(f"Error searching additional info: {e}", exc_info=True)
            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "entity_name": "",
                "info": {},
                "error": str(e),
            }

    @tool
    async def judge_confidence(
        speaker_name: str,
        candidate: dict[str, Any],
        additional_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Judge the confidence level of a matching candidate using BAML.

        マッチング候補の確信度をBAMLを使用して総合的に判定します。
        LLMが候補のスコア、追加情報を考慮して、最終的な確信度を計算します。

        Args:
            speaker_name: 発言者名
            candidate: 候補情報（evaluate_matching_candidatesの結果）
              - politician_id: 政治家ID
              - politician_name: 政治家名
              - party: 政党名
              - score: スコア（0.0-1.0）
              - match_type: マッチタイプ（"exact", "partial", "fuzzy"）
              - is_affiliated: 所属フラグ
            additional_info: 追加情報（search_additional_infoの結果、オプション）

        Returns:
            Dictionary with:
            - confidence: 確信度（0.0-1.0）
            - confidence_level: 確信度レベル（"HIGH", "MEDIUM", "LOW"）
            - should_match: マッチすべきかどうか（確信度0.8以上でTrue）
            - reason: 判定理由の説明
            - contributing_factors: 確信度に寄与した要素のリスト
              - factor: 要素名
              - impact: スコアへの影響
              - description: 説明
            - recommendation: 推奨アクション
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> candidate = {
            ...     "politician_id": 123,
            ...     "politician_name": "田中太郎",
            ...     "score": 0.85,
            ...     "match_type": "exact",
            ...     "is_affiliated": True
            ... }
            >>> result = await judge_confidence(
            ...     speaker_name="田中太郎",
            ...     candidate=candidate
            ... )
            >>> print(result["confidence"])
            0.95
            >>> print(result["should_match"])
            True
        """
        try:
            # Input validation
            if not speaker_name or not speaker_name.strip():
                return {
                    "confidence": 0.0,
                    "confidence_level": "LOW",
                    "should_match": False,
                    "reason": "発言者名が空です",
                    "contributing_factors": [],
                    "recommendation": "発言者名を指定してください",
                    "error": "Empty speaker name",
                }

            if not candidate or not isinstance(candidate, dict):
                return {
                    "confidence": 0.0,
                    "confidence_level": "LOW",
                    "should_match": False,
                    "reason": "候補情報が無効です",
                    "contributing_factors": [],
                    "recommendation": "有効な候補情報を提供してください",
                    "error": "Invalid candidate data",
                }

            # Convert match_type to uppercase for BAML
            if "match_type" in candidate:
                candidate["match_type"] = candidate["match_type"].upper()

            # Convert candidate and additional_info to JSON strings
            candidate_json = json.dumps(candidate, ensure_ascii=False, indent=2)
            additional_info_json = (
                json.dumps(additional_info, ensure_ascii=False, indent=2)
                if additional_info
                else None
            )

            logger.info(
                f"Calling BAML JudgeMatchingConfidence for speaker='{speaker_name}'"
            )

            # Call BAML function
            result = await b.JudgeMatchingConfidence(
                speaker_name=speaker_name,
                candidate_json=candidate_json,
                additional_info_json=additional_info_json,
            )

            # Convert BAML result to dict
            return {
                "confidence": result.confidence,
                "confidence_level": result.confidence_level.lower(),
                "should_match": result.should_match,
                "reason": result.reason,
                "contributing_factors": [
                    {
                        "factor": f.factor,
                        "impact": f.impact,
                        "description": f.description,
                    }
                    for f in result.contributing_factors
                ],
                "recommendation": result.recommendation,
            }

        except Exception as e:
            logger.error(f"Error judging confidence with BAML: {e}", exc_info=True)
            return {
                "confidence": 0.0,
                "confidence_level": "low",
                "should_match": False,
                "reason": f"確信度判定中にエラーが発生: {str(e)}",
                "contributing_factors": [],
                "recommendation": "エラーのため判定不能",
                "error": str(e),
            }

    return [evaluate_matching_candidates, search_additional_info, judge_confidence]


def _calculate_name_similarity(name1: str, name2: str) -> tuple[float, str]:
    """Calculate name similarity score.

    名前の類似度を計算します。完全一致、部分一致、ファジーマッチングを考慮します。

    Args:
        name1: 名前1
        name2: 名前2

    Returns:
        Tuple of (similarity_score, match_type)
        - similarity_score: 類似度スコア（0.0-1.0）
        - match_type: マッチタイプ（"exact", "partial", "fuzzy"）
    """
    # Normalize names (remove whitespace, convert to lowercase)
    norm_name1 = name1.strip().replace(" ", "").replace("　", "").lower()
    norm_name2 = name2.strip().replace(" ", "").replace("　", "").lower()

    # Exact match
    if norm_name1 == norm_name2:
        return (1.0, "exact")

    # Partial match (one is substring of the other)
    if norm_name1 in norm_name2 or norm_name2 in norm_name1:
        # Calculate overlap ratio
        overlap_len = min(len(norm_name1), len(norm_name2))
        max_len = max(len(norm_name1), len(norm_name2))
        score = overlap_len / max_len
        return (score, "partial")

    # Fuzzy match (simple character overlap)
    # Count common characters
    common_chars = sum(
        min(norm_name1.count(char), norm_name2.count(char)) for char in set(norm_name1)
    )
    max_len = max(len(norm_name1), len(norm_name2))

    if max_len == 0:
        return (0.0, "fuzzy")

    score = common_chars / max_len

    # Minimum score for fuzzy match
    if score < 0.3:
        score = 0.0

    return (score, "fuzzy")
