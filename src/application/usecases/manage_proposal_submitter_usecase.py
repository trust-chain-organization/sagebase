"""議案提出者の手動設定UseCase.

議案の提出者情報を手動で設定・更新するためのシンプルな操作を提供します。
LLMによる自動マッチング機能の前段階として、手動入力によるスキーマ検証を目的としています。
"""

from dataclasses import dataclass

from src.application.dtos.proposal_submitter_dto import ProposalSubmitterDTO
from src.application.dtos.submitter_candidates_dto import (
    ParliamentaryGroupCandidateDTO,
    PoliticianCandidateDTO,
    SubmitterCandidatesDTO,
)
from src.common.logging import get_logger
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.politician_affiliation_repository import (
    PoliticianAffiliationRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.repositories.proposal_submitter_repository import (
    ProposalSubmitterRepository,
)
from src.domain.value_objects.submitter_type import SubmitterType


@dataclass
class SetSubmitterOutputDTO:
    """提出者設定の結果DTO."""

    success: bool
    message: str
    submitter: ProposalSubmitterDTO | None = None


@dataclass
class ClearSubmitterOutputDTO:
    """提出者クリアの結果DTO."""

    success: bool
    message: str
    deleted_count: int = 0


@dataclass
class UpdateSubmittersOutputDTO:
    """提出者一括更新の結果DTO."""

    success: bool
    message: str
    submitters: list[ProposalSubmitterDTO] | None = None


class ManageProposalSubmitterUseCase:
    """議案提出者の手動設定UseCase.

    議案の提出者情報を手動で設定・更新するためのシンプルな操作を提供します。
    """

    def __init__(
        self,
        proposal_repository: ProposalRepository,
        proposal_submitter_repository: ProposalSubmitterRepository,
        meeting_repository: MeetingRepository,
        politician_affiliation_repository: PoliticianAffiliationRepository,
        parliamentary_group_repository: ParliamentaryGroupRepository,
        politician_repository: PoliticianRepository,
    ) -> None:
        """UseCaseを初期化する.

        Args:
            proposal_repository: 議案リポジトリ
            proposal_submitter_repository: 提出者リポジトリ
            meeting_repository: 会議リポジトリ
            politician_affiliation_repository: 政治家所属リポジトリ
            parliamentary_group_repository: 会派リポジトリ
            politician_repository: 政治家リポジトリ
        """
        self.proposal_repository = proposal_repository
        self.proposal_submitter_repository = proposal_submitter_repository
        self.meeting_repository = meeting_repository
        self.politician_affiliation_repository = politician_affiliation_repository
        self.parliamentary_group_repository = parliamentary_group_repository
        self.politician_repository = politician_repository
        self.logger = get_logger(self.__class__.__name__)

    async def set_submitter(
        self,
        proposal_id: int,
        submitter: str,
        submitter_type: SubmitterType,
        submitter_politician_id: int | None = None,
        submitter_parliamentary_group_id: int | None = None,
    ) -> SetSubmitterOutputDTO:
        """議案の提出者情報を設定する.

        Args:
            proposal_id: 議案ID
            submitter: 生の提出者文字列
            submitter_type: 提出者種別
            submitter_politician_id: 議員提出の場合のPolitician ID
            submitter_parliamentary_group_id: 会派提出の場合のParliamentaryGroup ID

        Returns:
            設定結果DTO
        """
        try:
            # 議案の存在確認
            proposal = await self.proposal_repository.get_by_id(proposal_id)
            if not proposal:
                return SetSubmitterOutputDTO(
                    success=False,
                    message=f"議案ID {proposal_id} が見つかりません",
                )

            # バリデーション: submitter_typeとIDの整合性チェック
            validation_result = self._validate_submitter_type_and_ids(
                submitter_type,
                submitter_politician_id,
                submitter_parliamentary_group_id,
            )
            if validation_result is not None:
                return validation_result

            # 議員IDが指定されている場合、存在確認
            if submitter_politician_id is not None:
                politician = await self.politician_repository.get_by_id(
                    submitter_politician_id
                )
                if not politician:
                    return SetSubmitterOutputDTO(
                        success=False,
                        message=f"議員ID {submitter_politician_id} が見つかりません",
                    )

            # 会派IDが指定されている場合、存在確認
            if submitter_parliamentary_group_id is not None:
                parliamentary_group = (
                    await self.parliamentary_group_repository.get_by_id(
                        submitter_parliamentary_group_id
                    )
                )
                if not parliamentary_group:
                    pg_id = submitter_parliamentary_group_id
                    return SetSubmitterOutputDTO(
                        success=False,
                        message=f"会派ID {pg_id} が見つかりません",
                    )

            # 既存の提出者を削除
            await self.proposal_submitter_repository.delete_by_proposal(proposal_id)

            # 新しい提出者を作成
            new_submitter = ProposalSubmitter(
                proposal_id=proposal_id,
                submitter_type=submitter_type,
                politician_id=submitter_politician_id,
                parliamentary_group_id=submitter_parliamentary_group_id,
                raw_name=submitter,
                is_representative=True,
                display_order=0,
            )
            created_submitter = await self.proposal_submitter_repository.create(
                new_submitter
            )

            # DTOに変換
            dto = await self._entity_to_dto(created_submitter)

            return SetSubmitterOutputDTO(
                success=True,
                message="提出者情報を設定しました",
                submitter=dto,
            )

        except Exception as e:
            self.logger.error(f"提出者設定エラー: {e}", exc_info=True)
            return SetSubmitterOutputDTO(
                success=False,
                message=f"設定中にエラーが発生しました: {e!s}",
            )

    async def clear_submitter(self, proposal_id: int) -> ClearSubmitterOutputDTO:
        """提出者情報をクリアする.

        Args:
            proposal_id: 議案ID

        Returns:
            クリア結果DTO
        """
        try:
            # 議案の存在確認
            proposal = await self.proposal_repository.get_by_id(proposal_id)
            if not proposal:
                return ClearSubmitterOutputDTO(
                    success=False,
                    message=f"議案ID {proposal_id} が見つかりません",
                )

            # 提出者を削除
            deleted_count = await self.proposal_submitter_repository.delete_by_proposal(
                proposal_id
            )

            return ClearSubmitterOutputDTO(
                success=True,
                message=(
                    "提出者情報をクリアしました"
                    if deleted_count > 0
                    else "クリアする提出者情報がありませんでした"
                ),
                deleted_count=deleted_count,
            )

        except Exception as e:
            self.logger.error(f"提出者クリアエラー: {e}", exc_info=True)
            return ClearSubmitterOutputDTO(
                success=False,
                message=f"クリア中にエラーが発生しました: {e!s}",
            )

    async def update_submitters(
        self,
        proposal_id: int,
        politician_ids: list[int] | None = None,
        conference_ids: list[int] | None = None,
        parliamentary_group_id: int | None = None,
        other_submitter: tuple[SubmitterType, str] | None = None,
    ) -> UpdateSubmittersOutputDTO:
        """議案の提出者を一括更新する.

        既存の提出者を全て削除し、新しい提出者を作成します。

        Args:
            proposal_id: 議案ID
            politician_ids: 議員IDリスト（複数可）
            conference_ids: 会議体IDリスト（複数可）
            parliamentary_group_id: 会派ID（単一）
            other_submitter: その他の提出者（種別, 名前）

        Returns:
            更新結果DTO
        """
        try:
            # 議案の存在確認
            proposal = await self.proposal_repository.get_by_id(proposal_id)
            if not proposal:
                return UpdateSubmittersOutputDTO(
                    success=False,
                    message=f"議案ID {proposal_id} が見つかりません",
                )

            # 既存の提出者を削除
            await self.proposal_submitter_repository.delete_by_proposal(proposal_id)

            # 提出者が指定されていない場合
            has_submitters = (
                politician_ids
                or conference_ids
                or parliamentary_group_id
                or other_submitter
            )
            if not has_submitters:
                return UpdateSubmittersOutputDTO(
                    success=True,
                    message="提出者をクリアしました",
                    submitters=[],
                )

            # 新しい提出者エンティティを作成
            submitters: list[ProposalSubmitter] = []
            display_order = 0

            # 議員提出者を追加
            for idx, politician_id in enumerate(politician_ids or []):
                # 議員の存在確認
                politician = await self.politician_repository.get_by_id(politician_id)
                if not politician:
                    self.logger.warning(f"議員ID {politician_id} が見つかりません")
                    continue

                submitter = ProposalSubmitter(
                    proposal_id=proposal_id,
                    submitter_type=SubmitterType.POLITICIAN,
                    politician_id=politician_id,
                    is_representative=(idx == 0),  # 最初の議員が代表
                    display_order=display_order,
                )
                submitters.append(submitter)
                display_order += 1

            # 会議体提出者を追加
            for conference_id in conference_ids or []:
                submitter = ProposalSubmitter(
                    proposal_id=proposal_id,
                    submitter_type=SubmitterType.CONFERENCE,
                    conference_id=conference_id,
                    is_representative=False,
                    display_order=display_order,
                )
                submitters.append(submitter)
                display_order += 1

            # 会派提出者を追加
            if parliamentary_group_id:
                # 会派の存在確認
                parliamentary_group = (
                    await self.parliamentary_group_repository.get_by_id(
                        parliamentary_group_id
                    )
                )
                if not parliamentary_group:
                    return UpdateSubmittersOutputDTO(
                        success=False,
                        message=f"会派ID {parliamentary_group_id} が見つかりません",
                    )

                submitter = ProposalSubmitter(
                    proposal_id=proposal_id,
                    submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
                    parliamentary_group_id=parliamentary_group_id,
                    is_representative=True,
                    display_order=display_order,
                )
                submitters.append(submitter)
                display_order += 1

            # その他の提出者を追加（市長、委員会など）
            if other_submitter:
                submitter_type, raw_name = other_submitter
                submitter = ProposalSubmitter(
                    proposal_id=proposal_id,
                    submitter_type=submitter_type,
                    raw_name=raw_name,
                    is_representative=True,
                    display_order=display_order,
                )
                submitters.append(submitter)

            # 一括作成
            created_submitters = await self.proposal_submitter_repository.bulk_create(
                submitters
            )

            # DTOに変換
            submitter_dtos = [await self._entity_to_dto(s) for s in created_submitters]

            return UpdateSubmittersOutputDTO(
                success=True,
                message=f"{len(submitter_dtos)}件の提出者を登録しました",
                submitters=submitter_dtos,
            )

        except Exception as e:
            self.logger.error(f"提出者更新エラー: {e}", exc_info=True)
            return UpdateSubmittersOutputDTO(
                success=False,
                message=f"更新中にエラーが発生しました: {e!s}",
            )

    async def get_submitter_candidates(
        self, conference_id: int
    ) -> SubmitterCandidatesDTO:
        """会議体に所属する議員/会派の候補一覧を取得する.

        Args:
            conference_id: 会議体ID

        Returns:
            提出者候補一覧DTO
        """
        # 会派一覧を取得
        parliamentary_groups = (
            await self.parliamentary_group_repository.get_by_conference_id(
                conference_id, active_only=True
            )
        )
        parliamentary_group_candidates = [
            ParliamentaryGroupCandidateDTO(
                id=pg.id,
                name=pg.name,
            )
            for pg in parliamentary_groups
            if pg.id is not None
        ]

        # 所属議員一覧を取得
        affiliations = await self.politician_affiliation_repository.get_by_conference(
            conference_id, active_only=True
        )

        # 議員名を取得してDTOに変換
        politician_candidates: list[PoliticianCandidateDTO] = []
        for affiliation in affiliations:
            politician = await self.politician_repository.get_by_id(
                affiliation.politician_id
            )
            if politician and politician.id is not None:
                politician_candidates.append(
                    PoliticianCandidateDTO(
                        id=politician.id,
                        name=politician.name,
                    )
                )

        return SubmitterCandidatesDTO(
            conference_id=conference_id,
            politicians=politician_candidates,
            parliamentary_groups=parliamentary_group_candidates,
        )

    def _validate_submitter_type_and_ids(
        self,
        submitter_type: SubmitterType,
        submitter_politician_id: int | None,
        submitter_parliamentary_group_id: int | None,
    ) -> SetSubmitterOutputDTO | None:
        """submitter_typeとIDの整合性を検証する.

        Args:
            submitter_type: 提出者種別
            submitter_politician_id: 議員ID
            submitter_parliamentary_group_id: 会派ID

        Returns:
            エラーがあればSetSubmitterOutputDTO、なければNone
        """
        if submitter_type == SubmitterType.POLITICIAN:
            if submitter_politician_id is None:
                return SetSubmitterOutputDTO(
                    success=False,
                    message="議員提出の場合はsubmitter_politician_idが必須です",
                )
            if submitter_parliamentary_group_id is not None:
                return SetSubmitterOutputDTO(
                    success=False,
                    message=(
                        "議員提出の場合はsubmitter_parliamentary_group_idを"
                        "指定できません"
                    ),
                )

        elif submitter_type == SubmitterType.PARLIAMENTARY_GROUP:
            if submitter_parliamentary_group_id is None:
                return SetSubmitterOutputDTO(
                    success=False,
                    message=(
                        "会派提出の場合はsubmitter_parliamentary_group_idが必須です"
                    ),
                )
            if submitter_politician_id is not None:
                return SetSubmitterOutputDTO(
                    success=False,
                    message=("会派提出の場合はsubmitter_politician_idを指定できません"),
                )

        else:
            # MAYOR, COMMITTEE, OTHERの場合はIDは不要
            if submitter_politician_id is not None:
                return SetSubmitterOutputDTO(
                    success=False,
                    message=(
                        f"{submitter_type.value}の場合は"
                        "submitter_politician_idを指定できません"
                    ),
                )
            if submitter_parliamentary_group_id is not None:
                return SetSubmitterOutputDTO(
                    success=False,
                    message=(
                        f"{submitter_type.value}の場合は"
                        "submitter_parliamentary_group_idを指定できません"
                    ),
                )

        return None

    async def _entity_to_dto(self, entity: ProposalSubmitter) -> ProposalSubmitterDTO:
        """エンティティをDTOに変換する.

        Args:
            entity: 提出者エンティティ

        Returns:
            提出者DTO
        """
        from datetime import UTC, datetime

        # 議員名を取得
        politician_name: str | None = None
        if entity.politician_id is not None:
            politician = await self.politician_repository.get_by_id(
                entity.politician_id
            )
            if politician:
                politician_name = politician.name

        # 会派名を取得
        parliamentary_group_name: str | None = None
        if entity.parliamentary_group_id is not None:
            parliamentary_group = await self.parliamentary_group_repository.get_by_id(
                entity.parliamentary_group_id
            )
            if parliamentary_group:
                parliamentary_group_name = parliamentary_group.name

        now = datetime.now(UTC)

        return ProposalSubmitterDTO(
            id=entity.id or 0,
            proposal_id=entity.proposal_id,
            submitter_type=entity.submitter_type.value,
            politician_id=entity.politician_id,
            politician_name=politician_name,
            parliamentary_group_id=entity.parliamentary_group_id,
            parliamentary_group_name=parliamentary_group_name,
            raw_name=entity.raw_name,
            is_representative=entity.is_representative,
            display_order=entity.display_order,
            created_at=now,
            updated_at=now,
        )
