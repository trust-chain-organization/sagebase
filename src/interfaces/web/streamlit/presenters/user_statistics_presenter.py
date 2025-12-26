"""ユーザー統計プレゼンターモジュール

このモジュールは、ユーザー統計情報の表示ロジックを提供します。
"""

import asyncio
import logging

from datetime import datetime
from uuid import UUID

import pandas as pd

import streamlit as st

from src.application.dtos.user_statistics_dto import (
    UserStatisticsDTO,
)
from src.application.dtos.work_history_dto import WorkType
from src.application.usecases.get_user_statistics_usecase import (
    GetUserStatisticsUseCase,
)
from src.application.usecases.get_work_history_usecase import GetWorkHistoryUseCase
from src.infrastructure.di.container import Container

logger = logging.getLogger(__name__)


class UserStatisticsPresenter:
    """ユーザー統計プレゼンター

    ユーザー統計データを取得し、Streamlit UIで表示しやすい形式に変換します。
    """

    def __init__(self) -> None:
        """プレゼンターを初期化する"""
        container = Container()
        work_history_usecase = GetWorkHistoryUseCase(
            speaker_repository=container.repositories.speaker_repository(),
            parliamentary_group_membership_repository=container.repositories.parliamentary_group_membership_repository(),
            user_repository=container.repositories.user_repository(),
        )
        self.user_statistics_usecase = GetUserStatisticsUseCase(
            work_history_usecase=work_history_usecase
        )
        self.logger = logger

    def load_data(self) -> None:
        """データをロードする（現在は何もしない）"""
        pass

    def handle_action(self, action: str) -> None:
        """アクションを処理する

        Args:
            action: アクション名
        """
        # 現在は特別なアクションはない
        pass

    def get_statistics(
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
            top_n: 上位貢献者の表示数

        Returns:
            ユーザー統計情報のDTO
        """
        try:
            return asyncio.run(
                self.user_statistics_usecase.execute(
                    user_id=user_id,
                    work_types=work_types,
                    start_date=start_date,
                    end_date=end_date,
                    top_n=top_n,
                )
            )
        except Exception as e:
            self.logger.error(f"統計情報の取得中にエラーが発生しました: {e}")
            st.error(f"統計情報の取得中にエラーが発生しました: {e}")
            return UserStatisticsDTO(
                total_count=0,
                work_type_counts={},
                user_counts={},
                timeline_data=[],
                top_contributors=[],
            )

    def get_timeline_dataframe(self, stats: UserStatisticsDTO) -> pd.DataFrame | None:
        """時系列データをDataFrameに変換する

        Args:
            stats: ユーザー統計情報

        Returns:
            時系列データのDataFrame（データがない場合はNone）
        """
        if not stats.timeline_data:
            return None

        timeline_records = [
            {"日付": point.date, "作業件数": point.count}
            for point in stats.timeline_data
        ]

        df = pd.DataFrame(timeline_records)
        df = df.sort_values("日付")
        return df

    def get_contributors_dataframe(
        self, stats: UserStatisticsDTO
    ) -> pd.DataFrame | None:
        """上位貢献者をDataFrameに変換する

        Args:
            stats: ユーザー統計情報

        Returns:
            上位貢献者のDataFrame（データがない場合はNone）
        """
        if not stats.top_contributors:
            return None

        contributors_records = []
        for contributor in stats.top_contributors:
            # 作業タイプ別内訳を文字列に変換
            breakdown_str = ", ".join(
                [
                    f"{self._get_work_type_display_name(wt)}: {count}"
                    for wt, count in contributor.work_type_breakdown.items()
                ]
            )

            contributors_records.append(
                {
                    "順位": contributor.rank,
                    "ユーザー名": contributor.user_name or "未設定",
                    "メールアドレス": contributor.user_email or "未設定",
                    "総作業件数": contributor.total_works,
                    "作業内訳": breakdown_str,
                }
            )

        return pd.DataFrame(contributors_records)

    def get_work_type_display_names(self) -> dict[WorkType, str]:
        """作業タイプの表示名マップを取得する

        Returns:
            作業タイプから表示名へのマッピング
        """
        return {
            WorkType.SPEAKER_POLITICIAN_MATCHING: "発言者-政治家紐付け",
            WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION: "議員団メンバー作成",
        }

    def _get_work_type_display_name(self, work_type: str) -> str:
        """作業タイプの表示名を取得する

        Args:
            work_type: 作業タイプ（文字列）

        Returns:
            作業タイプの表示名
        """
        try:
            work_type_enum = WorkType(work_type)
            display_names = self.get_work_type_display_names()
            return display_names.get(work_type_enum, work_type)
        except ValueError:
            return work_type
