"""会派賛否情報の手動管理UseCase.

会派単位の賛否情報を手動で登録・編集・削除するためのシンプルなCRUD操作を提供します。
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
from src.domain.repositories.proposal_parliamentary_group_judge_repository import (
    ProposalParliamentaryGroupJudgeRepository,
)


# 有効なjudgment値
VALID_JUDGMENTS = {"賛成", "反対", "棄権", "欠席"}


@dataclass
class CreateJudgeOutputDTO:
    """会派賛否作成の結果DTO."""

    success: bool
    message: str
    judge: ProposalParliamentaryGroupJudgeDTO | None = None


@dataclass
class UpdateJudgeOutputDTO:
    """会派賛否更新の結果DTO."""

    success: bool
    message: str
    judge: ProposalParliamentaryGroupJudgeDTO | None = None


@dataclass
class DeleteJudgeOutputDTO:
    """会派賛否削除の結果DTO."""

    success: bool
    message: str


class ManageParliamentaryGroupJudgesUseCase:
    """会派賛否情報の手動管理UseCase.

    会派単位の賛否情報を手動で登録・編集・削除するためのCRUD操作を提供します。
    """

    def __init__(
        self,
        judge_repository: ProposalParliamentaryGroupJudgeRepository,
        parliamentary_group_repository: ParliamentaryGroupRepository,
    ) -> None:
        """UseCaseを初期化する.

        Args:
            judge_repository: 会派賛否リポジトリ
            parliamentary_group_repository: 会派リポジトリ（会派名取得用）
        """
        self.judge_repository = judge_repository
        self.parliamentary_group_repository = parliamentary_group_repository
        self.logger = get_logger(self.__class__.__name__)

    async def create(
        self,
        proposal_id: int,
        parliamentary_group_id: int,
        judgment: str,
        member_count: int | None = None,
        note: str | None = None,
    ) -> CreateJudgeOutputDTO:
        """会派賛否を新規登録する.

        Args:
            proposal_id: 議案ID
            parliamentary_group_id: 会派ID
            judgment: 賛否判断（賛成/反対/棄権/欠席）
            member_count: この判断をした会派メンバーの人数
            note: 備考（自由投票など特記事項）

        Returns:
            作成結果DTO
        """
        try:
            # judgment値の検証
            if judgment not in VALID_JUDGMENTS:
                valid_values = ", ".join(VALID_JUDGMENTS)
                return CreateJudgeOutputDTO(
                    success=False,
                    message=f"無効なjudgment値です。有効な値: {valid_values}",
                )

            # 会派の存在確認
            parliamentary_group = await self.parliamentary_group_repository.get_by_id(
                parliamentary_group_id
            )
            if not parliamentary_group:
                return CreateJudgeOutputDTO(
                    success=False,
                    message=f"会派ID {parliamentary_group_id} が見つかりません",
                )

            # 重複チェック（同一議案・同一会派）
            existing = await self.judge_repository.get_by_proposal_and_group(
                proposal_id, parliamentary_group_id
            )
            if existing:
                return CreateJudgeOutputDTO(
                    success=False,
                    message=(
                        f"議案ID {proposal_id} と会派ID {parliamentary_group_id} "
                        "の組み合わせは既に登録されています"
                    ),
                )

            # エンティティ作成
            entity = ProposalParliamentaryGroupJudge(
                proposal_id=proposal_id,
                parliamentary_group_id=parliamentary_group_id,
                judgment=judgment,
                member_count=member_count,
                note=note,
            )

            # 保存
            created = await self.judge_repository.create(entity)

            # DTOに変換
            dto = await self._entity_to_dto(created)

            return CreateJudgeOutputDTO(
                success=True,
                message="会派賛否を作成しました",
                judge=dto,
            )

        except Exception as e:
            self.logger.error(f"会派賛否作成エラー: {e}", exc_info=True)
            return CreateJudgeOutputDTO(
                success=False,
                message=f"作成中にエラーが発生しました: {e!s}",
            )

    async def update(
        self,
        judge_id: int,
        judgment: str | None = None,
        member_count: int | None = None,
        note: str | None = None,
    ) -> UpdateJudgeOutputDTO:
        """会派賛否を更新する.

        Args:
            judge_id: 会派賛否ID
            judgment: 賛否判断（賛成/反対/棄権/欠席）
            member_count: この判断をした会派メンバーの人数
            note: 備考（自由投票など特記事項）

        Returns:
            更新結果DTO
        """
        try:
            # 対象の存在確認
            existing = await self.judge_repository.get_by_id(judge_id)
            if not existing:
                return UpdateJudgeOutputDTO(
                    success=False,
                    message=f"会派賛否ID {judge_id} が見つかりません",
                )

            # judgment値の検証（指定された場合のみ）
            if judgment is not None and judgment not in VALID_JUDGMENTS:
                valid_values = ", ".join(VALID_JUDGMENTS)
                return UpdateJudgeOutputDTO(
                    success=False,
                    message=f"無効なjudgment値です。有効な値: {valid_values}",
                )

            # フィールドを更新
            if judgment is not None:
                existing.judgment = judgment
            if member_count is not None:
                existing.member_count = member_count
            if note is not None:
                existing.note = note

            # 保存
            updated = await self.judge_repository.update(existing)

            # DTOに変換
            dto = await self._entity_to_dto(updated)

            return UpdateJudgeOutputDTO(
                success=True,
                message="会派賛否を更新しました",
                judge=dto,
            )

        except Exception as e:
            self.logger.error(f"会派賛否更新エラー: {e}", exc_info=True)
            return UpdateJudgeOutputDTO(
                success=False,
                message=f"更新中にエラーが発生しました: {e!s}",
            )

    async def delete(self, judge_id: int) -> DeleteJudgeOutputDTO:
        """会派賛否を削除する.

        Args:
            judge_id: 会派賛否ID

        Returns:
            削除結果DTO
        """
        try:
            # 対象の存在確認
            existing = await self.judge_repository.get_by_id(judge_id)
            if not existing:
                return DeleteJudgeOutputDTO(
                    success=False,
                    message=f"会派賛否ID {judge_id} が見つかりません",
                )

            # 削除
            success = await self.judge_repository.delete(judge_id)

            if success:
                return DeleteJudgeOutputDTO(
                    success=True,
                    message="会派賛否を削除しました",
                )
            else:
                return DeleteJudgeOutputDTO(
                    success=False,
                    message="削除に失敗しました",
                )

        except Exception as e:
            self.logger.error(f"会派賛否削除エラー: {e}", exc_info=True)
            return DeleteJudgeOutputDTO(
                success=False,
                message=f"削除中にエラーが発生しました: {e!s}",
            )

    async def list_by_proposal(
        self, proposal_id: int
    ) -> ProposalParliamentaryGroupJudgeListOutputDTO:
        """議案に紐づく会派賛否一覧を取得する.

        Args:
            proposal_id: 議案ID

        Returns:
            会派賛否一覧DTO
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
            self.logger.error(f"会派賛否一覧取得エラー: {e}", exc_info=True)
            raise

    async def _entity_to_dto(
        self, entity: ProposalParliamentaryGroupJudge
    ) -> ProposalParliamentaryGroupJudgeDTO:
        """エンティティをDTOに変換する.

        Args:
            entity: 会派賛否エンティティ

        Returns:
            会派賛否DTO
        """
        # 会派名を取得
        parliamentary_group = await self.parliamentary_group_repository.get_by_id(
            entity.parliamentary_group_id
        )
        parliamentary_group_name = (
            parliamentary_group.name if parliamentary_group else "（不明）"
        )

        # created_at/updated_atはリポジトリから取得できないため、現在時刻を使用
        # 実際の運用ではリポジトリからtimestamp情報を返す必要がある
        now = datetime.now(UTC)

        return ProposalParliamentaryGroupJudgeDTO(
            id=entity.id or 0,
            proposal_id=entity.proposal_id,
            parliamentary_group_id=entity.parliamentary_group_id,
            parliamentary_group_name=parliamentary_group_name,
            judgment=entity.judgment,
            member_count=entity.member_count,
            note=entity.note,
            created_at=now,
            updated_at=now,
        )
