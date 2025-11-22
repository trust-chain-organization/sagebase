"""作業履歴取得ユースケースのテスト"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.dtos.work_history_dto import WorkType
from src.application.usecases.get_work_history_usecase import GetWorkHistoryUseCase
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.entities.user import User


@pytest.mark.asyncio
async def test_get_work_history_all_types():
    """全ての作業タイプの履歴を取得するテスト"""
    # Arrange
    user_id = uuid4()
    user = User(user_id=user_id, email="test@example.com", name="Test User")

    # モックリポジトリの作成
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # 発言者-政治家紐付け作業のテストデータ
    politician = Politician(id=1, name="Test Politician")
    speaker = Speaker(
        id=1,
        name="Test Speaker",
        is_politician=True,
    )
    # 必要な属性を手動で設定
    speaker.politician_id = 1
    speaker.politician = politician
    speaker.matched_by_user_id = user_id
    speaker.updated_at = datetime.now()
    speaker_repo.find_by_matched_user = AsyncMock(return_value=[speaker])

    # 議員団メンバー作成作業のテストデータ
    group = ParliamentaryGroup(id=1, name="Test Group", conference_id=1)
    membership = ParliamentaryGroupMembership(
        id=1,
        politician_id=1,
        parliamentary_group_id=1,
        start_date=datetime.now().date(),
        role="Member",
    )
    # 必要な属性を手動で設定
    membership.politician = politician
    membership.parliamentary_group = group
    membership.created_by_user_id = user_id
    membership.created_at = datetime.now()
    membership.updated_at = datetime.now()
    membership_repo.find_by_created_user = AsyncMock(return_value=[membership])

    # ユーザーリポジトリのモック
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    histories = await usecase.execute()

    # Assert
    assert len(histories) == 2
    assert any(h.work_type == WorkType.SPEAKER_POLITICIAN_MATCHING for h in histories)
    assert any(
        h.work_type == WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION
        for h in histories
    )
    assert all(h.user_id == user_id for h in histories)
    assert all(h.user_name == "Test User" for h in histories)
