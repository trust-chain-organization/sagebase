"""BAML-based Politician Matching Service

このモジュールは、BAMLを使用して政治家マッチング処理を行います。
Infrastructure層に配置され、Domain層のIPoliticianMatchingServiceインターフェースを実装します。

Clean Architecture準拠:
    - Infrastructure層に配置
    - Domain層のインターフェース（IPoliticianMatchingService）を実装
    - Domain層のValue Object（PoliticianMatch）を戻り値として使用
"""

import logging
import re

from typing import Any

from baml_py.errors import BamlValidationError

from baml_client.async_client import b

from src.domain.exceptions import ExternalServiceException
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.value_objects.politician_match import PoliticianMatch


logger = logging.getLogger(__name__)


class BAMLPoliticianMatchingService:
    """BAML-based 発言者-政治家マッチングサービス

    BAMLを使用して政治家マッチング処理を行うクラス。
    IPoliticianMatchingServiceインターフェースを実装します。

    特徴:
        - ルールベースマッチング（高速パス）とBAMLマッチングのハイブリッド
        - トークン効率とパース精度の向上
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
        logger.info("BAMLPoliticianMatchingService 初期化完了")

    # 役職のみの発言者名パターン（個人を特定できないためマッチ対象外）
    # frozensetで不変性を明示
    TITLE_ONLY_PATTERNS: frozenset[str] = frozenset(
        {
            "委員長",
            "副委員長",
            "議長",
            "副議長",
            "事務局長",
            "事務局次長",
            "参考人",
            "証人",
            "説明員",
            "政府委員",
            "幹事",
            "書記",
        }
    )

    def _is_title_only_speaker(self, speaker_name: str) -> bool:
        """役職のみの発言者名かどうかを判定する。

        Args:
            speaker_name: 発言者名

        Returns:
            bool: 役職のみの場合はTrue
        """
        cleaned = speaker_name.strip()
        return cleaned in self.TITLE_ONLY_PATTERNS

    async def find_best_match(
        self,
        speaker_name: str,
        speaker_type: str | None = None,
        speaker_party: str | None = None,
        role_name_mappings: dict[str, str] | None = None,
    ) -> PoliticianMatch:
        """
        発言者に最適な政治家マッチを見つける

        Args:
            speaker_name: マッチングする発言者名
            speaker_type: 発言者の種別
            speaker_party: 発言者の所属政党（もしあれば）
            role_name_mappings: 役職-人名マッピング辞書（例: {"議長": "伊藤条一"}）
                役職のみの発言者名を実名に解決するために使用

        Returns:
            PoliticianMatch: マッチング結果
        """
        # 役職のみの発言者の場合、マッピングから実名解決を試みる
        resolved_name = speaker_name
        if self._is_title_only_speaker(speaker_name):
            if role_name_mappings and speaker_name in role_name_mappings:
                resolved_name = role_name_mappings[speaker_name]
                logger.info(
                    f"役職'{speaker_name}'を人名'{resolved_name}'に解決（マッピング使用）"
                )
            else:
                # マッピングがない場合は早期リターン（BAML呼び出しをスキップ）
                logger.debug(
                    f"役職のみの発言者をスキップ（マッピングなし）: '{speaker_name}'"
                )
                return PoliticianMatch(
                    matched=False,
                    confidence=0.0,
                    reason=f"役職名のみでマッピングなし: {speaker_name}",
                )

        # 既存の政治家リストを取得
        available_politicians = await self.politician_repository.get_all_for_matching()

        if not available_politicians:
            return PoliticianMatch(
                matched=False, confidence=0.0, reason="利用可能な政治家リストが空です"
            )

        # まず従来のルールベースマッチングを試行（高速パス）
        # 解決済みの名前を使用
        rule_based_match = self._rule_based_matching(
            resolved_name, speaker_party, available_politicians
        )
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            logger.info(f"ルールベースマッチング成功: '{resolved_name}'")
            return rule_based_match

        # BAMLによる高度なマッチング
        try:
            # 候補を絞り込み（パフォーマンス向上のため）
            # 解決済みの名前を使用
            filtered_politicians = self._filter_candidates(
                resolved_name, speaker_party, available_politicians
            )

            # BAML関数を呼び出し（解決済みの名前を使用）
            baml_result = await b.MatchPolitician(
                speaker_name=resolved_name,
                speaker_type=speaker_type or "不明",
                speaker_party=speaker_party or "不明",
                available_politicians=self._format_politicians_for_llm(
                    filtered_politicians
                ),
            )

            # BAML結果をPoliticianMatchに変換
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
                match_result = PoliticianMatch(
                    matched=False,
                    politician_id=None,
                    politician_name=None,
                    political_party_name=None,
                    confidence=match_result.confidence,
                    reason=match_result.reason,
                )

            logger.info(
                f"BAMLマッチング結果: '{resolved_name}' - "
                f"matched={match_result.matched}, confidence={match_result.confidence}"
            )

            return match_result

        except BamlValidationError as e:
            # LLMが構造化出力を返さなかった場合（自然言語での回答など）
            # これは正常なケースとして扱い、マッチなし結果を返す
            logger.warning(
                f"BAMLバリデーション失敗: '{resolved_name}' - {e}. "
                "マッチなし結果を返します。"
            )
            return PoliticianMatch(
                matched=False,
                confidence=0.0,
                reason=f"LLMが構造化出力を返せませんでした: {resolved_name}",
            )
        except Exception as e:
            logger.error(
                f"BAML政治家マッチング中のエラー: '{resolved_name}' - {e}",
                exc_info=True,
            )
            raise ExternalServiceException(
                service_name="BAML",
                operation="politician_matching",
                reason=f"政治家マッチング中にエラーが発生しました: {e}",
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
