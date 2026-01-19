"""Use case for extracting proposal judges from web pages."""

import logging

from datetime import datetime

from src.application.dtos.proposal_judge_dto import (
    CreateProposalJudgesInputDTO,
    CreateProposalJudgesOutputDTO,
    ExtractedJudgeDTO,
    ExtractProposalJudgesInputDTO,
    ExtractProposalJudgesOutputDTO,
    JudgeMatchResultDTO,
    MatchProposalJudgesInputDTO,
    MatchProposalJudgesOutputDTO,
    ProposalJudgeDTO,
)
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.repositories.extracted_proposal_judge_repository import (
    ExtractedProposalJudgeRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.proposal_judge_repository import ProposalJudgeRepository
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.web_scraper_service import IWebScraperService


logger = logging.getLogger(__name__)


class ExtractProposalJudgesUseCase:
    """議案賛否情報抽出ユースケース

    議案ページから賛成者・反対者のリストを抽出し、
    政治家とのマッチングを行い、最終的にProposalJudgeレコードを作成する
    3段階プロセスを管理します。

    処理フロー:
    1. extract_judges: WebページからLLMで賛否情報を抽出
    2. match_judges: 抽出した名前と既存政治家をマッチング
    3. create_judges: マッチング結果からProposalJudgeを作成

    Attributes:
        proposal_repo: 議案リポジトリ
        politician_repo: 政治家リポジトリ
        extracted_repo: 抽出済み賛否情報リポジトリ
        judge_repo: 議案賛否リポジトリ
        scraper: Webスクレイピングサービス
        llm: LLMサービス
    """

    def __init__(
        self,
        proposal_repository: ProposalRepository,
        politician_repository: PoliticianRepository,
        extracted_proposal_judge_repository: ExtractedProposalJudgeRepository,
        proposal_judge_repository: ProposalJudgeRepository,
        web_scraper_service: IWebScraperService,
        llm_service: ILLMService,
    ):
        """議案賛否情報抽出ユースケースを初期化する

        Args:
            proposal_repository: 議案リポジトリの実装
            politician_repository: 政治家リポジトリの実装
            extracted_proposal_judge_repository: 抽出済み賛否情報リポジトリの実装
            proposal_judge_repository: 議案賛否リポジトリの実装
            web_scraper_service: Webスクレイピングサービス
            llm_service: LLMサービス
        """
        self.proposal_repo = proposal_repository
        self.politician_repo = politician_repository
        self.extracted_repo = extracted_proposal_judge_repository
        self.judge_repo = proposal_judge_repository
        self.scraper = web_scraper_service
        self.llm = llm_service

    async def extract_judges(
        self, request: ExtractProposalJudgesInputDTO
    ) -> ExtractProposalJudgesOutputDTO:
        """議案ページから賛否情報を抽出する

        URLから議案の賛成者・反対者リストを抽出し、
        ステージングテーブル（extracted_proposal_judges）に保存します。

        Args:
            request: 抽出リクエストDTO
                - url: 議案ページのURL
                - proposal_id: 議案ID（オプション）
                - conference_id: 会議体ID（オプション）
                - force: 既存データを強制的に再抽出するか

        Returns:
            ExtractProposalJudgesOutputDTO:
                - proposal_id: 議案ID
                - extracted_count: 抽出された賛否情報数
                - judges: 抽出された賛否情報DTOリスト

        Raises:
            ValueError: URLがサポートされていない場合
            RuntimeError: スクレイピングに失敗した場合
        """
        logger.info(f"Starting to extract proposal judges from URL: {request.url}")

        # Check if URL is supported
        if not self.scraper.is_supported_url(request.url):
            raise ValueError(f"Unsupported URL: {request.url}")

        # Check existing if not forcing
        if not request.force and request.proposal_id:
            existing = await self.extracted_repo.get_by_proposal(request.proposal_id)
            if existing:
                logger.info(
                    f"Found {len(existing)} existing judges for "
                    f"proposal {request.proposal_id}"
                )
                return ExtractProposalJudgesOutputDTO(
                    proposal_id=request.proposal_id,
                    extracted_count=len(existing),
                    judges=[self._to_extracted_dto(j) for j in existing],
                )

        # Scrape and extract judges using LLM
        try:
            judges_data = await self.scraper.scrape_proposal_judges(request.url)
        except Exception as e:
            logger.error(
                f"Failed to scrape proposal judges from {request.url}: {str(e)}"
            )
            raise RuntimeError(f"Failed to scrape proposal judges: {str(e)}") from e

        # Save to staging table
        created_judges: list[ExtractedProposalJudge] = []
        for judge_data in judges_data:
            # Judgment is already normalized by domain service
            judgment = judge_data.get("judgment", "APPROVE")

            judge = ExtractedProposalJudge(
                proposal_id=request.proposal_id or 0,  # Default to 0 if None
                extracted_politician_name=judge_data["name"],
                extracted_party_name=judge_data.get("party"),
                extracted_judgment=judgment,
                source_url=request.url,
            )
            created = await self.extracted_repo.create(judge)
            created_judges.append(created)

        logger.info(f"Successfully extracted {len(created_judges)} judges")
        return ExtractProposalJudgesOutputDTO(
            proposal_id=request.proposal_id,
            extracted_count=len(created_judges),
            judges=[self._to_extracted_dto(j) for j in created_judges],
        )

    async def match_judges(
        self, request: MatchProposalJudgesInputDTO
    ) -> MatchProposalJudgesOutputDTO:
        """抽出済み賛否情報と既存政治家をマッチングする

        LLMを使用してファジーマッチングを行い、信頼度スコアを付与します。
        - matched: 信頼度 ≥ 0.7
        - needs_review: 0.5 ≤ 信頼度 < 0.7
        - no_match: 信頼度 < 0.5

        Args:
            request: マッチングリクエストDTO
                - proposal_id: 議案ID（オプション）
                - judge_ids: 特定の賛否情報IDリスト（オプション）

        Returns:
            MatchProposalJudgesOutputDTO:
                - matched_count: マッチ成功数
                - needs_review_count: 要確認数
                - no_match_count: マッチなし数
                - results: マッチング結果DTOリスト
        """
        logger.info("Starting to match proposal judges with politicians")

        # Get judges to process
        if request.proposal_id:
            judges = await self.extracted_repo.get_pending_by_proposal(
                request.proposal_id
            )
        elif request.judge_ids:
            # Get specific judges by IDs
            all_judges = await self.extracted_repo.get_all_pending()
            judges = [j for j in all_judges if j.id in request.judge_ids]
        else:
            judges = await self.extracted_repo.get_all_pending()

        logger.info(f"Found {len(judges)} judges to match")

        results: list[JudgeMatchResultDTO] = []
        for judge in judges:
            match_result = await self._match_judge_to_politician(judge)
            results.append(match_result)

        # Count by status
        matched_count = sum(1 for r in results if r.matching_status == "matched")
        needs_review = sum(1 for r in results if r.matching_status == "needs_review")
        no_match = sum(1 for r in results if r.matching_status == "no_match")

        logger.info(
            f"Matching complete: {matched_count} matched, "
            f"{needs_review} needs review, {no_match} no match"
        )

        return MatchProposalJudgesOutputDTO(
            matched_count=matched_count,
            needs_review_count=needs_review,
            no_match_count=no_match,
            results=results,
        )

    async def create_judges(
        self, request: CreateProposalJudgesInputDTO
    ) -> CreateProposalJudgesOutputDTO:
        """マッチング結果から議案賛否情報を作成する

        'matched'ステータスの賛否情報のみを対象に、
        proposal_judgesテーブルに賛否情報を作成します。

        Args:
            request: 賛否情報作成リクエストDTO
                - proposal_id: 議案ID（オプション）
                - judge_ids: 特定の賛否情報IDリスト（オプション）

        Returns:
            CreateProposalJudgesOutputDTO:
                - created_count: 作成された賛否情報数
                - skipped_count: スキップされた数
                - judges: 作成された賛否情報DTOリスト

        Raises:
            ValueError: 議案またはマッチした政治家が見つからない場合
        """
        logger.info("Starting to create proposal judges from matched data")

        # Get matched judges
        if request.proposal_id:
            judges = await self.extracted_repo.get_matched_by_proposal(
                request.proposal_id
            )
        elif request.judge_ids:
            # Get specific judges by IDs that are matched
            all_judges = await self.extracted_repo.get_all_matched()
            judges = [j for j in all_judges if j.id in request.judge_ids]
        else:
            judges = await self.extracted_repo.get_all_matched()

        logger.info(f"Found {len(judges)} matched judges to process")

        created_judges: list[ProposalJudgeDTO] = []
        skipped_count = 0

        for judge in judges:
            if not judge.matched_politician_id:
                skipped_count += 1
                continue

            if not judge.proposal_id:
                logger.warning(f"Judge {judge.id} has no proposal_id, skipping")
                skipped_count += 1
                continue

            # Check if judge already exists
            existing = await self.judge_repo.get_by_proposal_and_politician(
                judge.proposal_id, judge.matched_politician_id
            )

            if existing:
                logger.info(
                    f"Judge already exists for proposal {judge.proposal_id} "
                    f"and politician {judge.matched_politician_id}"
                )
                skipped_count += 1
                continue

            # Get politician for validation
            politician = await self.politician_repo.get_by_id(
                judge.matched_politician_id
            )
            if not politician:
                raise ValueError(f"Politician {judge.matched_politician_id} not found")

            # Create proposal judge
            proposal_judge = ProposalJudge(
                proposal_id=judge.proposal_id,
                politician_id=judge.matched_politician_id,
                approve=judge.extracted_judgment,
            )

            created = await self.judge_repo.create(proposal_judge)

            # Mark extracted judge as processed
            await self.extracted_repo.mark_processed(judge.id or 0)

            created_judges.append(
                ProposalJudgeDTO(
                    id=created.id or 0,
                    proposal_id=created.proposal_id,
                    politician_id=created.politician_id,
                    politician_name=politician.name,
                    judgment=created.approve or "Unknown",
                    created_at=created.created_at or datetime.now(),
                    updated_at=created.updated_at or datetime.now(),
                )
            )

        logger.info(
            f"Created {len(created_judges)} proposal judges, skipped {skipped_count}"
        )

        return CreateProposalJudgesOutputDTO(
            created_count=len(created_judges),
            skipped_count=skipped_count,
            judges=created_judges,
        )

    async def _match_judge_to_politician(
        self, judge: ExtractedProposalJudge
    ) -> JudgeMatchResultDTO:
        """個別賛否情報と政治家のマッチングを実行する

        Args:
            judge: 抽出済み賛否情報エンティティ

        Returns:
            マッチング結果DTO
        """
        # Search for politicians by name
        name = judge.extracted_politician_name or ""
        if not name:
            # No name to match
            judge.matching_status = "no_match"
            judge.matching_confidence = 0.0
            await self.extracted_repo.update_matching_result(
                judge.id or 0,
                politician_id=None,
                confidence=0.0,
                status="no_match",
            )

            return JudgeMatchResultDTO(
                judge_id=judge.id or 0,
                judge_name="Unknown",
                judgment=judge.extracted_judgment or "Unknown",
                matched_politician_id=None,
                matched_politician_name=None,
                confidence_score=0.0,
                matching_status="no_match",
                matching_notes="No name to match",
            )

        candidates = await self.politician_repo.search_by_name(name)

        # Filter by party if available
        if judge.extracted_party_name:
            filtered = []
            for candidate in candidates:
                # Check if party name matches (this would need party info on politician)
                # For now, just add all candidates
                filtered.append(candidate)
            candidates = filtered if filtered else candidates

        if not candidates:
            # No candidates found
            judge.matching_status = "no_match"
            judge.matching_confidence = 0.0
            await self.extracted_repo.update_matching_result(
                judge.id or 0,
                politician_id=None,
                confidence=0.0,
                status="no_match",
            )

            return JudgeMatchResultDTO(
                judge_id=judge.id or 0,
                judge_name=name,
                judgment=judge.extracted_judgment or "Unknown",
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

        # Use the same matching logic as conference members
        match_result = await self.llm.match_conference_member(
            name,
            judge.extracted_party_name,
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

                # Update judge
                judge.matched_politician_id = politician.id
                judge.matching_confidence = confidence
                judge.matching_status = status
                await self.extracted_repo.update_matching_result(
                    judge.id or 0,
                    politician_id=judge.matched_politician_id,
                    confidence=judge.matching_confidence,
                    status=judge.matching_status,
                )

                return JudgeMatchResultDTO(
                    judge_id=judge.id or 0,
                    judge_name=name,
                    judgment=judge.extracted_judgment or "Unknown",
                    matched_politician_id=politician.id,
                    matched_politician_name=politician.name,
                    confidence_score=confidence,
                    matching_status=status,
                    matching_notes=match_result.get("reason", ""),
                )

        # No match
        judge.matching_status = "no_match"
        judge.matching_confidence = 0.0
        await self.extracted_repo.update_matching_result(
            judge.id or 0,
            politician_id=None,
            confidence=0.0,
            status="no_match",
        )

        return JudgeMatchResultDTO(
            judge_id=judge.id or 0,
            judge_name=name,
            judgment=judge.extracted_judgment or "Unknown",
            matched_politician_id=None,
            matched_politician_name=None,
            confidence_score=0.0,
            matching_status="no_match",
            matching_notes="LLM could not find a match",
        )

    def _to_extracted_dto(self, judge: ExtractedProposalJudge) -> ExtractedJudgeDTO:
        """抽出済み賛否情報エンティティをDTOに変換する

        Args:
            judge: 抽出済み賛否情報エンティティ

        Returns:
            抽出済み賛否情報DTO
        """
        return ExtractedJudgeDTO(
            id=judge.id or 0,
            proposal_id=judge.proposal_id,
            extracted_name=judge.extracted_politician_name or "Unknown",
            extracted_party_name=judge.extracted_party_name,
            extracted_judgment=judge.extracted_judgment or "Unknown",
            source_url=judge.source_url or "",
            matched_politician_id=judge.matched_politician_id,
            matching_status=judge.matching_status,
            confidence_score=judge.matching_confidence,
            created_at=judge.extracted_at or datetime.now(),
            updated_at=judge.extracted_at or datetime.now(),
        )
