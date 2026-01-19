"""Domain service for parliamentary group member matching logic."""

from src.application.dtos.base_dto import PoliticianBaseDTO
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.entities.politician import Politician
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.domain.types import LLMMatchResult


class ParliamentaryGroupMemberMatchingService:
    """議員団メンバーマッチングドメインサービス

    抽出された議員団メンバーと既存の政治家データをマッチングする
    ビジネスロジックを提供します。
    """

    def __init__(
        self,
        politician_repository: PoliticianRepository,
        llm_service: ILLMService,
        speaker_service: SpeakerDomainService,
    ):
        """Initialize the matching service.

        Args:
            politician_repository: 政治家リポジトリ
            llm_service: LLMサービス
            speaker_service: 発言者ドメインサービス（名前正規化等）
        """
        self.politician_repo = politician_repository
        self.llm_service = llm_service
        self.speaker_service = speaker_service

    async def find_matching_politician(
        self, member: ExtractedParliamentaryGroupMember
    ) -> tuple[int | None, float, str]:
        """抽出されたメンバーにマッチする政治家を検索する

        Args:
            member: 抽出された議員団メンバー

        Returns:
            (matched_politician_id, confidence_score, matching_reason)のタプル
        """
        # 名前を正規化
        normalized_name = self.speaker_service.normalize_speaker_name(
            member.extracted_name
        )

        # 1. ルールベースマッチング
        rule_match = await self._rule_based_matching(normalized_name, member)
        if rule_match and rule_match[1] >= 0.8:  # 信頼度0.8以上ならルールベースで確定
            return rule_match

        # 2. LLMベースマッチング
        llm_match = await self._llm_based_matching(member, normalized_name)
        if llm_match:
            return llm_match

        # マッチなし
        return None, 0.0, "No matching politician found"

    async def _rule_based_matching(
        self, normalized_name: str, member: ExtractedParliamentaryGroupMember
    ) -> tuple[int | None, float, str] | None:
        """ルールベースのマッチング

        Args:
            normalized_name: 正規化された名前
            member: 抽出されたメンバー

        Returns:
            (politician_id, confidence, reason) or None
        """
        # 名前で検索
        candidates = await self.politician_repo.search_by_name(normalized_name)

        if not candidates:
            return None

        best_match: Politician | None = None
        best_score = 0.0

        for candidate in candidates:
            # 名前の類似度を計算
            score = self.speaker_service.calculate_name_similarity(
                member.extracted_name, candidate.name
            )

            # 政党IDが一致する場合はスコアをブースト
            # Note: 現在のPoliticianエンティティには政党名がないため、
            # political_party_idの一致で判定
            if member.extracted_party_name and candidate.political_party_id:
                # 将来的には政党名のルックアップを実装
                score += 0.15

            if score > best_score:
                best_match = candidate
                best_score = score

        if best_match and best_score >= 0.7:
            return (
                best_match.id,
                best_score,
                f"Rule-based match: name similarity {best_score:.2f}",
            )

        return None

    async def _llm_based_matching(
        self, member: ExtractedParliamentaryGroupMember, normalized_name: str
    ) -> tuple[int | None, float, str] | None:
        """LLMベースのマッチング

        Args:
            member: 抽出されたメンバー
            normalized_name: 正規化された名前

        Returns:
            (politician_id, confidence, reason) or None
        """
        # 候補政治家を取得（名前で絞り込み）
        candidates = await self.politician_repo.search_by_name(normalized_name)

        # 候補が少ない場合は全政治家から検索
        if len(candidates) < 3:
            all_politicians = await self.politician_repo.get_all(limit=100)
            candidates = all_politicians

        if not candidates:
            return None

        # PoliticianBaseDTOのリストに変換
        # Note: PoliticianエンティティにはDTOに必要な全てのフィールドがないため、
        # 利用可能なフィールドのみを使用し、それ以外はNoneまたはダミー値を設定
        from datetime import datetime

        candidate_dtos: list[PoliticianBaseDTO] = [
            PoliticianBaseDTO(
                id=p.id or 0,
                name=p.name,
                party_id=p.political_party_id,
                prefecture=None,  # Politicianエンティティにはprefectureフィールドがない
                electoral_district=p.district,  # districtフィールドを使用
                profile_url=p.profile_page_url,
                image_url=None,  # Politicianエンティティにはimage_urlフィールドがない
                created_at=datetime.now(),  # ダミー値
                updated_at=datetime.now(),  # ダミー値
            )
            for p in candidates
        ]

        # LLMでマッチング
        match_result: (
            LLMMatchResult | None
        ) = await self.llm_service.match_conference_member(
            member_name=member.extracted_name,
            party_name=member.extracted_party_name,
            candidates=candidate_dtos,
        )

        if (
            match_result
            and match_result.get("matched")
            and match_result.get("matched_id")
        ):
            return (
                match_result["matched_id"],
                match_result.get("confidence", 0.7),
                match_result.get("reason", "LLM-based match"),
            )

        return None

    def determine_matching_status(self, confidence: float) -> str:
        """信頼度スコアからマッチングステータスを決定する

        Args:
            confidence: 信頼度スコア (0.0-1.0)

        Returns:
            マッチングステータス: "matched" or "no_match"
        """
        if confidence >= 0.7:
            return "matched"
        else:
            return "no_match"
