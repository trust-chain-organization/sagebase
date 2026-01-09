"""LangGraph tools for politician matching.

政治家マッチングエージェント用のLangGraphツール。
ReActパターンによる反復的推論を支援するツールを提供します。
"""

import json
import logging
import re

from typing import Any

from langchain_core.tools import tool

from baml_client.async_client import b

from src.domain.repositories.politician_affiliation_repository import (
    PoliticianAffiliationRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository


logger = logging.getLogger(__name__)

# 類似度計算用の定数
PARTIAL_MATCH_SCORE = 0.8
FUZZY_NAME_MATCH_SCORE = 0.6
FUZZY_SIMILARITY_THRESHOLD = 0.5
FUZZY_SCORE_FACTOR = 0.5
PARTY_MATCH_BOOST = 0.15
CONFIDENCE_THRESHOLD = 0.7


def _calculate_name_similarity(
    speaker_name: str, politician_name: str
) -> tuple[float, str]:
    """名前の類似度を計算

    Args:
        speaker_name: 発言者名
        politician_name: 政治家名

    Returns:
        (score, match_type) のタプル
        - score: 類似度スコア（0.0-1.0）
        - match_type: マッチタイプ（"exact", "partial", "fuzzy", "none"）
    """
    # 敬称を除去して正規化
    cleaned_speaker = re.sub(r"(議員|氏|さん|様|先生)$", "", speaker_name.strip())
    cleaned_politician = politician_name.strip()

    # 完全一致
    if cleaned_speaker == cleaned_politician:
        return 1.0, "exact"

    # 部分一致（発言者名が政治家名を含む、または逆）
    if cleaned_speaker in cleaned_politician or cleaned_politician in cleaned_speaker:
        return PARTIAL_MATCH_SCORE, "partial"

    # 姓または名の一致
    speaker_parts = cleaned_speaker.split()
    politician_parts = cleaned_politician.split()
    if any(sp in politician_parts for sp in speaker_parts if len(sp) >= 2):
        return FUZZY_NAME_MATCH_SCORE, "fuzzy"

    # レーベンシュタイン距離ベースのあいまいマッチ
    if len(cleaned_speaker) > 0 and len(cleaned_politician) > 0:
        common_chars = set(cleaned_speaker) & set(cleaned_politician)
        similarity = len(common_chars) / max(
            len(cleaned_speaker), len(cleaned_politician)
        )
        if similarity > FUZZY_SIMILARITY_THRESHOLD:
            return similarity * FUZZY_SCORE_FACTOR, "fuzzy"

    return 0.0, "none"


def create_politician_matching_tools(
    politician_repo: PoliticianRepository,
    affiliation_repo: PoliticianAffiliationRepository,
) -> list[Any]:
    """政治家マッチング用のLangGraphツールを作成

    Args:
        politician_repo: PoliticianRepository（必須）
        affiliation_repo: PoliticianAffiliationRepository（必須）

    Returns:
        政治家マッチング用のLangGraphツールリスト

    Raises:
        ValueError: リポジトリがNoneの場合
    """
    if politician_repo is None:
        raise ValueError("politician_repo is required")
    if affiliation_repo is None:
        raise ValueError("affiliation_repo is required")

    @tool
    async def search_politician_candidates(
        speaker_name: str,
        speaker_party: str | None = None,
        max_candidates: int = 20,
    ) -> dict[str, Any]:
        """発言者名から政治家候補を検索・スコアリング

        発言者名に対する政治家候補のリストを評価・スコアリングします。
        名前の類似度、政党の一致などを考慮して、上位候補を返します。

        Args:
            speaker_name: 発言者名（マッチング対象）
            speaker_party: 発言者の所属政党（オプション）
            max_candidates: 返す最大候補数（デフォルト: 20）

        Returns:
            Dictionary with:
            - candidates: スコア付き候補リスト
              - politician_id: 政治家ID
              - politician_name: 政治家名
              - party_name: 政党名
              - score: スコア（0.0-1.0）
              - match_type: マッチタイプ（"exact", "partial", "fuzzy", "none"）
            - total_candidates: 候補総数
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> result = await search_politician_candidates(
            ...     speaker_name="田中太郎",
            ...     speaker_party="○○党"
            ... )
            >>> print(result["candidates"][0])
            {
                "politician_id": 123,
                "politician_name": "田中太郎",
                "party_name": "○○党",
                "score": 0.95,
                "match_type": "exact"
            }
        """
        try:
            if not speaker_name or not speaker_name.strip():
                return {
                    "candidates": [],
                    "total_candidates": 0,
                    "error": "発言者名が空です",
                }

            speaker_name = speaker_name.strip()

            # 政治家一覧を取得
            all_politicians = await politician_repo.get_all_for_matching()

            if not all_politicians:
                return {
                    "candidates": [],
                    "total_candidates": 0,
                    "error": "利用可能な政治家リストが空です",
                }

            # 各政治家をスコアリング
            candidates: list[dict[str, Any]] = []
            for politician in all_politicians:
                pol_name = politician.get("name", "")
                pol_id = politician.get("id")
                pol_party = politician.get("party_name")

                if not pol_name or pol_id is None:
                    continue

                # 名前類似度を計算
                score, match_type = _calculate_name_similarity(speaker_name, pol_name)

                # 政党一致でスコアをブースト
                if speaker_party and pol_party and speaker_party == pol_party:
                    score = min(1.0, score + PARTY_MATCH_BOOST)

                if score > 0:
                    candidates.append(
                        {
                            "politician_id": pol_id,
                            "politician_name": pol_name,
                            "party_name": pol_party,
                            "score": score,
                            "match_type": match_type,
                        }
                    )

            # スコア順にソート
            candidates.sort(key=lambda x: x["score"], reverse=True)

            # 上位候補を返す
            top_candidates = candidates[:max_candidates]

            return {
                "candidates": top_candidates,
                "total_candidates": len(candidates),
            }

        except Exception as e:
            logger.error(f"Error searching politician candidates: {e}", exc_info=True)
            return {
                "candidates": [],
                "total_candidates": 0,
                "error": str(e),
            }

    @tool
    async def verify_politician_affiliation(
        politician_id: int,
        expected_party: str | None = None,
    ) -> dict[str, Any]:
        """政治家の所属情報を検証

        政治家の所属会議体や政党情報を取得し、検証します。
        期待される政党と一致するかどうかも確認できます。

        Args:
            politician_id: 検証する政治家のID
            expected_party: 期待される所属政党（オプション）

        Returns:
            Dictionary with:
            - politician_id: 政治家ID
            - politician_name: 政治家名
            - current_party: 現在の所属政党
            - party_matches: 期待政党と一致するか（expected_party指定時）
            - affiliations: 所属会議体のリスト
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> result = await verify_politician_affiliation(
            ...     politician_id=123,
            ...     expected_party="○○党"
            ... )
            >>> print(result["party_matches"])
            True
        """
        try:
            # 政治家情報を取得
            politicians = await politician_repo.get_all_for_matching()
            politician = next(
                (p for p in politicians if p.get("id") == politician_id), None
            )

            if politician is None:
                return {
                    "politician_id": politician_id,
                    "politician_name": None,
                    "current_party": None,
                    "party_matches": False,
                    "affiliations": [],
                    "error": f"政治家ID {politician_id} が見つかりません",
                }

            current_party = politician.get("party_name")

            # 所属情報を取得
            affiliations = []
            try:
                affiliation_list = await affiliation_repo.get_by_politician(
                    politician_id
                )
                affiliations = [
                    {
                        "conference_id": aff.conference_id,
                        "start_date": (
                            aff.start_date.isoformat() if aff.start_date else None
                        ),
                        "end_date": aff.end_date.isoformat() if aff.end_date else None,
                    }
                    for aff in affiliation_list
                ]
            except Exception as e:
                logger.warning(f"Failed to get affiliation info: {e}")

            # 政党一致確認
            party_matches = None
            if expected_party is not None:
                party_matches = current_party == expected_party

            return {
                "politician_id": politician_id,
                "politician_name": politician.get("name"),
                "current_party": current_party,
                "party_matches": party_matches,
                "affiliations": affiliations,
            }

        except Exception as e:
            logger.error(f"Error verifying politician affiliation: {e}", exc_info=True)
            return {
                "politician_id": politician_id,
                "politician_name": None,
                "current_party": None,
                "party_matches": False,
                "affiliations": [],
                "error": str(e),
            }

    @tool
    async def match_politician_with_baml(
        speaker_name: str,
        speaker_type: str,
        speaker_party: str,
        candidates_json: str,
    ) -> dict[str, Any]:
        """BAMLを使用して政治家マッチングを実行

        候補リストからBAML（LLM）を使用して最適な政治家を選択します。
        高度な推論が必要な曖昧なケースで使用します。

        Args:
            speaker_name: 発言者名
            speaker_type: 発言者の種別（例: "議員", "委員"）
            speaker_party: 発言者の所属政党
            candidates_json: 候補政治家のJSON文字列

        Returns:
            Dictionary with:
            - matched: マッチング成功フラグ
            - politician_id: マッチした政治家ID
            - politician_name: マッチした政治家名
            - political_party_name: マッチした政治家の所属政党
            - confidence: マッチングの信頼度（0.0-1.0）
            - reason: マッチング判定の理由
            - error: エラーメッセージ（エラー時のみ）

        Example:
            >>> candidates = '[{"id": 1, "name": "田中太郎", "party_name": "○○党"}]'
            >>> result = await match_politician_with_baml(
            ...     speaker_name="田中太郎",
            ...     speaker_type="議員",
            ...     speaker_party="○○党",
            ...     candidates_json=candidates
            ... )
            >>> print(result["matched"])
            True
        """
        try:
            # 候補をフォーマット
            candidates = json.loads(candidates_json)
            formatted_politicians = []
            for p in candidates:
                pol_id = p.get("politician_id", p.get("id"))
                pol_name = p.get("politician_name", p.get("name"))
                info = f"ID: {pol_id}, 名前: {pol_name}"
                if p.get("party_name"):
                    info += f", 政党: {p['party_name']}"
                formatted_politicians.append(info)
            available_politicians = "\n".join(formatted_politicians)

            # BAML呼び出し
            logger.info(f"Calling BAML MatchPolitician for speaker='{speaker_name}'")
            baml_result = await b.MatchPolitician(
                speaker_name=speaker_name,
                speaker_type=speaker_type or "不明",
                speaker_party=speaker_party or "不明",
                available_politicians=available_politicians,
            )

            # 信頼度が低い場合はマッチなしとして扱う
            is_confident = baml_result.confidence >= CONFIDENCE_THRESHOLD
            matched = baml_result.matched and is_confident

            return {
                "matched": matched,
                "politician_id": baml_result.politician_id if matched else None,
                "politician_name": baml_result.politician_name if matched else None,
                "political_party_name": (
                    baml_result.political_party_name if matched else None
                ),
                "confidence": baml_result.confidence,
                "reason": baml_result.reason,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in candidates_json: {e}")
            return {
                "matched": False,
                "politician_id": None,
                "politician_name": None,
                "political_party_name": None,
                "confidence": 0.0,
                "reason": f"候補データのJSONパースエラー: {str(e)}",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error in BAML politician matching: {e}", exc_info=True)
            return {
                "matched": False,
                "politician_id": None,
                "politician_name": None,
                "political_party_name": None,
                "confidence": 0.0,
                "reason": f"マッチング中にエラーが発生: {str(e)}",
                "error": str(e),
            }

    return [
        search_politician_candidates,
        verify_politician_affiliation,
        match_politician_with_baml,
    ]
