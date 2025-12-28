"""Tests for ParliamentaryGroupRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupModel,
    ParliamentaryGroupRepositoryImpl,
)


class TestParliamentaryGroupRepositoryImpl:
    """Test cases for ParliamentaryGroupRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ParliamentaryGroupRepositoryImpl:
        """Create parliamentary group repository."""
        return ParliamentaryGroupRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_group_entity(self) -> ParliamentaryGroup:
        """Sample parliamentary group entity."""
        return ParliamentaryGroup(
            id=1,
            name="自民党会派",
            conference_id=10,
            url="https://example.com/group",
            description="自由民主党の会派",
            is_active=True,
        )

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
        sample_group_entity: ParliamentaryGroup,
    ) -> None:
        """Test create successfully creates a parliamentary group."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自民党会派"
        mock_row.conference_id = 10
        mock_row.url = "https://example.com/group"
        mock_row.description = "自由民主党の会派"
        mock_row.is_active = True

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.create(sample_group_entity)

        assert result.id == 1
        assert result.name == "自民党会派"
        assert result.conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
        sample_group_entity: ParliamentaryGroup,
    ) -> None:
        """Test create raises error when creation fails."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Failed to create parliamentary group"):
            await repository.create(sample_group_entity)

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
        sample_group_entity: ParliamentaryGroup,
    ) -> None:
        """Test update successfully updates a parliamentary group."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自民党会派（更新）"
        mock_row.conference_id = 10
        mock_row.url = "https://example.com/group"
        mock_row.description = "自由民主党の会派"
        mock_row.is_active = True

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        sample_group_entity.name = "自民党会派（更新）"
        result = await repository.update(sample_group_entity)

        assert result.name == "自民党会派（更新）"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update raises error when entity has no ID."""
        entity = ParliamentaryGroup(
            name="自民党会派",
            conference_id=10,
            is_active=True,
        )

        with pytest.raises(ValueError, match="Entity must have an ID to update"):
            await repository.update(entity)

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
        sample_group_entity: ParliamentaryGroup,
    ) -> None:
        """Test update raises error when group not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Parliamentary group with ID 1 not found"):
            await repository.update(sample_group_entity)

    @pytest.mark.asyncio
    async def test_get_by_name_and_conference_found(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name_and_conference when group is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自民党会派"
        mock_row.conference_id = 10
        mock_row.url = "https://example.com/group"
        mock_row.description = "自由民主党の会派"
        mock_row.is_active = True

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_conference("自民党会派", 10)

        assert result is not None
        assert result.id == 1
        assert result.name == "自民党会派"
        assert result.conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_conference_not_found(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name_and_conference when group is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_conference("存在しない会派", 10)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference_id_active_only(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_conference_id with active_only=True."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自民党会派"
        mock_row.conference_id = 10
        mock_row.url = "https://example.com/group"
        mock_row.description = "自由民主党の会派"
        mock_row.is_active = True

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference_id(10, active_only=True)

        assert len(result) == 1
        assert result[0].is_active is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference_id_all(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_conference_id with active_only=False."""
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.name = "自民党会派"
        mock_row1.conference_id = 10
        mock_row1.is_active = True

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.name = "民主党会派"
        mock_row2.conference_id = 10
        mock_row2.is_active = False

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference_id(10, active_only=False)

        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_active returns only active groups."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自民党会派"
        mock_row.conference_id = 10
        mock_row.is_active = True

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_active()

        assert len(result) == 1
        assert result[0].is_active is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns all groups."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自民党会派"
        mock_row.conference_id = 10
        mock_row.is_active = True

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 1
        assert result[0].name == "自民党会派"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all with limit and offset."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_details(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all_with_details returns detailed information."""
        mock_row = (
            1,
            "自民党会派",
            10,
            "https://example.com/group",
            "説明",
            True,
            "東京都議会",
            "東京都",
        )

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_result.keys = MagicMock(
            return_value=[
                "id",
                "name",
                "conference_id",
                "url",
                "description",
                "is_active",
                "conference_name",
                "governing_body_name",
            ]
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_all_with_details()

        assert len(result) == 1
        assert result[0]["name"] == "自民党会派"
        assert result[0]["conference_name"] == "東京都議会"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_details_filtered(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all_with_details with filters."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_result.keys = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all_with_details(
            conference_id=10, active_only=True, with_url_only=True
        )

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when group is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自民党会派"
        mock_row.conference_id = 10
        mock_row.is_active = True

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "自民党会派"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when group is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    def test_row_to_entity(self, repository: ParliamentaryGroupRepositoryImpl) -> None:
        """Test _row_to_entity converts row to entity correctly."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自民党会派"
        mock_row.conference_id = 10
        mock_row.url = "https://example.com/group"
        mock_row.description = "自由民主党の会派"
        mock_row.is_active = True

        entity = repository._row_to_entity(mock_row)

        assert isinstance(entity, ParliamentaryGroup)
        assert entity.id == 1
        assert entity.name == "自民党会派"
        assert entity.conference_id == 10
        assert entity.url == "https://example.com/group"
        assert entity.is_active is True

    def test_to_entity(self, repository: ParliamentaryGroupRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = ParliamentaryGroupModel(
            id=1,
            name="自民党会派",
            conference_id=10,
            url="https://example.com/group",
            description="自由民主党の会派",
            is_active=True,
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, ParliamentaryGroup)
        assert entity.id == 1
        assert entity.name == "自民党会派"

    def test_to_model(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        sample_group_entity: ParliamentaryGroup,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_group_entity)

        assert isinstance(model, ParliamentaryGroupModel)
        assert model.id == 1
        assert model.name == "自民党会派"
        assert model.conference_id == 10
        assert model.is_active is True

    def test_update_model(
        self,
        repository: ParliamentaryGroupRepositoryImpl,
        sample_group_entity: ParliamentaryGroup,
    ) -> None:
        """Test _update_model updates model fields from entity."""
        model = ParliamentaryGroupModel(
            id=1,
            name="旧会派名",
            conference_id=5,
            description="旧説明",
            is_active=False,
        )

        repository._update_model(model, sample_group_entity)

        assert model.name == "自民党会派"
        assert model.conference_id == 10
        assert model.description == "自由民主党の会派"
        assert model.is_active is True
        assert model.url == "https://example.com/group"
