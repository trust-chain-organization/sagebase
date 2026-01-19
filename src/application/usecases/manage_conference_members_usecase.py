"""Use case for managing conference members."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from src.application.dtos.conference_dto import (
    CreateAffiliationDTO,
    ExtractedConferenceMemberDTO,
)
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.entities.politician_affiliation import PoliticianAffiliation
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository,
)
from src.domain.repositories.politician_affiliation_repository import (
    PoliticianAffiliationRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.conference_domain_service import ConferenceDomainService
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.web_scraper_service import IWebScraperService


# DTOs for Use Case
@dataclass
class ExtractMembersInputDTO:
    """Input DTO for extract_members."""

    conference_id: int
    force: bool = False


@dataclass
class ExtractedMemberDTO:
    """DTO for extracted member data."""

    id: int
    conference_id: int
    name: str
    role: str | None
    party_affiliation: str | None
    matched_politician_id: int | None
    matching_status: str
    confidence_score: float | None


@dataclass
class ExtractMembersOutputDTO:
    """Output DTO for extract_members."""

    conference_id: int
    extracted_count: int
    members: list[ExtractedMemberDTO]


@dataclass
class MatchMembersInputDTO:
    """Input DTO for match_members."""

    conference_id: int | None = None
    member_ids: list[int] | None = None


@dataclass
class MemberMatchResultDTO:
    """DTO for member match result."""

    member_id: int
    member_name: str
    matched_politician_id: int | None
    matched_politician_name: str | None
    confidence_score: float
    matching_status: str
    matching_notes: str


@dataclass
class MatchMembersOutputDTO:
    """Output DTO for match_members."""

    matched_count: int
    needs_review_count: int
    no_match_count: int
    results: list[MemberMatchResultDTO]


@dataclass
class CreateAffiliationsInputDTO:
    """Input DTO for create_affiliations."""

    conference_id: int | None = None
    member_ids: list[int] | None = None
    start_date: date | None = None


@dataclass
class PoliticianAffiliationDTO:
    """DTO for politician affiliation data."""

    id: int
    politician_id: int
    politician_name: str
    conference_id: int
    role: str | None
    start_date: date
    end_date: date | None


@dataclass
class CreateAffiliationsOutputDTO:
    """Output DTO for create_affiliations."""

    created_count: int
    skipped_count: int
    affiliations: list[PoliticianAffiliationDTO]


# Protocol for external repositories
class ExtractedMemberEntity:
    """Minimal entity for extracted member."""

    id: int
    name: str
    conference_id: int
    party_affiliation: str | None
    role: str | None
    matching_status: str
    matched_politician_id: int | None
    confidence_score: float | None


class ExtractedMemberRepository(Protocol):
    """Protocol for extracted member repository."""

    async def get_by_conference(
        self, conference_id: int
    ) -> list[ExtractedMemberEntity]:
        """Get extracted members by conference."""
        ...

    async def get_pending_by_conference(
        self, conference_id: int
    ) -> list[ExtractedMemberEntity]:
        """Get pending extracted members by conference."""
        ...

    async def get_all_pending(self) -> list[ExtractedMemberEntity]:
        """Get all pending extracted members."""
        ...

    async def get_by_conference_and_status(
        self, conference_id: int, status: str | None
    ) -> list[ExtractedMemberEntity]:
        """Get extracted members by conference and status."""
        ...

    async def get_by_status(self, status: str | None) -> list[ExtractedMemberEntity]:
        """Get extracted members by status."""
        ...

    async def create(
        self, member: ExtractedConferenceMemberDTO
    ) -> ExtractedMemberEntity:
        """Create extracted member."""
        ...

    async def update(
        self, member_id: int, data: dict[str, Any]
    ) -> ExtractedMemberEntity:
        """Update extracted member."""
        ...

    async def update_matching_status(
        self,
        member_id: int,
        status: str,
        matched_politician_id: int | None,
        confidence_score: float,
    ) -> None:
        """Update member matching status."""
        ...

    async def mark_processed(self, member_id: int) -> None:
        """Mark member as processed."""
        ...


class AffiliationEntity:
    """Minimal entity for affiliation."""

    id: int
    politician_id: int
    conference_id: int
    start_date: date
    end_date: date | None
    role: str | None


class AffiliationRepository(Protocol):
    """Protocol for affiliation repository."""

    async def create(self, affiliation: CreateAffiliationDTO) -> AffiliationEntity:
        """Create affiliation."""
        ...

    async def get_by_politician_and_conference(
        self, politician_id: int, conference_id: int
    ) -> list[AffiliationEntity]:
        """Get affiliations by politician and conference."""
        ...


class ManageConferenceMembersUseCase:
    """会議体メンバー管理ユースケース

    会議体（議会・委員会）のメンバー情報を抽出、マッチング、
    所属情報作成を行う3段階プロセスを管理します。

    処理フロー：
    1. extract_members: WebページからメンバーをLLMで抽出
    2. match_members: 抽出メンバーと既存政治家をマッチング
    3. create_affiliations: マッチング結果から所属情報を作成

    Attributes:
        conference_repo: 会議体リポジトリ
        politician_repo: 政治家リポジトリ
        conference_service: 会議体ドメインサービス
        extracted_repo: 抽出済みメンバーリポジトリ
        affiliation_repo: 所属情報リポジトリ
        scraper: Webスクレイピングサービス
        llm: LLMサービス

    Example:
        >>> use_case = ManageConferenceMembersUseCase(...)
        >>>
        >>> # Step 1: メンバー抽出
        >>> extracted = await use_case.extract_members(
        ...     ExtractMembersInputDTO(conference_id=185)
        ... )
        >>>
        >>> # Step 2: 政治家マッチング
        >>> matched = await use_case.match_members(
        ...     MatchMembersInputDTO(conference_id=185)
        ... )
        >>>
        >>> # Step 3: 所属情報作成
        >>> created = await use_case.create_affiliations(
        ...     CreateAffiliationsInputDTO(conference_id=185)
        ... )
    """

    def __init__(
        self,
        conference_repository: ConferenceRepository,
        politician_repository: PoliticianRepository,
        conference_domain_service: ConferenceDomainService,
        extracted_member_repository: ExtractedConferenceMemberRepository,
        politician_affiliation_repository: PoliticianAffiliationRepository,
        web_scraper_service: IWebScraperService,
        llm_service: ILLMService,
    ):
        """会議体メンバー管理ユースケースを初期化する

        Args:
            conference_repository: 会議体リポジトリの実装
            politician_repository: 政治家リポジトリの実装
            conference_domain_service: 会議体ドメインサービス
            extracted_member_repository: 抽出済みメンバーリポジトリの実装
            politician_affiliation_repository: 所属情報リポジトリの実装
            web_scraper_service: Webスクレイピングサービス
            llm_service: LLMサービス
        """
        self.conference_repo = conference_repository
        self.politician_repo = politician_repository
        self.conference_service = conference_domain_service
        self.extracted_repo = extracted_member_repository
        self.affiliation_repo = politician_affiliation_repository
        self.scraper = web_scraper_service
        self.llm = llm_service

    async def extract_members(
        self, request: ExtractMembersInputDTO
    ) -> ExtractMembersOutputDTO:
        """会議体メンバーをWebページから抽出する

        会議体のmembers_introduction_urlからメンバー情報を抽出し、
        ステージングテーブル（extracted_conference_members）に保存します。

        Args:
            request: 抽出リクエストDTO
                - conference_id: 対象会議体ID
                - force: 既存データを強制的に再抽出するか

        Returns:
            ExtractMembersOutputDTO:
                - conference_id: 会議体ID
                - extracted_count: 抽出されたメンバー数
                - members: 抽出されたメンバーDTOリスト

        Raises:
            ValueError: 会議体が見つからない、URLが未設定の場合
        """
        # Get conference
        conference = await self.conference_repo.get_by_id(request.conference_id)
        if not conference:
            raise ValueError(f"Conference {request.conference_id} not found")

        if not conference.members_introduction_url:
            raise ValueError(f"Conference {conference.name} has no members URL")

        # Check existing if not forcing
        if not request.force:
            existing = await self.extracted_repo.get_by_conference(
                request.conference_id
            )
            if existing:
                return ExtractMembersOutputDTO(
                    conference_id=request.conference_id,
                    extracted_count=len(existing),
                    members=[self._to_extracted_dto(m) for m in existing],
                )

        # Scrape and extract members using LLM
        # In a real implementation, this would scrape and use LLM to extract data
        members_data = await self.scraper.scrape_conference_members(
            conference.members_introduction_url
        )

        # Save to staging table
        created_members: list[ExtractedConferenceMember] = []
        for member_data in members_data:
            member = ExtractedConferenceMember(
                conference_id=request.conference_id,
                extracted_name=member_data["name"],
                source_url=conference.members_introduction_url,
                extracted_role=member_data.get("role"),
                extracted_party_name=member_data.get("party"),
            )
            created = await self.extracted_repo.create(member)
            created_members.append(created)

        return ExtractMembersOutputDTO(
            conference_id=request.conference_id,
            extracted_count=len(created_members),
            members=[self._to_extracted_dto(m) for m in created_members],
        )

    async def match_members(
        self, request: MatchMembersInputDTO
    ) -> MatchMembersOutputDTO:
        """抽出済みメンバーと既存政治家をマッチングする

        LLMを使用してファジーマッチングを行い、信頼度スコアを付与します。
        - matched: 信頼度 ≥ 0.7
        - needs_review: 0.5 ≤ 信頼度 < 0.7
        - no_match: 信頼度 < 0.5

        Args:
            request: マッチングリクエストDTO
                - conference_id: 対象会議体ID（オプション）
                - member_ids: 特定メンバーIDリスト（オプション）

        Returns:
            MatchMembersOutputDTO:
                - matched_count: マッチ成功数
                - needs_review_count: 要確認数
                - no_match_count: マッチなし数
                - results: マッチング結果DTOリスト
        """
        # Get members to process
        if request.conference_id:
            members = await self.extracted_repo.get_pending_members(
                request.conference_id
            )
        elif request.member_ids:
            # Get specific members by IDs
            all_members = await self.extracted_repo.get_pending_members()
            members = [m for m in all_members if m.id in request.member_ids]
        else:
            members = await self.extracted_repo.get_pending_members()

        results: list[MemberMatchResultDTO] = []
        for member in members:
            match_result = await self._match_member_to_politician(member)
            results.append(match_result)

        # Count by status
        matched_count = sum(1 for r in results if r.matching_status == "matched")
        needs_review = sum(1 for r in results if r.matching_status == "needs_review")
        no_match = sum(1 for r in results if r.matching_status == "no_match")

        return MatchMembersOutputDTO(
            matched_count=matched_count,
            needs_review_count=needs_review,
            no_match_count=no_match,
            results=results,
        )

    async def create_affiliations(
        self, request: CreateAffiliationsInputDTO
    ) -> CreateAffiliationsOutputDTO:
        """マッチング結果から政治家所属情報を作成する

        'matched'ステータスのメンバーのみを対象に、
        politician_affiliationsテーブルに所属情報を作成します。

        Args:
            request: 所属情報作成リクエストDTO
                - conference_id: 対象会議体ID（オプション）
                - member_ids: 特定メンバーIDリスト（オプション）
                - start_date: 所属開始日（デフォルト: 今日）

        Returns:
            CreateAffiliationsOutputDTO:
                - created_count: 作成された所属情報数
                - skipped_count: スキップされた数
                - affiliations: 作成された所属情報DTOリスト

        Raises:
            ValueError: マッチした政治家が見つからない場合
        """
        # Get matched members
        if request.conference_id:
            members = await self.extracted_repo.get_matched_members(
                request.conference_id
            )
        elif request.member_ids:
            # Get specific members by IDs that are matched
            all_members = await self.extracted_repo.get_matched_members()
            members = [m for m in all_members if m.id in request.member_ids]
        else:
            members = await self.extracted_repo.get_matched_members()

        created_affiliations: list[PoliticianAffiliationDTO] = []
        skipped_count = 0

        for member in members:
            if not member.matched_politician_id:
                skipped_count += 1
                continue

            # Check if affiliation already exists
            existing = await self.affiliation_repo.get_by_politician_and_conference(
                member.matched_politician_id, member.conference_id
            )

            if existing:
                # Check if any active affiliation exists
                active = [a for a in existing if not a.end_date]
                if active:
                    # Active affiliation already exists
                    skipped_count += 1
                    continue

            # Get politician for validation
            politician = await self.politician_repo.get_by_id(
                member.matched_politician_id
            )
            if not politician:
                raise ValueError(f"Politician {member.matched_politician_id} not found")

            # Create affiliation
            affiliation = PoliticianAffiliation(
                politician_id=member.matched_politician_id,
                conference_id=member.conference_id,
                role=member.extracted_role,
                start_date=request.start_date or datetime.now().date(),
            )

            created = await self.affiliation_repo.create(affiliation)
            created_affiliations.append(
                PoliticianAffiliationDTO(
                    id=created.id or 0,
                    politician_id=created.politician_id,
                    politician_name=politician.name,
                    conference_id=created.conference_id,
                    role=created.role,
                    start_date=created.start_date,
                    end_date=created.end_date,
                )
            )

        return CreateAffiliationsOutputDTO(
            created_count=len(created_affiliations),
            skipped_count=skipped_count,
            affiliations=created_affiliations,
        )

    async def _match_member_to_politician(
        self, member: ExtractedConferenceMember
    ) -> MemberMatchResultDTO:
        """個別メンバーと政治家のマッチングを実行する

        Args:
            member: 抽出済みメンバーエンティティ

        Returns:
            マッチング結果DTO
        """
        # Search for politicians by name and party
        candidates = await self.politician_repo.search_by_name(member.extracted_name)

        # Filter by party if available
        if member.extracted_party_name:
            filtered = []
            for candidate in candidates:
                # Would need to check party name
                filtered.append(candidate)
            candidates = filtered if filtered else candidates

        if not candidates:
            # No candidates found
            member.matching_status = "no_match"
            member.matching_confidence = 0.0
            # Update matching result
            await self.extracted_repo.update_matching_result(
                member.id or 0,
                member.matched_politician_id,
                member.matching_confidence,
                member.matching_status,
            )

            return MemberMatchResultDTO(
                member_id=member.id or 0,
                member_name=member.extracted_name,
                matched_politician_id=None,
                matched_politician_name=None,
                confidence_score=0.0,
                matching_status="no_match",
                matching_notes="No matching politicians found",
            )

        # Use LLM for fuzzy matching
        from typing import cast

        from src.application.dtos.base_dto import PoliticianBaseDTO

        candidate_dtos = cast(
            list[PoliticianBaseDTO],
            [
                {
                    "id": c.id,
                    "name": c.name,
                    "party_id": c.political_party_id,
                    "prefecture": None,
                    "electoral_district": None,
                    "profile_url": None,
                    "image_url": None,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                }
                for c in candidates
            ],
        )

        match_result = await self.llm.match_conference_member(
            member.extracted_name,
            member.extracted_party_name,
            candidate_dtos,
        )

        if match_result and match_result["matched_id"]:
            politician = await self.politician_repo.get_by_id(
                match_result["matched_id"]
            )
            if politician:
                confidence = match_result["confidence"]

                # Determine status based on confidence
                if confidence >= 0.7:
                    status = "matched"
                elif confidence >= 0.5:
                    status = "needs_review"
                else:
                    status = "no_match"

                # Update member
                member.matched_politician_id = politician.id
                member.matching_confidence = confidence
                member.matching_status = status
                # Update matching result
                await self.extracted_repo.update_matching_result(
                    member.id or 0,
                    member.matched_politician_id,
                    member.matching_confidence,
                    member.matching_status,
                )

                return MemberMatchResultDTO(
                    member_id=member.id or 0,
                    member_name=member.extracted_name,
                    matched_politician_id=politician.id,
                    matched_politician_name=politician.name,
                    confidence_score=confidence,
                    matching_status=status,
                    matching_notes="",
                )

        # No match
        member.matching_status = "no_match"
        member.matching_confidence = 0.0
        await self.extracted_repo.update_matching_result(
            member.id or 0,
            None,
            0.0,
            "no_match",
        )

        return MemberMatchResultDTO(
            member_id=member.id or 0,
            member_name=member.extracted_name,
            matched_politician_id=None,
            matched_politician_name=None,
            confidence_score=0.0,
            matching_status="no_match",
            matching_notes="LLM could not find a match",
        )

    def _to_extracted_dto(
        self, member: ExtractedConferenceMember
    ) -> ExtractedMemberDTO:
        """抽出済みメンバーエンティティをDTOに変換する

        Args:
            member: 抽出済みメンバーエンティティ

        Returns:
            抽出済みメンバーDTO
        """
        return ExtractedMemberDTO(
            id=member.id or 0,
            conference_id=member.conference_id,
            name=member.extracted_name,
            role=member.extracted_role,
            party_affiliation=member.extracted_party_name,
            matched_politician_id=member.matched_politician_id,
            matching_status=member.matching_status,
            confidence_score=member.matching_confidence,
        )
