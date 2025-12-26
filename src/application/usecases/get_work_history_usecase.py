"""作業履歴取得ユースケースモジュール

ユーザーが実行した作業の履歴を取得するユースケースを定義します。
"""

import logging

from datetime import datetime
from typing import Any
from uuid import UUID

from src.application.dtos.work_history_dto import WorkHistoryDTO, WorkType
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.repositories.user_repository import IUserRepository

logger = logging.getLogger(__name__)


class GetWorkHistoryUseCase:
    """作業履歴取得ユースケース

    複数のテーブルから作業履歴を統合して取得します。
    """

    def __init__(
        self,
        speaker_repository: SpeakerRepository,
        parliamentary_group_membership_repository: (
            ParliamentaryGroupMembershipRepository
        ),
        user_repository: IUserRepository,
    ):
        """コンストラクタ

        Args:
            speaker_repository: 発言者リポジトリ
            parliamentary_group_membership_repository: 議員団メンバーシップリポジトリ
            user_repository: ユーザーリポジトリ
        """
        self.speaker_repo = speaker_repository
        self.membership_repo = parliamentary_group_membership_repository
        self.user_repo = user_repository

    async def execute(
        self,
        user_id: UUID | None = None,
        work_types: list[WorkType] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkHistoryDTO]:
        """作業履歴を取得する

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            work_types: フィルタリング対象の作業タイプリスト（Noneの場合は全タイプ）
            start_date: 開始日時（この日時以降の作業を取得）
            end_date: 終了日時（この日時以前の作業を取得）
            limit: 取得する最大件数
            offset: 取得開始位置（ページネーション用）

        Returns:
            作業履歴のリスト（実行日時の降順）
        """
        logger.info(
            f"作業履歴取得開始: user_id={user_id}, work_types={work_types}, "
            f"start_date={start_date}, end_date={end_date}, "
            f"limit={limit}, offset={offset}"
        )

        histories: list[WorkHistoryDTO] = []

        # 作業タイプのフィルタリング設定
        include_speaker_matching = work_types is None or (
            WorkType.SPEAKER_POLITICIAN_MATCHING in work_types
        )
        include_membership_creation = work_types is None or (
            WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION in work_types
        )

        # 1. 発言者-政治家紐付け作業の取得
        if include_speaker_matching:
            speaker_histories = await self._get_speaker_matching_histories(
                user_id, start_date, end_date
            )
            histories.extend(speaker_histories)

        # 2. 議員団メンバー作成作業の取得
        if include_membership_creation:
            membership_histories = await self._get_membership_creation_histories(
                user_id, start_date, end_date
            )
            histories.extend(membership_histories)

        # 実行日時で降順ソート
        histories.sort(key=lambda x: x.executed_at, reverse=True)

        # ページネーション
        total = len(histories)
        paginated_histories = histories[offset : offset + limit]

        logger.info(
            f"作業履歴取得完了: 取得件数={len(paginated_histories)}, 総件数={total}"
        )

        return paginated_histories

    async def _get_speaker_matching_histories(
        self,
        user_id: UUID | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> list[WorkHistoryDTO]:
        """発言者-政治家紐付け作業の履歴を取得

        Args:
            user_id: フィルタリング対象のユーザーID
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            発言者-政治家紐付け作業の履歴リスト
        """
        # matched_by_user_idが設定されているspeakersとpolitician情報を取得
        speaker_dtos = await self.speaker_repo.find_by_matched_user(user_id)

        histories: list[WorkHistoryDTO] = []
        user_cache: dict[UUID, tuple[str | None, str | None]] = {}

        for dto in speaker_dtos:
            speaker = dto.speaker
            politician = dto.politician

            if speaker.matched_by_user_id is None:
                continue

            # 日付フィルタリング
            if speaker.updated_at is None:
                continue
            if start_date and speaker.updated_at < start_date:
                continue
            if end_date and speaker.updated_at > end_date:
                continue

            # ユーザー情報の取得（キャッシュを使用）
            if speaker.matched_by_user_id not in user_cache:
                user = await self.user_repo.get_by_id(speaker.matched_by_user_id)
                user_cache[speaker.matched_by_user_id] = (
                    user.name if user else None,
                    user.email if user else None,
                )

            user_name, user_email = user_cache[speaker.matched_by_user_id]

            # 対象データの説明を作成
            politician_name = politician.name if politician else "不明な政治家"
            target_data = f"{speaker.name} → {politician_name}"

            histories.append(
                WorkHistoryDTO(
                    user_id=speaker.matched_by_user_id,
                    user_name=user_name,
                    user_email=user_email,
                    work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
                    target_data=target_data,
                    executed_at=speaker.updated_at,
                )
            )

        return histories

    async def _get_membership_creation_histories(
        self,
        user_id: UUID | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> list[WorkHistoryDTO]:
        """議員団メンバー作成作業の履歴を取得

        Args:
            user_id: フィルタリング対象のユーザーID
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            議員団メンバー作成作業の履歴リスト
        """
        # created_by_user_idが設定されているmembershipsと関連情報を取得
        membership_dtos = await self.membership_repo.find_by_created_user(user_id)

        histories: list[WorkHistoryDTO] = []
        user_cache: dict[UUID, tuple[str | None, str | None]] = {}

        for dto in membership_dtos:
            membership = dto.membership
            politician = dto.politician
            parliamentary_group = dto.parliamentary_group

            if membership.created_by_user_id is None:
                continue

            # 日付フィルタリング
            if membership.created_at is None:
                continue
            if start_date and membership.created_at < start_date:
                continue
            if end_date and membership.created_at > end_date:
                continue

            # ユーザー情報の取得（キャッシュを使用）
            if membership.created_by_user_id not in user_cache:
                user = await self.user_repo.get_by_id(membership.created_by_user_id)
                user_cache[membership.created_by_user_id] = (
                    user.name if user else None,
                    user.email if user else None,
                )

            user_name, user_email = user_cache[membership.created_by_user_id]

            # 対象データの説明を作成
            group_name = (
                parliamentary_group.name if parliamentary_group else "不明な議員団"
            )
            politician_name = politician.name if politician else "不明な政治家"
            role = membership.role if membership.role else "メンバー"
            target_data = f"{group_name}: {politician_name} ({role})"

            histories.append(
                WorkHistoryDTO(
                    user_id=membership.created_by_user_id,
                    user_name=user_name,
                    user_email=user_email,
                    work_type=WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION,
                    target_data=target_data,
                    executed_at=membership.created_at,
                )
            )

        return histories

    async def get_work_statistics_by_user(
        self,
        user_id: UUID | None = None,
        work_types: list[WorkType] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[UUID, dict[str, int]]:
        """ユーザー別の作業件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            work_types: フィルタリング対象の作業タイプリスト（Noneの場合は全タイプ）
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            ユーザーIDごとの作業タイプ別件数
            例: {UUID('...'): {'SPEAKER_POLITICIAN_MATCHING': 10,
                             'PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION': 5}}
        """
        # Determine which statistics to collect
        include_speaker_matching = work_types is None or (
            WorkType.SPEAKER_POLITICIAN_MATCHING in work_types
        )
        include_membership_creation = work_types is None or (
            WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION in work_types
        )

        # Collect statistics from repositories
        user_statistics: dict[UUID, dict[str, int]] = {}

        if include_speaker_matching:
            speaker_stats = (
                await self.speaker_repo.get_speaker_matching_statistics_by_user(
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
            for uid, count in speaker_stats.items():
                if uid not in user_statistics:
                    user_statistics[uid] = {}
                user_statistics[uid]["SPEAKER_POLITICIAN_MATCHING"] = count

        if include_membership_creation:
            membership_stats = (
                await self.membership_repo.get_membership_creation_statistics_by_user(
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
            for uid, count in membership_stats.items():
                if uid not in user_statistics:
                    user_statistics[uid] = {}
                user_statistics[uid]["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] = count

        return user_statistics

    async def get_work_statistics_by_type(
        self,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, int]:
        """作業タイプ別の件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            作業タイプ別の件数
            例: {'SPEAKER_POLITICIAN_MATCHING': 100,
               'PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION': 50}
        """
        type_statistics: dict[str, int] = {}

        # Get speaker matching statistics
        speaker_stats = await self.speaker_repo.get_speaker_matching_statistics_by_user(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        total_speaker_matching = sum(speaker_stats.values())
        type_statistics["SPEAKER_POLITICIAN_MATCHING"] = total_speaker_matching

        # Get membership creation statistics
        membership_stats = (
            await self.membership_repo.get_membership_creation_statistics_by_user(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
        )
        total_membership_creation = sum(membership_stats.values())
        type_statistics["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] = (
            total_membership_creation
        )

        return type_statistics

    async def get_timeline_statistics(
        self,
        user_id: UUID | None = None,
        work_types: list[WorkType] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の作業件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            work_types: フィルタリング対象の作業タイプリスト（Noneの場合は全タイプ）
            start_date: 開始日時
            end_date: 終了日時
            interval: 集計間隔（"day", "week", "month"）

        Returns:
            時系列データのリスト
            例: [{"date": "2024-01-01",
                "SPEAKER_POLITICIAN_MATCHING": 5,
                "PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION": 3}, ...]
        """
        from collections import defaultdict

        # Determine which statistics to collect
        include_speaker_matching = work_types is None or (
            WorkType.SPEAKER_POLITICIAN_MATCHING in work_types
        )
        include_membership_creation = work_types is None or (
            WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION in work_types
        )

        # Collect timeline data from repositories
        date_statistics: dict[str, dict[str, int]] = defaultdict(dict)

        if include_speaker_matching:
            speaker_timeline = (
                await self.speaker_repo.get_speaker_matching_timeline_statistics(
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                )
            )
            for entry in speaker_timeline:
                date_statistics[entry["date"]]["SPEAKER_POLITICIAN_MATCHING"] = entry[
                    "count"
                ]

        if include_membership_creation:
            membership_timeline = (
                await self.membership_repo.get_membership_creation_timeline_statistics(
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                )
            )
            for entry in membership_timeline:
                date_statistics[entry["date"]][
                    "PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"
                ] = entry["count"]

        # Convert to list of dictionaries sorted by date
        timeline: list[dict[str, Any]] = []
        for date_str in sorted(date_statistics.keys()):
            entry: dict[str, Any] = {"date": date_str}
            entry.update(date_statistics[date_str])
            timeline.append(entry)

        return timeline

    async def get_top_contributors(
        self,
        work_types: list[WorkType] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """上位貢献者を取得する（データベースレベルで集計）

        Args:
            work_types: フィルタリング対象の作業タイプリスト（Noneの場合は全タイプ）
            start_date: 開始日時
            end_date: 終了日時
            limit: 取得する上位貢献者数

        Returns:
            上位貢献者のリスト
            例: [{"user_id": UUID('...'), "user_name": "...",
                "total_count": 15, "by_type": {...}}, ...]
        """
        # Get user statistics
        user_stats = await self.get_work_statistics_by_user(
            user_id=None,
            work_types=work_types,
            start_date=start_date,
            end_date=end_date,
        )

        # Calculate total count for each user
        user_totals: list[tuple[UUID, int, dict[str, int]]] = []
        for uid, type_counts in user_stats.items():
            total = sum(type_counts.values())
            user_totals.append((uid, total, type_counts))

        # Sort by total count descending
        user_totals.sort(key=lambda x: x[1], reverse=True)

        # Get user information and build result
        top_contributors = []
        for uid, total, type_counts in user_totals[:limit]:
            # Get user info
            user = await self.user_repo.get_by_id(uid)
            user_name = user.name if user else None
            user_email = user.email if user else None

            top_contributors.append(
                {
                    "user_id": uid,
                    "user_name": user_name,
                    "user_email": user_email,
                    "total_count": total,
                    "by_type": type_counts,
                }
            )

        return top_contributors
