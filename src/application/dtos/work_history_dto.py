"""作業履歴DTOモジュール

ユーザーが実行した作業の履歴を表現するDTOを定義します。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class WorkType(str, Enum):
    """作業タイプの列挙型"""

    SPEAKER_POLITICIAN_MATCHING = "speaker_politician_matching"
    """発言者-政治家紐付け作業"""

    PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION = "parliamentary_group_membership_creation"
    """議員団メンバー作成作業"""

    POLITICIAN_CREATE = "politician_create"
    """政治家作成作業"""

    POLITICIAN_UPDATE = "politician_update"
    """政治家更新作業"""

    POLITICIAN_DELETE = "politician_delete"
    """政治家削除作業"""

    PROPOSAL_CREATE = "proposal_create"
    """議案作成作業"""

    PROPOSAL_UPDATE = "proposal_update"
    """議案更新作業"""

    PROPOSAL_DELETE = "proposal_delete"
    """議案削除作業"""


@dataclass
class WorkHistoryDTO:
    """作業履歴を表現するDTO

    Attributes:
        user_id: 作業を実行したユーザーのID (UUID)
        user_name: 作業を実行したユーザーの名前
        user_email: 作業を実行したユーザーのメールアドレス
        work_type: 作業タイプ（WorkType列挙型）
        target_data: 作業対象データの説明
        executed_at: 作業実行日時
    """

    user_id: UUID
    user_name: str | None
    user_email: str | None
    work_type: WorkType
    target_data: str
    executed_at: datetime

    @property
    def work_type_display_name(self) -> str:
        """作業タイプの表示名を返す

        Returns:
            作業タイプの日本語表示名
        """
        display_names = {
            WorkType.SPEAKER_POLITICIAN_MATCHING: "発言者-政治家紐付け",
            WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION: "議員団メンバー作成",
            WorkType.POLITICIAN_CREATE: "政治家作成",
            WorkType.POLITICIAN_UPDATE: "政治家更新",
            WorkType.POLITICIAN_DELETE: "政治家削除",
            WorkType.PROPOSAL_CREATE: "議案作成",
            WorkType.PROPOSAL_UPDATE: "議案更新",
            WorkType.PROPOSAL_DELETE: "議案削除",
        }
        return display_names.get(self.work_type, self.work_type.value)
