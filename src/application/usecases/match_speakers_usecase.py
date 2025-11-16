"""Use case for matching speakers to politicians."""

from uuid import UUID

from src.application.dtos.speaker_dto import SpeakerMatchingDTO
from src.domain.entities.speaker import Speaker
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.domain.types.llm import LLMSpeakerMatchContext


class MatchSpeakersUseCase:
    """発言者と政治家のマッチングユースケース

    発言者（Speaker）と政治家（Politician）を名前や所属政党情報を基に
    マッチングします。ルールベースとLLMベースの2段階マッチングを実装。

    Attributes:
        speaker_repo: 発言者リポジトリ
        politician_repo: 政治家リポジトリ
        conversation_repo: 発言リポジトリ
        speaker_service: 発言者ドメインサービス
        llm_service: LLMサービス（同期版アダプタ）

    Example:
        >>> use_case = MatchSpeakersUseCase(
        ...     speaker_repo, politician_repo, conversation_repo,
        ...     speaker_service, llm_service
        ... )
        >>> results = use_case.execute(use_llm=True, limit=100)
        >>> for result in results:
        ...     if result.matched_politician_id:
        ...         print(f"{result.speaker_name} → {result.matched_politician_name}")
    """

    def __init__(
        self,
        speaker_repository: SpeakerRepository,
        politician_repository: PoliticianRepository,
        conversation_repository: ConversationRepository,
        speaker_domain_service: SpeakerDomainService,
        llm_service: ILLMService,  # LLMServiceAdapter for sync usage
    ):
        """発言者マッチングユースケースを初期化する

        Args:
            speaker_repository: 発言者リポジトリの実装
            politician_repository: 政治家リポジトリの実装
            conversation_repository: 発言リポジトリの実装
            speaker_domain_service: 発言者ドメインサービス
            llm_service: LLMサービスアダプタ（同期版）
        """
        self.speaker_repo = speaker_repository
        self.politician_repo = politician_repository
        self.conversation_repo = conversation_repository
        self.speaker_service = speaker_domain_service
        self.llm_service = llm_service

    async def execute(
        self,
        use_llm: bool = True,
        speaker_ids: list[int] | None = None,
        limit: int | None = None,
        user_id: UUID | None = None,
    ) -> list[SpeakerMatchingDTO]:
        """発言者と政治家のマッチングを実行する

        マッチング処理の流れ：
        1. 既にリンクされている発言者をスキップ
        2. ルールベースマッチング（名前の類似度）
        3. LLMベースマッチング（コンテキストを考慮）

        Args:
            use_llm: LLMマッチングを使用するか（デフォルト: True）
            speaker_ids: 処理対象の発言者IDリスト（Noneの場合は全件）
            limit: 処理する発言者数の上限
            user_id: マッチング作業を実行したユーザーのID（UUID）

        Returns:
            SpeakerMatchingDTOのリスト。各DTOには以下が含まれる：
            - speaker_id: 発言者ID
            - speaker_name: 発言者名
            - matched_politician_id: マッチした政治家ID（マッチなしの場合None）
            - matched_politician_name: マッチした政治家名
            - confidence_score: マッチング信頼度（0.0〜1.0）
            - matching_method: マッチング手法（existing/rule-based/llm/none）
            - matching_reason: マッチング理由の説明
        """
        # Get speakers to process
        speakers: list[Speaker] = []
        if speaker_ids:
            # Fetch speakers individually
            for speaker_id in speaker_ids:
                speaker = await self.speaker_repo.get_by_id(speaker_id)
                if speaker:
                    speakers.append(speaker)
        else:
            # Get all politician speakers
            speakers = await self.speaker_repo.get_politicians()
            if limit:
                speakers = speakers[:limit]

        results: list[SpeakerMatchingDTO] = []

        for speaker in speakers:
            # Skip if already linked
            if speaker.id is None:
                continue
            # Check if speaker already has politician_id linked
            if speaker.politician_id:
                existing_politician = await self.politician_repo.get_by_id(
                    speaker.politician_id
                )
                if existing_politician:
                    results.append(
                        SpeakerMatchingDTO(
                            speaker_id=speaker.id if speaker.id is not None else 0,
                            speaker_name=speaker.name,
                            matched_politician_id=existing_politician.id,
                            matched_politician_name=existing_politician.name,
                            confidence_score=1.0,
                            matching_method="existing",
                            matching_reason="Already linked to politician",
                        )
                    )
                    continue

            # Try rule-based matching first
            match_result = await self._rule_based_matching(speaker)

            if not match_result and use_llm:
                # Try LLM-based matching
                match_result = await self._llm_based_matching(speaker)

            if match_result:
                # Update speaker with matched politician_id and user_id
                if match_result.matched_politician_id:
                    speaker.politician_id = match_result.matched_politician_id
                    speaker.matched_by_user_id = user_id
                    await self.speaker_repo.update(speaker)
                results.append(match_result)
            else:
                # No match found
                results.append(
                    SpeakerMatchingDTO(
                        speaker_id=speaker.id if speaker.id is not None else 0,
                        speaker_name=speaker.name,
                        matched_politician_id=None,
                        matched_politician_name=None,
                        confidence_score=0.0,
                        matching_method="none",
                        matching_reason="No matching politician found",
                    )
                )

        return results

    async def _rule_based_matching(self, speaker: Speaker) -> SpeakerMatchingDTO | None:
        """ルールベースの発言者マッチングを実行する

        名前の類似度と政党情報を使用してマッチングします。
        類似度が0.8以上の場合にマッチとみなします。

        Args:
            speaker: マッチング対象の発言者

        Returns:
            マッチング結果DTO（マッチなしの場合None）
        """
        # Normalize speaker name
        normalized_name = self.speaker_service.normalize_speaker_name(speaker.name)

        # Search for politicians with similar names
        candidates = await self.politician_repo.search_by_name(normalized_name)
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            # Calculate similarity
            score = self.speaker_service.calculate_name_similarity(
                speaker.name, candidate.name
            )

            # Boost score if party matches
            if speaker.political_party_name and candidate.political_party_id:
                # Would need to lookup party name
                score += 0.1

            if score > best_score and score >= 0.8:
                best_match = candidate
                best_score = score

        if best_match:
            return SpeakerMatchingDTO(
                speaker_id=speaker.id if speaker.id is not None else 0,
                speaker_name=speaker.name,
                matched_politician_id=best_match.id,
                matched_politician_name=best_match.name,
                confidence_score=best_score,
                matching_method="rule-based",
                matching_reason=f"Name similarity score: {best_score:.2f}",
            )

        return None

    async def _llm_based_matching(self, speaker: Speaker) -> SpeakerMatchingDTO | None:
        """LLMベースの発言者マッチングを実行する

        LLMを使用して、コンテキスト情報を考慮した高度なマッチングを行います。
        処理履歴はLLMProcessingHistoryに記録されます。

        Args:
            speaker: マッチング対象の発言者

        Returns:
            マッチング結果DTO（マッチなしの場合None）
        """
        # Get potential candidates
        candidates = await self.politician_repo.get_all(limit=100)
        if not candidates:
            return None

        # Prepare context for LLM
        context = LLMSpeakerMatchContext(
            speaker_name=speaker.name,
            normalized_name=self.speaker_service.normalize_speaker_name(speaker.name),
            party_affiliation=speaker.political_party_name,
            position=speaker.position,
            meeting_date="",  # Not available in this context
            candidates=[
                {
                    "id": str(c.id),
                    "name": c.name,
                    "party": "",  # Would need party name lookup
                }
                for c in candidates
            ],
        )

        # Add metadata for history recording (metadata passed via set_input_reference)

        # Set input reference for history tracking if supported
        # Runtime check - ILLMService doesn't require this method
        if hasattr(self.llm_service, "set_input_reference"):
            # type: ignore - optional method not in protocol
            self.llm_service.set_input_reference(  # type: ignore[attr-defined]
                reference_type="speaker",
                reference_id=speaker.id if speaker.id else 0,
            )

        # Call LLM service with metadata
        match_result = await self.llm_service.match_speaker_to_politician(context)

        if match_result and match_result.get("matched_id") is not None:
            matched_id = match_result["matched_id"]
            if matched_id is not None:
                politician = await self.politician_repo.get_by_id(matched_id)
                if politician:
                    return SpeakerMatchingDTO(
                        speaker_id=speaker.id if speaker.id is not None else 0,
                        speaker_name=speaker.name,
                        matched_politician_id=politician.id,
                        matched_politician_name=politician.name,
                        confidence_score=match_result.get("confidence", 0.8),
                        matching_method="llm",
                        matching_reason=match_result.get("reason", ""),
                    )

        return None
