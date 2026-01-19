"""Use case for managing politicians.

Issue #969: UseCase層のリファクタリング
- DTO定義を politician_dto.py に分離
- 後方互換性のため、本モジュールからもre-export
"""

from typing import Any
from uuid import UUID

from src.application.dtos.politician_dto import (
    CreatePoliticianInputDto,
    CreatePoliticianOutputDto,
    DeletePoliticianInputDto,
    DeletePoliticianOutputDto,
    MergePoliticiansInputDto,
    MergePoliticiansOutputDto,
    PoliticianListInputDto,
    PoliticianListOutputDto,
    UpdatePoliticianInputDto,
    UpdatePoliticianOutputDto,
)
from src.common.logging import get_logger
from src.domain.entities import Politician
from src.domain.entities.politician_operation_log import (
    PoliticianOperationLog,
    PoliticianOperationType,
)
from src.domain.repositories.politician_operation_log_repository import (
    PoliticianOperationLogRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository


logger = get_logger(__name__)


# 後方互換性のため、DTOをre-export（既存のimport文が動作するように）
__all__ = [
    "ManagePoliticiansUseCase",
    "PoliticianListInputDto",
    "PoliticianListOutputDto",
    "CreatePoliticianInputDto",
    "CreatePoliticianOutputDto",
    "UpdatePoliticianInputDto",
    "UpdatePoliticianOutputDto",
    "DeletePoliticianInputDto",
    "DeletePoliticianOutputDto",
    "MergePoliticiansInputDto",
    "MergePoliticiansOutputDto",
]


class ManagePoliticiansUseCase:
    """Use case for managing politicians."""

    def __init__(
        self,
        politician_repository: PoliticianRepository,
        operation_log_repository: PoliticianOperationLogRepository | None = None,
    ):
        """Initialize the use case.

        Args:
            politician_repository: Repository instance (can be sync or async)
            operation_log_repository: Optional repository for operation logs
        """
        self.politician_repository = politician_repository
        self.operation_log_repository = operation_log_repository

    async def _log_operation(
        self,
        politician_id: int,
        politician_name: str,
        operation_type: PoliticianOperationType,
        user_id: UUID | None,
        details: dict[str, Any],
    ) -> None:
        """操作ログを記録する.

        Args:
            politician_id: 政治家ID
            politician_name: 政治家名
            operation_type: 操作種別
            user_id: 操作ユーザーID
            details: 操作詳細
        """
        if not self.operation_log_repository:
            return

        try:
            log = PoliticianOperationLog(
                politician_id=politician_id,
                politician_name=politician_name,
                operation_type=operation_type,
                user_id=user_id,
                operation_details=details,
            )
            await self.operation_log_repository.create(log)
            logger.info(
                f"操作ログ記録: politician_id={politician_id}, "
                f"operation_type={operation_type.value}, user_id={user_id}"
            )
        except Exception as e:
            # ログ記録失敗は主要操作に影響させない
            logger.warning(f"操作ログの記録に失敗: {e}")

    async def list_politicians(
        self, input_dto: PoliticianListInputDto
    ) -> PoliticianListOutputDto:
        """List politicians with optional filters."""
        try:
            if input_dto.search_name:
                politicians = await self.politician_repository.search_by_name(
                    input_dto.search_name
                )
            elif input_dto.party_id:
                politicians = await self.politician_repository.get_by_party(
                    input_dto.party_id
                )
            else:
                politicians = await self.politician_repository.get_all()

            return PoliticianListOutputDto(politicians=politicians)
        except Exception as e:
            logger.error(f"Failed to list politicians: {e}")
            raise

    async def create_politician(
        self, input_dto: CreatePoliticianInputDto
    ) -> CreatePoliticianOutputDto:
        """Create a new politician."""
        try:
            # Check for duplicates
            existing = await self.politician_repository.get_by_name_and_party(
                input_dto.name, input_dto.party_id
            )
            if existing:
                return CreatePoliticianOutputDto(
                    success=False,
                    error_message="同じ名前と政党の政治家が既に存在します。",
                )

            # Create new politician
            politician = Politician(
                id=0,  # Will be assigned by database
                name=input_dto.name,
                prefecture=input_dto.prefecture,
                political_party_id=input_dto.party_id,
                district=input_dto.district,
                profile_page_url=input_dto.profile_url,
            )

            created = await self.politician_repository.create(politician)

            # 操作ログを記録
            if created.id:
                await self._log_operation(
                    politician_id=created.id,
                    politician_name=input_dto.name,
                    operation_type=PoliticianOperationType.CREATE,
                    user_id=input_dto.user_id,
                    details={
                        "prefecture": input_dto.prefecture,
                        "district": input_dto.district,
                        "party_id": input_dto.party_id,
                        "profile_url": input_dto.profile_url,
                    },
                )

            return CreatePoliticianOutputDto(success=True, politician_id=created.id)
        except Exception as e:
            logger.error(f"Failed to create politician: {e}")
            return CreatePoliticianOutputDto(success=False, error_message=str(e))

    async def update_politician(
        self, input_dto: UpdatePoliticianInputDto
    ) -> UpdatePoliticianOutputDto:
        """Update an existing politician."""
        try:
            # Get existing politician
            existing = await self.politician_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdatePoliticianOutputDto(
                    success=False, error_message="政治家が見つかりません。"
                )

            # Update fields
            existing.name = input_dto.name
            existing.prefecture = input_dto.prefecture
            existing.political_party_id = input_dto.party_id
            existing.district = input_dto.district
            existing.profile_page_url = input_dto.profile_url

            await self.politician_repository.update(existing)

            # 操作ログを記録
            await self._log_operation(
                politician_id=input_dto.id,
                politician_name=input_dto.name,
                operation_type=PoliticianOperationType.UPDATE,
                user_id=input_dto.user_id,
                details={
                    "prefecture": input_dto.prefecture,
                    "district": input_dto.district,
                    "party_id": input_dto.party_id,
                    "profile_url": input_dto.profile_url,
                },
            )

            return UpdatePoliticianOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update politician: {e}")
            return UpdatePoliticianOutputDto(success=False, error_message=str(e))

    async def delete_politician(
        self, input_dto: DeletePoliticianInputDto
    ) -> DeletePoliticianOutputDto:
        """Delete a politician.

        関連データがある場合:
        - force=Falseの場合: 警告情報を返し、削除は実行しない
        - force=Trueの場合: 関連データを削除・解除してから削除を実行
        """
        try:
            # Check if politician exists
            existing = await self.politician_repository.get_by_id(input_dto.id)
            if not existing:
                return DeletePoliticianOutputDto(
                    success=False, error_message="政治家が見つかりません。"
                )

            # 削除前に政治家名を保存
            politician_name = existing.name

            # 関連データの件数を確認
            related_counts = await self.politician_repository.get_related_data_counts(
                input_dto.id
            )
            total_related = sum(related_counts.values())

            # 関連データがある場合の処理
            if total_related > 0:
                # force=Falseの場合は警告を返す
                if not input_dto.force:
                    # 件数があるテーブルのみをフィルタリング
                    non_zero_counts = {k: v for k, v in related_counts.items() if v > 0}
                    return DeletePoliticianOutputDto(
                        success=False,
                        error_message=(
                            f"この政治家には関連データが{total_related}件あります。"
                            "削除するには関連データの解除・削除が必要です。"
                        ),
                        has_related_data=True,
                        related_data_counts=non_zero_counts,
                    )

                # force=Trueの場合は関連データを削除・解除
                deleted_counts = await self.politician_repository.delete_related_data(
                    input_dto.id
                )
                logger.info(
                    f"Deleted/unlinked related data for politician {input_dto.id}: "
                    f"{deleted_counts}"
                )

            # 政治家を削除
            await self.politician_repository.delete(input_dto.id)

            # 操作ログを記録
            await self._log_operation(
                politician_id=input_dto.id,
                politician_name=politician_name,
                operation_type=PoliticianOperationType.DELETE,
                user_id=input_dto.user_id,
                details={
                    "deleted_related_data": related_counts if total_related > 0 else {},
                },
            )

            return DeletePoliticianOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to delete politician: {e}")
            return DeletePoliticianOutputDto(success=False, error_message=str(e))

    async def merge_politicians(
        self, input_dto: MergePoliticiansInputDto
    ) -> MergePoliticiansOutputDto:
        """Merge two politicians."""
        try:
            # Check if both politicians exist
            source = await self.politician_repository.get_by_id(input_dto.source_id)
            target = await self.politician_repository.get_by_id(input_dto.target_id)

            if not source:
                return MergePoliticiansOutputDto(
                    success=False, error_message="マージ元の政治家が見つかりません。"
                )
            if not target:
                return MergePoliticiansOutputDto(
                    success=False, error_message="マージ先の政治家が見つかりません。"
                )

            # マージ機能は現時点では不要と判断し、未実装のまま
            return MergePoliticiansOutputDto(
                success=False, error_message="マージ機能は現在実装されていません。"
            )
        except Exception as e:
            logger.error(f"Failed to merge politicians: {e}")
            return MergePoliticiansOutputDto(success=False, error_message=str(e))
