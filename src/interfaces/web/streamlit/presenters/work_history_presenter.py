"""作業履歴プレゼンターモジュール

作業履歴の表示と操作を行うプレゼンタークラスを定義します。
"""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

import streamlit as st

from src.application.dtos.work_history_dto import WorkHistoryDTO, WorkType
from src.application.usecases.get_work_history_usecase import GetWorkHistoryUseCase
from src.infrastructure.di.container import Container

logger = logging.getLogger(__name__)


class WorkHistoryPresenter:
    """作業履歴プレゼンター

    作業履歴の取得、フィルタリング、表示をサポートします。
    """

    def __init__(self):
        """コンストラクタ"""
        container = Container()
        self.work_history_usecase = GetWorkHistoryUseCase(
            speaker_repository=container.repositories.speaker_repository(),
            parliamentary_group_membership_repository=container.repositories.parliamentary_group_membership_repository(),
            user_repository=container.repositories.user_repository(),
        )
        self.logger = logging.getLogger(__name__)

    def load_data(self) -> None:
        """データの初期読み込み（必要に応じて使用）"""
        pass

    def handle_action(self, action: str, **kwargs: str | int) -> None:
        """アクション処理（将来的な拡張用）

        Args:
            action: アクション名
            **kwargs: アクションパラメータ
        """
        pass

    def search_histories(
        self,
        user_id: UUID | None = None,
        work_types: list[WorkType] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[WorkHistoryDTO]:
        """作業履歴を検索する

        Args:
            user_id: フィルタリング対象のユーザーID
            work_types: フィルタリング対象の作業タイプリスト
            start_date: 開始日時
            end_date: 終了日時
            limit: 取得する最大件数
            offset: 取得開始位置

        Returns:
            作業履歴のリスト
        """
        try:
            histories = asyncio.run(
                self.work_history_usecase.execute(
                    user_id=user_id,
                    work_types=work_types,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    offset=offset,
                )
            )
            return histories
        except Exception as e:
            self.logger.error(f"作業履歴の検索中にエラーが発生しました: {e}")
            st.error(f"作業履歴の検索中にエラーが発生しました: {e}")
            return []

    def get_statistics(
        self,
        user_id: UUID | None = None,
        work_types: list[WorkType] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, int | dict[str, int]]:
        """作業履歴の統計情報を取得する

        Args:
            user_id: フィルタリング対象のユーザーID
            work_types: フィルタリング対象の作業タイプリスト
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            統計情報の辞書
        """
        try:
            # すべての履歴を取得（limitを大きく設定）
            histories = asyncio.run(
                self.work_history_usecase.execute(
                    user_id=user_id,
                    work_types=work_types,
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000,  # 統計用に大量取得
                )
            )

            # 統計情報の集計
            total_count = len(histories)
            work_type_counts = {}
            user_counts = {}

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

            return {
                "total_count": total_count,
                "work_type_counts": work_type_counts,
                "user_counts": user_counts,
            }
        except Exception as e:
            self.logger.error(f"統計情報の取得中にエラーが発生しました: {e}")
            st.error(f"統計情報の取得中にエラーが発生しました: {e}")
            return {
                "total_count": 0,
                "work_type_counts": {},
                "user_counts": {},
            }

    def get_work_types(self) -> list[WorkType]:
        """利用可能な作業タイプのリストを取得する

        Returns:
            作業タイプのリスト
        """
        return list(WorkType)

    def get_work_type_display_names(self) -> dict[WorkType, str]:
        """作業タイプの表示名を取得する

        Returns:
            作業タイプと表示名の辞書
        """
        return {
            WorkType.SPEAKER_POLITICIAN_MATCHING: "発言者-政治家紐付け",
            WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION: "議員団メンバー作成",
        }
