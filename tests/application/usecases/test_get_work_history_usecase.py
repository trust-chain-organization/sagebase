"""作業履歴取得ユースケースのテスト"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.dtos.parliamentary_group_membership_dto import (
    ParliamentaryGroupMembershipWithRelationsDTO,
)
from src.application.dtos.speaker_dto import SpeakerWithPoliticianDTO
from src.application.dtos.work_history_dto import WorkType
from src.application.usecases.get_work_history_usecase import GetWorkHistoryUseCase
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.entities.politician import Politician
from src.domain.entities.politician_operation_log import (
    PoliticianOperationLog,
    PoliticianOperationType,
)
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
    politician = Politician(
        id=1, name="Test Politician", prefecture="東京都", district="東京1区"
    )
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
    politician1 = Politician(
        id=1, name="Politician 1", prefecture="東京都", district="東京1区"
    )
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

    politician = Politician(
        id=1, name="Test Politician", prefecture="東京都", district="東京1区"
    )
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
    politician = Politician(
        id=1, name="Test Politician", prefecture="東京都", district="東京1区"
    )
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
    politician1 = Politician(
        id=1, name="Politician 1", prefecture="東京都", district="東京1区"
    )
    speaker1 = Speaker(
        id=1,
        name="Speaker 1",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=datetime(2024, 1, 10, 10, 0),  # Within range
    )
    speaker1_dto = SpeakerWithPoliticianDTO(speaker=speaker1, politician=politician1)

    politician2 = Politician(
        id=2, name="Politician 2", prefecture="東京都", district="東京2区"
    )
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
        politician = Politician(
            id=i, name=f"Politician {i}", prefecture="東京都", district=f"東京{i}区"
        )
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
    politician1 = Politician(
        id=1, name="Politician 1", prefecture="東京都", district="東京1区"
    )
    speaker1 = Speaker(
        id=1,
        name="Speaker 1",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=None,  # No timestamp
    )
    speaker1_dto = SpeakerWithPoliticianDTO(speaker=speaker1, politician=politician1)

    # Speaker with updated_at
    politician2 = Politician(
        id=2, name="Politician 2", prefecture="東京都", district="東京2区"
    )
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
    politician1 = Politician(
        id=1, name="Politician 1", prefecture="東京都", district="東京1区"
    )
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
    politician2 = Politician(
        id=2, name="Politician 2", prefecture="東京都", district="東京2区"
    )
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
    politician1 = Politician(
        id=1, name="Politician 1", prefecture="東京都", district="東京1区"
    )
    speaker = Speaker(
        id=1,
        name="Speaker 1",
        is_politician=True,
        matched_by_user_id=user_id,
        updated_at=datetime(2024, 1, 15, 10, 0),  # Later date
    )
    speaker_dto = SpeakerWithPoliticianDTO(speaker=speaker, politician=politician1)

    politician2 = Politician(
        id=2, name="Politician 2", prefecture="東京都", district="東京2区"
    )
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


@pytest.mark.asyncio
async def test_get_work_statistics_by_user_all_users():
    """全ユーザーの作業統計を取得するテスト"""
    # Arrange
    user_id_1 = uuid4()
    user_id_2 = uuid4()

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker statistics
    speaker_stats = {
        user_id_1: 10,
        user_id_2: 5,
    }
    speaker_repo.get_speaker_matching_statistics_by_user = AsyncMock(
        return_value=speaker_stats
    )

    # Mock membership statistics
    membership_stats = {
        user_id_1: 3,
        user_id_2: 7,
    }
    membership_repo.get_membership_creation_statistics_by_user = AsyncMock(
        return_value=membership_stats
    )

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_work_statistics_by_user()

    # Assert
    assert len(result) == 2
    assert result[user_id_1]["SPEAKER_POLITICIAN_MATCHING"] == 10
    assert result[user_id_1]["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 3
    assert result[user_id_2]["SPEAKER_POLITICIAN_MATCHING"] == 5
    assert result[user_id_2]["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 7


@pytest.mark.asyncio
async def test_get_work_statistics_by_user_specific_user():
    """特定ユーザーの作業統計を取得するテスト"""
    # Arrange
    user_id = uuid4()

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker statistics
    speaker_stats = {user_id: 15}
    speaker_repo.get_speaker_matching_statistics_by_user = AsyncMock(
        return_value=speaker_stats
    )

    # Mock membership statistics
    membership_stats = {user_id: 8}
    membership_repo.get_membership_creation_statistics_by_user = AsyncMock(
        return_value=membership_stats
    )

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_work_statistics_by_user(user_id=user_id)

    # Assert
    assert len(result) == 1
    assert user_id in result
    assert result[user_id]["SPEAKER_POLITICIAN_MATCHING"] == 15
    assert result[user_id]["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 8
    speaker_repo.get_speaker_matching_statistics_by_user.assert_called_once_with(
        user_id=user_id, start_date=None, end_date=None
    )


@pytest.mark.asyncio
async def test_get_work_statistics_by_user_filter_by_work_type():
    """作業タイプでフィルタリングした統計取得のテスト"""
    # Arrange
    user_id = uuid4()

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker statistics
    speaker_stats = {user_id: 20}
    speaker_repo.get_speaker_matching_statistics_by_user = AsyncMock(
        return_value=speaker_stats
    )

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_work_statistics_by_user(
        work_types=[WorkType.SPEAKER_POLITICIAN_MATCHING]
    )

    # Assert
    assert len(result) == 1
    assert result[user_id]["SPEAKER_POLITICIAN_MATCHING"] == 20
    assert "PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION" not in result[user_id]
    speaker_repo.get_speaker_matching_statistics_by_user.assert_called_once()
    membership_repo.get_membership_creation_statistics_by_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_work_statistics_by_user_with_date_filter():
    """日付フィルタ付きの統計取得のテスト"""
    # Arrange
    user_id = uuid4()
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker statistics
    speaker_stats = {user_id: 5}
    speaker_repo.get_speaker_matching_statistics_by_user = AsyncMock(
        return_value=speaker_stats
    )

    # Mock membership statistics
    membership_stats = {user_id: 2}
    membership_repo.get_membership_creation_statistics_by_user = AsyncMock(
        return_value=membership_stats
    )

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_work_statistics_by_user(
        start_date=start_date, end_date=end_date
    )

    # Assert
    assert len(result) == 1
    assert result[user_id]["SPEAKER_POLITICIAN_MATCHING"] == 5
    assert result[user_id]["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 2
    speaker_repo.get_speaker_matching_statistics_by_user.assert_called_once_with(
        user_id=None, start_date=start_date, end_date=end_date
    )


@pytest.mark.asyncio
async def test_get_work_statistics_by_user_no_results():
    """統計結果がない場合のテスト"""
    # Arrange
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    speaker_repo.get_speaker_matching_statistics_by_user = AsyncMock(return_value={})
    membership_repo.get_membership_creation_statistics_by_user = AsyncMock(
        return_value={}
    )

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_work_statistics_by_user()

    # Assert
    assert len(result) == 0
    assert result == {}


@pytest.mark.asyncio
async def test_get_work_statistics_by_type():
    """作業タイプ別の統計取得のテスト"""
    # Arrange
    user_id_1 = uuid4()
    user_id_2 = uuid4()

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker statistics (total: 15)
    speaker_stats = {
        user_id_1: 10,
        user_id_2: 5,
    }
    speaker_repo.get_speaker_matching_statistics_by_user = AsyncMock(
        return_value=speaker_stats
    )

    # Mock membership statistics (total: 10)
    membership_stats = {
        user_id_1: 3,
        user_id_2: 7,
    }
    membership_repo.get_membership_creation_statistics_by_user = AsyncMock(
        return_value=membership_stats
    )

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_work_statistics_by_type()

    # Assert
    assert len(result) == 2
    assert result["SPEAKER_POLITICIAN_MATCHING"] == 15
    assert result["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 10


@pytest.mark.asyncio
async def test_get_timeline_statistics():
    """時系列統計取得のテスト"""
    # Arrange
    user_id = uuid4()

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker timeline statistics
    speaker_timeline = [
        {"date": "2024-01-01", "count": 5},
        {"date": "2024-01-02", "count": 3},
    ]
    speaker_repo.get_speaker_matching_timeline_statistics = AsyncMock(
        return_value=speaker_timeline
    )

    # Mock membership timeline statistics
    membership_timeline = [
        {"date": "2024-01-01", "count": 2},
        {"date": "2024-01-03", "count": 4},
    ]
    membership_repo.get_membership_creation_timeline_statistics = AsyncMock(
        return_value=membership_timeline
    )

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_timeline_statistics(user_id=user_id)

    # Assert
    assert len(result) == 3  # Three unique dates
    # Check 2024-01-01 (has both types)
    date_2024_01_01 = next(r for r in result if r["date"] == "2024-01-01")
    assert date_2024_01_01["SPEAKER_POLITICIAN_MATCHING"] == 5
    assert date_2024_01_01["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 2
    # Check 2024-01-02 (only speaker matching)
    date_2024_01_02 = next(r for r in result if r["date"] == "2024-01-02")
    assert date_2024_01_02["SPEAKER_POLITICIAN_MATCHING"] == 3
    assert "PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION" not in date_2024_01_02
    # Check 2024-01-03 (only membership creation)
    date_2024_01_03 = next(r for r in result if r["date"] == "2024-01-03")
    assert date_2024_01_03["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 4
    assert "SPEAKER_POLITICIAN_MATCHING" not in date_2024_01_03


@pytest.mark.asyncio
async def test_get_timeline_statistics_with_interval():
    """interval指定での時系列統計取得のテスト"""
    # Arrange
    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker timeline statistics
    speaker_timeline = [
        {"date": "2024-01-01", "count": 10},
    ]
    speaker_repo.get_speaker_matching_timeline_statistics = AsyncMock(
        return_value=speaker_timeline
    )

    # Mock membership timeline statistics
    membership_timeline = [
        {"date": "2024-01-01", "count": 5},
    ]
    membership_repo.get_membership_creation_timeline_statistics = AsyncMock(
        return_value=membership_timeline
    )

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_timeline_statistics(interval="week")

    # Assert
    assert len(result) == 1
    assert result[0]["date"] == "2024-01-01"
    assert result[0]["SPEAKER_POLITICIAN_MATCHING"] == 10
    assert result[0]["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 5
    speaker_repo.get_speaker_matching_timeline_statistics.assert_called_once_with(
        user_id=None, start_date=None, end_date=None, interval="week"
    )


@pytest.mark.asyncio
async def test_get_top_contributors():
    """上位貢献者取得のテスト"""
    # Arrange
    user_id_1 = uuid4()
    user_id_2 = uuid4()
    user_id_3 = uuid4()

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker statistics
    speaker_stats = {
        user_id_1: 10,
        user_id_2: 5,
        user_id_3: 2,
    }
    speaker_repo.get_speaker_matching_statistics_by_user = AsyncMock(
        return_value=speaker_stats
    )

    # Mock membership statistics
    membership_stats = {
        user_id_1: 3,  # Total: 13
        user_id_2: 7,  # Total: 12
        user_id_3: 1,  # Total: 3
    }
    membership_repo.get_membership_creation_statistics_by_user = AsyncMock(
        return_value=membership_stats
    )

    # Mock user repository
    async def get_user(uid):
        users = {
            user_id_1: User(
                user_id=user_id_1, email="user1@example.com", name="User 1"
            ),
            user_id_2: User(
                user_id=user_id_2, email="user2@example.com", name="User 2"
            ),
            user_id_3: User(
                user_id=user_id_3, email="user3@example.com", name="User 3"
            ),
        }
        return users.get(uid)

    user_repo.get_by_id = AsyncMock(side_effect=get_user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_top_contributors(limit=2)

    # Assert
    assert len(result) == 2
    # First contributor should be user_id_1 (total: 13)
    assert result[0]["user_id"] == user_id_1
    assert result[0]["user_name"] == "User 1"
    assert result[0]["total_count"] == 13
    assert result[0]["by_type"]["SPEAKER_POLITICIAN_MATCHING"] == 10
    assert result[0]["by_type"]["PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION"] == 3
    # Second contributor should be user_id_2 (total: 12)
    assert result[1]["user_id"] == user_id_2
    assert result[1]["user_name"] == "User 2"
    assert result[1]["total_count"] == 12


@pytest.mark.asyncio
async def test_get_top_contributors_with_filter():
    """フィルタ付きの上位貢献者取得のテスト"""
    # Arrange
    user_id_1 = uuid4()
    user_id_2 = uuid4()

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    # Mock speaker statistics (only this type is requested)
    speaker_stats = {
        user_id_1: 20,
        user_id_2: 15,
    }
    speaker_repo.get_speaker_matching_statistics_by_user = AsyncMock(
        return_value=speaker_stats
    )

    # Mock user repository
    async def get_user(uid):
        users = {
            user_id_1: User(
                user_id=user_id_1, email="user1@example.com", name="User 1"
            ),
            user_id_2: User(
                user_id=user_id_2, email="user2@example.com", name="User 2"
            ),
        }
        return users.get(uid)

    user_repo.get_by_id = AsyncMock(side_effect=get_user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
    )

    # Act
    result = await usecase.get_top_contributors(
        work_types=[WorkType.SPEAKER_POLITICIAN_MATCHING],
        limit=10,
    )

    # Assert
    assert len(result) == 2
    assert result[0]["user_id"] == user_id_1
    assert result[0]["total_count"] == 20
    assert "SPEAKER_POLITICIAN_MATCHING" in result[0]["by_type"]
    assert "PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION" not in result[0]["by_type"]


@pytest.mark.asyncio
async def test_get_work_history_with_politician_operations():
    """政治家操作履歴を含む作業履歴取得テスト"""
    # Arrange
    user_id = uuid4()
    user = User(user_id=user_id, email="test@example.com", name="Test User")

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()
    politician_log_repo = MagicMock()

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[])
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    # 政治家操作ログのテストデータ
    log = PoliticianOperationLog(
        id=1,
        politician_id=42,
        politician_name="山田太郎",
        operation_type=PoliticianOperationType.CREATE,
        user_id=user_id,
        operated_at=datetime.now(),
    )
    politician_log_repo.find_by_filters = AsyncMock(return_value=[log])

    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
        politician_operation_log_repository=politician_log_repo,
    )

    # Act
    histories = await usecase.execute()

    # Assert
    assert len(histories) >= 1
    assert any(h.work_type == WorkType.POLITICIAN_CREATE for h in histories)


@pytest.mark.asyncio
async def test_get_work_history_with_all_politician_operation_types():
    """全ての政治家操作タイプの履歴取得テスト"""
    # Arrange
    user_id = uuid4()
    user = User(user_id=user_id, email="test@example.com", name="Test User")

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()
    politician_log_repo = MagicMock()

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[])
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    # 全ての政治家操作タイプのテストデータ
    logs = [
        PoliticianOperationLog(
            id=1,
            politician_id=1,
            politician_name="山田太郎",
            operation_type=PoliticianOperationType.CREATE,
            user_id=user_id,
            operated_at=datetime.now(),
        ),
        PoliticianOperationLog(
            id=2,
            politician_id=2,
            politician_name="鈴木花子",
            operation_type=PoliticianOperationType.UPDATE,
            user_id=user_id,
            operated_at=datetime.now(),
        ),
        PoliticianOperationLog(
            id=3,
            politician_id=3,
            politician_name="田中次郎",
            operation_type=PoliticianOperationType.DELETE,
            user_id=user_id,
            operated_at=datetime.now(),
        ),
    ]
    politician_log_repo.find_by_filters = AsyncMock(return_value=logs)

    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
        politician_operation_log_repository=politician_log_repo,
    )

    # Act
    histories = await usecase.execute()

    # Assert
    # 各操作タイプが履歴に含まれていることを確認
    assert any(h.work_type == WorkType.POLITICIAN_CREATE for h in histories)
    assert any(h.work_type == WorkType.POLITICIAN_UPDATE for h in histories)
    assert any(h.work_type == WorkType.POLITICIAN_DELETE for h in histories)


@pytest.mark.asyncio
async def test_get_work_history_without_politician_log_repo():
    """政治家操作ログリポジトリがない場合のテスト（後方互換性）"""
    # Arrange
    user_id = uuid4()
    user = User(user_id=user_id, email="test@example.com", name="Test User")

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[])
    membership_repo.find_by_created_user = AsyncMock(return_value=[])
    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
        politician_operation_log_repository=None,  # No log repository
    )

    # Act
    histories = await usecase.execute()

    # Assert - should work without politician log repository
    assert len(histories) == 0


@pytest.mark.asyncio
async def test_get_work_history_politician_log_without_user_id_skipped():
    """user_idがNoneの政治家操作ログはスキップされるテスト"""
    # Arrange
    user_id = uuid4()
    user = User(user_id=user_id, email="test@example.com", name="Test User")

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()
    politician_log_repo = MagicMock()

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[])
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    # user_idがNoneのログ
    log_without_user = PoliticianOperationLog(
        id=1,
        politician_id=42,
        politician_name="山田太郎",
        operation_type=PoliticianOperationType.CREATE,
        user_id=None,  # No user
        operated_at=datetime.now(),
    )
    politician_log_repo.find_by_filters = AsyncMock(return_value=[log_without_user])

    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
        politician_operation_log_repository=politician_log_repo,
    )

    # Act
    histories = await usecase.execute()

    # Assert - log without user_id should be skipped
    assert len(histories) == 0


@pytest.mark.asyncio
async def test_get_work_history_filter_by_politician_create_type():
    """政治家作成タイプでフィルタリングするテスト"""
    # Arrange
    user_id = uuid4()
    user = User(user_id=user_id, email="test@example.com", name="Test User")

    speaker_repo = MagicMock()
    membership_repo = MagicMock()
    user_repo = MagicMock()
    politician_log_repo = MagicMock()

    speaker_repo.find_by_matched_user = AsyncMock(return_value=[])
    membership_repo.find_by_created_user = AsyncMock(return_value=[])

    log = PoliticianOperationLog(
        id=1,
        politician_id=42,
        politician_name="山田太郎",
        operation_type=PoliticianOperationType.CREATE,
        user_id=user_id,
        operated_at=datetime.now(),
    )
    politician_log_repo.find_by_filters = AsyncMock(return_value=[log])

    user_repo.get_by_id = AsyncMock(return_value=user)

    usecase = GetWorkHistoryUseCase(
        speaker_repository=speaker_repo,
        parliamentary_group_membership_repository=membership_repo,
        user_repository=user_repo,
        politician_operation_log_repository=politician_log_repo,
    )

    # Act
    histories = await usecase.execute(work_types=[WorkType.POLITICIAN_CREATE])

    # Assert
    politician_create_histories = [
        h for h in histories if h.work_type == WorkType.POLITICIAN_CREATE
    ]
    assert len(politician_create_histories) >= 1
    assert politician_create_histories[0].target_data == "山田太郎"
