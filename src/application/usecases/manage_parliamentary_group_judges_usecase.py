"""会派/政治家賛否情報の手動管理UseCase.

会派単位・政治家単位の賛否情報を手動で登録・編集・削除するためのシンプルなCRUD操作を提供します。
Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from src.application.dtos.proposal_parliamentary_group_judge_dto import (
    ProposalParliamentaryGroupJudgeDTO,
    ProposalParliamentaryGroupJudgeListOutputDTO,
)
from src.common.logging import get_logger
from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.proposal_parliamentary_group_judge_repository import (
    ProposalParliamentaryGroupJudgeRepository,
)
from src.domain.value_objects.judge_type import JudgeType


VALID_JUDGMENTS = {"賛成", "反対", "棄権", "欠席"}


@dataclass
class CreateJudgeOutputDTO:
    """会派/政治家賛否作成の結果DTO."""

    success: bool
    message: str
    judge: ProposalParliamentaryGroupJudgeDTO | None = None


@dataclass
class UpdateJudgeOutputDTO:
    """会派/政治家賛否更新の結果DTO."""

    success: bool
    message: str
    judge: ProposalParliamentaryGroupJudgeDTO | None = None


@dataclass
class DeleteJudgeOutputDTO:
    """会派/政治家賛否削除の結果DTO."""

    success: bool
    message: str


class ManageParliamentaryGroupJudgesUseCase:
    """会派/政治家賛否情報の手動管理UseCase.

    会派単位・政治家単位の賛否情報を手動で登録・編集・削除するためのCRUD操作を提供します。
    Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。
    """

    def __init__(
        self,
        judge_repository: ProposalParliamentaryGroupJudgeRepository,
        parliamentary_group_repository: ParliamentaryGroupRepository,
        politician_repository: PoliticianRepository | None = None,
    ) -> None:
        """UseCaseを初期化する.

        Args:
            judge_repository: 会派/政治家賛否リポジトリ
            parliamentary_group_repository: 会派リポジトリ（会派名取得用）
            politician_repository: 政治家リポジトリ（政治家名取得用、オプション）
        """
        self.judge_repository = judge_repository
        self.parliamentary_group_repository = parliamentary_group_repository
        self.politician_repository = politician_repository
        self.logger = get_logger(self.__class__.__name__)

    async def create(
        self,
        proposal_id: int,
        judgment: str,
        judge_type: str = "parliamentary_group",
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
        member_count: int | None = None,
        note: str | None = None,
    ) -> CreateJudgeOutputDTO:
        """会派/政治家賛否を新規登録する.

        Args:
            proposal_id: 議案ID
            judgment: 賛否判断（賛成/反対/棄権/欠席）
            judge_type: 賛否の種別（parliamentary_group/politician）
            parliamentary_group_ids: 会派IDのリスト（会派単位の場合に必須）
            politician_ids: 政治家IDのリスト（政治家単位の場合に必須）
            member_count: この判断をした会派メンバーの人数（会派単位の場合に使用）
            note: 備考（自由投票など特記事項）

        Returns:
            作成結果DTO
        """
        try:
            if judgment not in VALID_JUDGMENTS:
                valid_values = ", ".join(VALID_JUDGMENTS)
                return CreateJudgeOutputDTO(
                    success=False,
                    message=f"無効なjudgment値です。有効な値: {valid_values}",
                )

            judge_type_enum = JudgeType(judge_type)
            pg_ids = parliamentary_group_ids or []
            pol_ids = politician_ids or []

            validation_result = await self._validate_judge_type_and_ids(
                judge_type_enum, pg_ids, pol_ids
            )
            if validation_result:
                return validation_result

            duplicate_result = await self._check_duplicate(
                proposal_id, judge_type_enum, pg_ids, pol_ids
            )
            if duplicate_result:
                return duplicate_result

            is_pg = judge_type_enum == JudgeType.PARLIAMENTARY_GROUP
            entity = ProposalParliamentaryGroupJudge(
                proposal_id=proposal_id,
                judgment=judgment,
                judge_type=judge_type_enum,
                parliamentary_group_ids=pg_ids,
                politician_ids=pol_ids,
                member_count=member_count if is_pg else None,
                note=note,
            )

            created = await self.judge_repository.create(entity)
            dto = await self._entity_to_dto(created)

            return CreateJudgeOutputDTO(
                success=True,
                message="賛否情報を作成しました",
                judge=dto,
            )

        except ValueError as e:
            return CreateJudgeOutputDTO(
                success=False,
                message=f"無効なjudge_type値です: {e!s}",
            )
        except Exception as e:
            self.logger.error(f"賛否作成エラー: {e}", exc_info=True)
            return CreateJudgeOutputDTO(
                success=False,
                message=f"作成中にエラーが発生しました: {e!s}",
            )

    async def _validate_judge_type_and_ids(
        self,
        judge_type: JudgeType,
        parliamentary_group_ids: list[int],
        politician_ids: list[int],
    ) -> CreateJudgeOutputDTO | None:
        """賛否種別とIDの組み合わせを検証する."""
        if judge_type == JudgeType.PARLIAMENTARY_GROUP:
            if not parliamentary_group_ids:
                return CreateJudgeOutputDTO(
                    success=False,
                    message="会派単位の賛否には会派IDが必要です",
                )
            # すべての会派IDが存在するか確認
            for pg_id in parliamentary_group_ids:
                parliamentary_group = (
                    await self.parliamentary_group_repository.get_by_id(pg_id)
                )
                if not parliamentary_group:
                    return CreateJudgeOutputDTO(
                        success=False,
                        message=f"会派ID {pg_id} が見つかりません",
                    )
        elif judge_type == JudgeType.POLITICIAN:
            if not politician_ids:
                return CreateJudgeOutputDTO(
                    success=False,
                    message="政治家単位の賛否には政治家IDが必要です",
                )
            # すべての政治家IDが存在するか確認
            if self.politician_repository:
                for pol_id in politician_ids:
                    politician = await self.politician_repository.get_by_id(pol_id)
                    if not politician:
                        return CreateJudgeOutputDTO(
                            success=False,
                            message=f"政治家ID {pol_id} が見つかりません",
                        )
        return None

    async def _check_duplicate(
        self,
        proposal_id: int,
        judge_type: JudgeType,
        parliamentary_group_ids: list[int],
        politician_ids: list[int],
    ) -> CreateJudgeOutputDTO | None:
        """重複チェックを行う."""
        if judge_type == JudgeType.PARLIAMENTARY_GROUP and parliamentary_group_ids:
            existing = await self.judge_repository.get_by_proposal_and_groups(
                proposal_id, parliamentary_group_ids
            )
            if existing:
                pg_ids_str = ",".join(map(str, parliamentary_group_ids))
                return CreateJudgeOutputDTO(
                    success=False,
                    message=(
                        f"議案ID {proposal_id} と会派ID [{pg_ids_str}] "
                        "の組み合わせは既に登録されています"
                    ),
                )
        elif judge_type == JudgeType.POLITICIAN and politician_ids:
            existing = await self.judge_repository.get_by_proposal_and_politicians(
                proposal_id, politician_ids
            )
            if existing:
                pol_ids_str = ",".join(map(str, politician_ids))
                return CreateJudgeOutputDTO(
                    success=False,
                    message=(
                        f"議案ID {proposal_id} と政治家ID [{pol_ids_str}] "
                        "の組み合わせは既に登録されています"
                    ),
                )
        return None

    async def update(
        self,
        judge_id: int,
        judgment: str | None = None,
        member_count: int | None = None,
        note: str | None = None,
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
    ) -> UpdateJudgeOutputDTO:
        """会派/政治家賛否を更新する.

        Args:
            judge_id: 賛否ID
            judgment: 賛否判断（賛成/反対/棄権/欠席）
            member_count: この判断をした会派メンバーの人数（会派単位の場合に使用）
            note: 備考（自由投票など特記事項）
            parliamentary_group_ids: 紐付ける会派IDのリスト（Noneの場合は変更しない）
            politician_ids: 紐付ける政治家IDのリスト（Noneの場合は変更しない）

        Returns:
            更新結果DTO
        """
        try:
            existing = await self.judge_repository.get_by_id(judge_id)
            if not existing:
                return UpdateJudgeOutputDTO(
                    success=False,
                    message=f"賛否ID {judge_id} が見つかりません",
                )

            if judgment is not None and judgment not in VALID_JUDGMENTS:
                valid_values = ", ".join(VALID_JUDGMENTS)
                return UpdateJudgeOutputDTO(
                    success=False,
                    message=f"無効なjudgment値です。有効な値: {valid_values}",
                )

            if judgment is not None:
                existing.judgment = judgment
            if member_count is not None:
                existing.member_count = member_count
            if note is not None:
                existing.note = note
            if parliamentary_group_ids is not None:
                existing.parliamentary_group_ids = parliamentary_group_ids
            if politician_ids is not None:
                existing.politician_ids = politician_ids

            updated = await self.judge_repository.update(existing)
            dto = await self._entity_to_dto(updated)

            return UpdateJudgeOutputDTO(
                success=True,
                message="賛否情報を更新しました",
                judge=dto,
            )

        except Exception as e:
            self.logger.error(f"賛否更新エラー: {e}", exc_info=True)
            return UpdateJudgeOutputDTO(
                success=False,
                message=f"更新中にエラーが発生しました: {e!s}",
            )

    async def delete(self, judge_id: int) -> DeleteJudgeOutputDTO:
        """会派/政治家賛否を削除する.

        Args:
            judge_id: 賛否ID

        Returns:
            削除結果DTO
        """
        try:
            existing = await self.judge_repository.get_by_id(judge_id)
            if not existing:
                return DeleteJudgeOutputDTO(
                    success=False,
                    message=f"賛否ID {judge_id} が見つかりません",
                )

            success = await self.judge_repository.delete(judge_id)

            if success:
                return DeleteJudgeOutputDTO(
                    success=True,
                    message="賛否情報を削除しました",
                )
            else:
                return DeleteJudgeOutputDTO(
                    success=False,
                    message="削除に失敗しました",
                )

        except Exception as e:
            self.logger.error(f"賛否削除エラー: {e}", exc_info=True)
            return DeleteJudgeOutputDTO(
                success=False,
                message=f"削除中にエラーが発生しました: {e!s}",
            )

    async def list_by_proposal(
        self, proposal_id: int
    ) -> ProposalParliamentaryGroupJudgeListOutputDTO:
        """議案に紐づく会派/政治家賛否一覧を取得する.

        Args:
            proposal_id: 議案ID

        Returns:
            賛否一覧DTO
        """
        try:
            entities = await self.judge_repository.get_by_proposal(proposal_id)

            dtos: list[ProposalParliamentaryGroupJudgeDTO] = []
            for entity in entities:
                dto = await self._entity_to_dto(entity)
                dtos.append(dto)

            return ProposalParliamentaryGroupJudgeListOutputDTO(
                total_count=len(dtos),
                judges=dtos,
            )

        except Exception as e:
            self.logger.error(f"賛否一覧取得エラー: {e}", exc_info=True)
            raise

    async def _entity_to_dto(
        self, entity: ProposalParliamentaryGroupJudge
    ) -> ProposalParliamentaryGroupJudgeDTO:
        """エンティティをDTOに変換する.

        Args:
            entity: 賛否エンティティ

        Returns:
            賛否DTO
        """
        # 会派名を取得
        parliamentary_group_names: list[str] = []
        for pg_id in entity.parliamentary_group_ids:
            parliamentary_group = await self.parliamentary_group_repository.get_by_id(
                pg_id
            )
            if parliamentary_group:
                parliamentary_group_names.append(parliamentary_group.name)
            else:
                parliamentary_group_names.append("（不明）")

        # 政治家名を取得
        politician_names: list[str] = []
        if self.politician_repository:
            for pol_id in entity.politician_ids:
                politician = await self.politician_repository.get_by_id(pol_id)
                if politician:
                    politician_names.append(politician.name)
                else:
                    politician_names.append("（不明）")

        now = datetime.now(UTC)

        return ProposalParliamentaryGroupJudgeDTO(
            id=entity.id or 0,
            proposal_id=entity.proposal_id,
            judge_type=entity.judge_type.value,
            judgment=entity.judgment,
            parliamentary_group_ids=entity.parliamentary_group_ids,
            parliamentary_group_names=parliamentary_group_names,
            politician_ids=entity.politician_ids,
            politician_names=politician_names,
            member_count=entity.member_count,
            note=entity.note,
            created_at=now,
            updated_at=now,
        )
