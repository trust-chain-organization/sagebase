"""作業履歴取得ユースケースのテスト"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.dtos.work_history_dto import WorkType
from src.application.usecases.get_work_history_usecase import GetWorkHistoryUseCase
from src.domain.dtos.parliamentary_group_membership_dto import (
    ParliamentaryGroupMembershipWithRelationsDTO,
)
from src.domain.dtos.speaker_dto import SpeakerWithPoliticianDTO
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
        politician_id=1,
        matched_by_user_id=user_id,
        updated_at=datetime.now(),
    )
    speaker_dto = SpeakerWithPoliticianDTO(speaker=speaker, politician=politician)
    speaker_repo.find_by_matched_user = AsyncMock(return_value=[speaker_dto])

    # 議員団メンバー作成作業のテストデータ
    group = ParliamentaryGroup(id=1, name="Test Group", conference_id=1)
    membership = ParliamentaryGroupMembership(
        id=1,
        politician_id=1,
        parliamentary_group_id=1,
        start_date=datetime.now().date(),
        role="Member",
        created_by_user_id=user_id,
        created_at=datetime.now(),
    )
    membership_dto = ParliamentaryGroupMembershipWithRelationsDTO(
        membership=membership, politician=politician, parliamentary_group=group
    )
    membership_repo.find_by_created_user = AsyncMock(return_value=[membership_dto])

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


@pytest.mark.asyncio
async def test_get_work_history_filter_by_user_id():
    """特定のユーザーIDでフィルタリングするテスト"""
    # Arrange
    user_id_1 = uuid4()

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # user_id_1のデータ
    politician1 = Politician(id=1, name="Politician 1")
    speaker1 = Speaker(
        id=1,
        name="Speaker 1",
        is_politician=True,
        matched_by_user_id=user_id_1,
        updated_at=datetime.now(),
    )
    speaker1_dto = SpeakerWithPoliticianDTO(speaker=speaker1, politician=politician1)

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[speaker1_dto])
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    user = User(user_id=user_id_1, email="user1@example.com", name="User 1")
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    histories = await usecase.execute(user_id=user_id_1)

    # Assert
    assert len(histories) == 1
    assert histories[0].user_id == user_id_1
    speaker_repo.find_by_matched_user.assert_called_once_with(user_id_1)


@pytest.mark.asyncio
async def test_get_work_history_filter_by_work_type_speaker_matching():
    """発言者-政治家紐付けのみでフィルタリングするテスト"""
    # Arrange
    user_id = uuid4()
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    politician = Politician(id=1, name="Test Politician")
    speaker = Speaker(
        id=1,
        name="Test Speaker",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=datetime.now(),
    )
    speaker_dto = SpeakerWithPoliticianDTO(speaker=speaker, politician=politician)
    speaker_repo.find_by_matched_user = AsyncMock(return_value=[speaker_dto])

    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    user = User(user_id=user_id, email="test@example.com", name="Test User")
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    histories = await usecase.execute(work_types=[WorkType.SPEAKER_POLITICIAN_MATCHING])

    # Assert
    assert len(histories) == 1
    assert histories[0].work_type == WorkType.SPEAKER_POLITICIAN_MATCHING
    speaker_repo.find_by_matched_user.assert_called_once()
    # Membership repo should not be called
    membership_repo.find_by_created_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_work_history_filter_by_work_type_membership_creation():
    """議員団メンバー作成のみでフィルタリングするテスト"""
    # Arrange
    user_id = uuid4()
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    group = ParliamentaryGroup(id=1, name="Test Group", conference_id=1)
    politician = Politician(id=1, name="Test Politician")
    membership = ParliamentaryGroupMembership(
        id=1,
        politician_id=1,
        parliamentary_group_id=1,
        start_date=datetime.now().date(),
        created_by_user_id=user_id,
        created_at=datetime.now(),
    )
    membership_dto = ParliamentaryGroupMembershipWithRelationsDTO(
        membership=membership, politician=politician, parliamentary_group=group
    )
    membership_repo.find_by_created_user = AsyncMock(return_value=[membership_dto])

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[])

    user = User(user_id=user_id, email="test@example.com", name="Test User")
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    histories = await usecase.execute(
        work_types=[WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION]
    )

    # Assert
    assert len(histories) == 1
    assert histories[0].work_type == WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION
    membership_repo.find_by_created_user.assert_called_once()
    # Speaker repo should not be called
    speaker_repo.find_by_matched_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_work_history_filter_by_date_range():
    """日付範囲でフィルタリングするテスト"""
    # Arrange
    user_id = uuid4()
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Create speakers with different dates
    politician1 = Politician(id=1, name="Politician 1")
    speaker1 = Speaker(
        id=1,
        name="Speaker 1",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=datetime(2024, 1, 10, 10, 0),  # Within range
    )
    speaker1_dto = SpeakerWithPoliticianDTO(speaker=speaker1, politician=politician1)

    politician2 = Politician(id=2, name="Politician 2")
    speaker2 = Speaker(
        id=2,
        name="Speaker 2",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=datetime(2024, 1, 20, 10, 0),  # Outside range
    )
    speaker2_dto = SpeakerWithPoliticianDTO(speaker=speaker2, politician=politician2)

    speaker_repo.find_by_matched_user = AsyncMock(
        return_value=[speaker1_dto, speaker2_dto]
    )
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    user = User(user_id=user_id, email="test@example.com", name="Test User")
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act - Filter to only include speaker1
    histories = await usecase.execute(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 15),
    )

    # Assert
    assert len(histories) == 1
    assert histories[0].executed_at == datetime(2024, 1, 10, 10, 0)


@pytest.mark.asyncio
async def test_get_work_history_pagination():
    """ページネーションのテスト"""
    # Arrange
    user_id = uuid4()
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Create 5 speakers with DTOs
    speaker_dtos = []
    for i in range(5):
        politician = Politician(id=i, name=f"Politician {i}")
        speaker = Speaker(
            id=i,
            name=f"Speaker {i}",
            is_politician=True,
            matched_by_user_id=user_id,
            updated_at=datetime(2024, 1, i + 1, 10, 0),
        )
        speaker_dto = SpeakerWithPoliticianDTO(speaker=speaker, politician=politician)
        speaker_dtos.append(speaker_dto)

    speaker_repo.find_by_matched_user = AsyncMock(return_value=speaker_dtos)
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    user = User(user_id=user_id, email="test@example.com", name="Test User")
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act - Get page 1 (limit=2, offset=0)
    page1 = await usecase.execute(limit=2, offset=0)

    # Act - Get page 2 (limit=2, offset=2)
    page2 = await usecase.execute(limit=2, offset=2)

    # Assert
    assert len(page1) == 2
    assert len(page2) == 2
    # Results should be sorted by date descending
    assert page1[0].executed_at > page1[1].executed_at
    # Page 2 should have different results
    assert page1[0].executed_at != page2[0].executed_at


@pytest.mark.asyncio
async def test_get_work_history_empty_results():
    """結果がない場合のテスト"""
    # Arrange
    user_id = uuid4()
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[])
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    histories = await usecase.execute(user_id=user_id)

    # Assert
    assert len(histories) == 0
    assert histories == []


@pytest.mark.asyncio
async def test_get_work_history_speaker_without_updated_at():
    """updated_atがないSpeakerを除外するテスト"""
    # Arrange
    user_id = uuid4()
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Speaker without updated_at
    politician1 = Politician(id=1, name="Politician 1")
    speaker1 = Speaker(
        id=1,
        name="Speaker 1",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=None,  # No timestamp
    )
    speaker1_dto = SpeakerWithPoliticianDTO(speaker=speaker1, politician=politician1)

    # Speaker with updated_at
    politician2 = Politician(id=2, name="Politician 2")
    speaker2 = Speaker(
        id=2,
        name="Speaker 2",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=datetime.now(),
    )
    speaker2_dto = SpeakerWithPoliticianDTO(speaker=speaker2, politician=politician2)

    speaker_repo.find_by_matched_user = AsyncMock(
        return_value=[speaker1_dto, speaker2_dto]
    )
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    user = User(user_id=user_id, email="test@example.com", name="Test User")
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    histories = await usecase.execute()

    # Assert
    assert len(histories) == 1  # Only speaker2 should be included
    assert histories[0].target_data.startswith("Speaker 2")


@pytest.mark.asyncio
async def test_get_work_history_membership_without_created_at():
    """created_atがないMembershipを除外するテスト"""
    # Arrange
    user_id = uuid4()
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Membership without created_at
    politician1 = Politician(id=1, name="Politician 1")
    parliamentary_group1 = ParliamentaryGroup(id=1, name="Group 1", conference_id=1)
    membership1 = ParliamentaryGroupMembership(
        id=1,
        politician_id=1,
        parliamentary_group_id=1,
        start_date=datetime.now().date(),
        created_by_user_id=user_id,
        created_at=None,  # No timestamp
    )
    membership1_dto = ParliamentaryGroupMembershipWithRelationsDTO(
        membership=membership1,
        politician=politician1,
        parliamentary_group=parliamentary_group1,
    )

    # Membership with created_at
    politician2 = Politician(id=2, name="Politician 2")
    parliamentary_group2 = ParliamentaryGroup(id=2, name="Group 2", conference_id=1)
    membership2 = ParliamentaryGroupMembership(
        id=2,
        politician_id=2,
        parliamentary_group_id=2,
        start_date=datetime.now().date(),
        created_by_user_id=user_id,
        created_at=datetime.now(),
    )
    membership2_dto = ParliamentaryGroupMembershipWithRelationsDTO(
        membership=membership2,
        politician=politician2,
        parliamentary_group=parliamentary_group2,
    )

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[])
    membership_repo.find_by_created_user = AsyncMock(
        return_value=[membership1_dto, membership2_dto]
    )

    user = User(user_id=user_id, email="test@example.com", name="Test User")
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    histories = await usecase.execute()

    # Assert
    assert len(histories) == 1  # Only membership2 should be included
    assert "Group 2" in histories[0].target_data


@pytest.mark.asyncio
async def test_get_work_history_sorted_by_date_descending():
    """日時で降順ソートされることを確認するテスト"""
    # Arrange
    user_id = uuid4()
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Create data with different timestamps
    politician1 = Politician(id=1, name="Politician 1")
    speaker = Speaker(
        id=1,
        name="Speaker 1",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=datetime(2024, 1, 15, 10, 0),  # Later date
    )
    speaker_dto = SpeakerWithPoliticianDTO(speaker=speaker, politician=politician1)

    politician2 = Politician(id=2, name="Politician 2")
    parliamentary_group = ParliamentaryGroup(id=1, name="Group 1", conference_id=1)
    membership = ParliamentaryGroupMembership(
        id=1,
        politician_id=2,
        parliamentary_group_id=1,
        start_date=datetime.now().date(),
        created_by_user_id=user_id,
        created_at=datetime(2024, 1, 10, 10, 0),  # Earlier date
    )
    membership_dto = ParliamentaryGroupMembershipWithRelationsDTO(
        membership=membership,
        politician=politician2,
        parliamentary_group=parliamentary_group,
    )

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[speaker_dto])
    membership_repo.find_by_created_user = AsyncMock(return_value=[membership_dto])

    user = User(user_id=user_id, email="test@example.com", name="Test User")
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
    # First result should be the more recent one (speaker)
    assert histories[0].work_type == WorkType.SPEAKER_POLITICIAN_MATCHING
    assert histories[0].executed_at == datetime(2024, 1, 15, 10, 0)
    # Second result should be the older one (membership)
    assert histories[1].work_type == WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION
    assert histories[1].executed_at == datetime(2024, 1, 10, 10, 0)
