"""ユーザー統計取得ユースケースモジュール

このモジュールは、ユーザー別の作業統計を取得するユースケースを提供します。
"""

import logging

from collections import defaultdict
from datetime import date, datetime
from uuid import UUID

from src.application.dtos.user_statistics_dto import (
    ContributorRank,
    TimelineDataPoint,
    UserStatisticsDTO,
)
from src.application.dtos.work_history_dto import WorkType
from src.application.usecases.get_work_history_usecase import GetWorkHistoryUseCase

logger = logging.getLogger(__name__)


class GetUserStatisticsUseCase:
    """ユーザー統計取得ユースケース

    作業履歴データを基に、ユーザー別の統計情報を集計します。
    時系列データや上位貢献者ランキングを含む包括的な統計を提供します。
    """

    def __init__(self, work_history_usecase: GetWorkHistoryUseCase) -> None:
        """ユースケースを初期化する

        Args:
            work_history_usecase: 作業履歴取得ユースケース
        """
        self.work_history_usecase = work_history_usecase

    async def execute(
        self,
        user_id: UUID | None = None,
        work_types: list[WorkType] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        top_n: int = 10,
    ) -> UserStatisticsDTO:
        """ユーザー統計を取得する

        Args:
            user_id: フィルタリング対象のユーザーID
            work_types: フィルタリング対象の作業タイプリスト
            start_date: 開始日時
            end_date: 終了日時
            top_n: 上位貢献者の表示数（デフォルト: 10）

        Returns:
            ユーザー統計情報のDTO
        """
        try:
            # すべての履歴を取得（limit を大きく設定）
            histories = await self.work_history_usecase.execute(
                user_id=user_id,
                work_types=work_types,
                start_date=start_date,
                end_date=end_date,
                limit=100000,  # 統計用に大量取得
            )

            # 基本統計の集計
            total_count = len(histories)
            work_type_counts: dict[str, int] = {}
            user_counts: dict[str, int] = {}
            user_details: dict[str, tuple[str | None, str | None, dict[str, int]]] = {}

            # 時系列データの集計用
            timeline_by_date: dict[tuple[date, WorkType | None], int] = defaultdict(int)

            for history in histories:
                # 作業タイプごとのカウント
                work_type = history.work_type.value
                work_type_counts[work_type] = work_type_counts.get(work_type, 0) + 1

                # ユーザーごとのカウント
                user_key = (
                    f"{history.user_name} ({history.user_email})"
                    if history.user_name
                    else str(history.user_id)
                )
                user_counts[user_key] = user_counts.get(user_key, 0) + 1

                # ユーザー詳細情報の保存（ランキング用）
                if user_key not in user_details:
                    user_details[user_key] = (
                        history.user_name,
                        history.user_email,
                        {},
                    )

                # 作業タイプ別内訳の更新
                breakdown = user_details[user_key][2]
                breakdown[work_type] = breakdown.get(work_type, 0) + 1

                # 時系列データの集計（日別）
                work_date = history.executed_at.date()
                timeline_by_date[(work_date, None)] += 1
                timeline_by_date[(work_date, history.work_type)] += 1

            # 時系列データの作成
            timeline_data = []
            # 全タイプ集計のみを抽出（個別タイプは除外してシンプルに）
            all_type_timeline = {
                date_val: count
                for (date_val, work_type), count in timeline_by_date.items()
                if work_type is None
            }
            for date_val, count in sorted(all_type_timeline.items()):
                timeline_data.append(
                    TimelineDataPoint(date=date_val, count=count, work_type=None)
                )

            # 上位貢献者ランキングの作成
            top_contributors = []
            sorted_users = sorted(
                user_counts.items(), key=lambda x: x[1], reverse=True
            )[:top_n]

            for rank, (user_key, total_works) in enumerate(sorted_users, start=1):
                user_name, user_email, breakdown = user_details[user_key]
                top_contributors.append(
                    ContributorRank(
                        rank=rank,
                        user_name=user_name,
                        user_email=user_email,
                        total_works=total_works,
                        work_type_breakdown=breakdown,
                    )
                )

            return UserStatisticsDTO(
                total_count=total_count,
                work_type_counts=work_type_counts,
                user_counts=user_counts,
                timeline_data=timeline_data,
                top_contributors=top_contributors,
            )

        except Exception as e:
            logger.error(f"ユーザー統計の取得中にエラーが発生しました: {e}")
            # エラー時は空の統計を返す
            return UserStatisticsDTO(
                total_count=0,
                work_type_counts={},
                user_counts={},
                timeline_data=[],
                top_contributors=[],
            )
