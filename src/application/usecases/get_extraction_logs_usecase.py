"""抽出ログ取得ユースケースモジュール。

このモジュールは、抽出ログの検索・統計情報取得のユースケースを提供します。
"""

import logging

from datetime import datetime, timedelta

from src.application.dtos.extraction_log_dto import (
    DailyCountDTO,
    ExtractionLogFilterDTO,
    ExtractionStatisticsDTO,
    PaginatedExtractionLogsDTO,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.repositories.extraction_log_repository import ExtractionLogRepository


logger = logging.getLogger(__name__)


class GetExtractionLogsUseCase:
    """抽出ログ取得ユースケース。

    抽出ログの検索・統計情報を取得するユースケースを提供します。
    """

    def __init__(self, extraction_log_repository: ExtractionLogRepository) -> None:
        """ユースケースを初期化する。

        Args:
            extraction_log_repository: 抽出ログリポジトリ
        """
        self.extraction_log_repository = extraction_log_repository

    async def execute(
        self, filter_dto: ExtractionLogFilterDTO
    ) -> PaginatedExtractionLogsDTO:
        """抽出ログを検索する。

        Args:
            filter_dto: 検索フィルター

        Returns:
            ページネーション付き抽出ログ
        """
        try:
            # 検索実行
            logs = await self.extraction_log_repository.search_with_date_range(
                entity_type=filter_dto.entity_type,
                entity_id=filter_dto.entity_id,
                pipeline_version=filter_dto.pipeline_version,
                min_confidence_score=filter_dto.min_confidence_score,
                date_from=filter_dto.date_from,
                date_to=filter_dto.date_to,
                limit=filter_dto.limit,
                offset=filter_dto.offset,
            )

            # 総件数取得
            total_count = await self.extraction_log_repository.count_with_filters(
                entity_type=filter_dto.entity_type,
                entity_id=filter_dto.entity_id,
                pipeline_version=filter_dto.pipeline_version,
                min_confidence_score=filter_dto.min_confidence_score,
                date_from=filter_dto.date_from,
                date_to=filter_dto.date_to,
            )

            return PaginatedExtractionLogsDTO(
                logs=logs,
                total_count=total_count,
                page_size=filter_dto.limit,
                current_offset=filter_dto.offset,
            )

        except Exception as e:
            logger.error(f"抽出ログの検索中にエラーが発生しました: {e}")
            return PaginatedExtractionLogsDTO(
                logs=[],
                total_count=0,
                page_size=filter_dto.limit,
                current_offset=filter_dto.offset,
            )

    async def get_statistics(
        self,
        entity_type: EntityType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ExtractionStatisticsDTO:
        """抽出統計情報を取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            date_from: 検索開始日時
            date_to: 検索終了日時

        Returns:
            抽出統計情報
        """
        try:
            # デフォルトの日付範囲（過去30日）
            if not date_from:
                date_from = datetime.now() - timedelta(days=30)
            if not date_to:
                date_to = datetime.now()

            # 総件数取得
            total_count = await self.extraction_log_repository.count_with_filters(
                entity_type=entity_type,
                date_from=date_from,
                date_to=date_to,
            )

            # エンティティタイプ別件数
            by_entity_type: dict[str, int] = {}
            for et in EntityType:
                count = await self.extraction_log_repository.count_with_filters(
                    entity_type=et,
                    date_from=date_from,
                    date_to=date_to,
                )
                if count > 0:
                    by_entity_type[et.value] = count

            # パイプラインバージョン一覧取得
            pipeline_versions = (
                await self.extraction_log_repository.get_distinct_pipeline_versions()
            )

            # パイプラインバージョン別件数と平均信頼度
            by_pipeline_version: dict[str, int] = {}
            confidence_by_pipeline: dict[str, float] = {}

            for version in pipeline_versions:
                count = await self.extraction_log_repository.count_with_filters(
                    entity_type=entity_type,
                    pipeline_version=version,
                    date_from=date_from,
                    date_to=date_to,
                )
                if count > 0:
                    by_pipeline_version[version] = count

                    # パイプラインバージョン別平均信頼度
                    repo = self.extraction_log_repository
                    avg_confidence = await repo.get_average_confidence_score(
                        entity_type=entity_type,
                        pipeline_version=version,
                    )
                    if avg_confidence is not None:
                        confidence_by_pipeline[version] = round(avg_confidence, 3)

            # 全体平均信頼度
            average_confidence = (
                await self.extraction_log_repository.get_average_confidence_score(
                    entity_type=entity_type,
                )
            )

            # 日別件数
            daily_counts_raw = await self.extraction_log_repository.get_count_by_date(
                entity_type=entity_type,
                date_from=date_from,
                date_to=date_to,
            )
            daily_counts = [
                DailyCountDTO(date=dt, count=count) for dt, count in daily_counts_raw
            ]

            return ExtractionStatisticsDTO(
                total_count=total_count,
                by_entity_type=by_entity_type,
                by_pipeline_version=by_pipeline_version,
                average_confidence=round(average_confidence, 3)
                if average_confidence
                else None,
                daily_counts=daily_counts,
                confidence_by_pipeline=confidence_by_pipeline,
            )

        except Exception as e:
            logger.error(f"抽出統計情報の取得中にエラーが発生しました: {e}")
            return ExtractionStatisticsDTO(
                total_count=0,
                by_entity_type={},
                by_pipeline_version={},
                average_confidence=None,
                daily_counts=[],
                confidence_by_pipeline={},
            )

    async def get_by_id(self, log_id: int) -> ExtractionLog | None:
        """IDで抽出ログを取得する。

        Args:
            log_id: 抽出ログID

        Returns:
            抽出ログ、存在しない場合はNone
        """
        try:
            return await self.extraction_log_repository.get_by_id(log_id)
        except Exception as e:
            logger.error(f"抽出ログの取得中にエラーが発生しました: {e}")
            return None

    async def get_by_entity(
        self, entity_type: EntityType, entity_id: int
    ) -> list[ExtractionLog]:
        """特定エンティティの抽出ログを取得する。

        Args:
            entity_type: エンティティタイプ
            entity_id: エンティティID

        Returns:
            抽出ログのリスト
        """
        try:
            return await self.extraction_log_repository.get_by_entity(
                entity_type=entity_type,
                entity_id=entity_id,
            )
        except Exception as e:
            logger.error(f"エンティティの抽出ログ取得中にエラーが発生しました: {e}")
            return []

    async def get_pipeline_versions(self) -> list[str]:
        """パイプラインバージョン一覧を取得する。

        Returns:
            パイプラインバージョンのリスト
        """
        try:
            return await self.extraction_log_repository.get_distinct_pipeline_versions()
        except Exception as e:
            logger.error(
                f"パイプラインバージョン一覧の取得中にエラーが発生しました: {e}"
            )
            return []

    async def get_entity_types(self) -> list[str]:
        """エンティティタイプ一覧を取得する。

        Returns:
            エンティティタイプの値リスト
        """
        return [et.value for et in EntityType]
