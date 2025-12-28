"""Tests for PoliticalPartyRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.political_party import PoliticalParty
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyModel,
    PoliticalPartyRepositoryImpl,
)


class TestPoliticalPartyRepositoryImpl:
    """Test cases for PoliticalPartyRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> PoliticalPartyRepositoryImpl:
        """Create political party repository."""
        return PoliticalPartyRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_party_entity(self) -> PoliticalParty:
        """Sample political party entity."""
        return PoliticalParty(
            id=1,
            name="自由民主党",
            members_list_url="https://example.com/members",
        )

    @pytest.mark.asyncio
    async def test_get_by_name_found(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name when party is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自由民主党"
        mock_row.members_list_url = "https://example.com/members"

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name("自由民主党")

        assert result is not None
        assert result.id == 1
        assert result.name == "自由民主党"
        assert result.members_list_url == "https://example.com/members"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name when party is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name("存在しない政党")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_members_url(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_with_members_url returns parties with URL."""
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.name = "自由民主党"
        mock_row1.members_list_url = "https://example.com/members1"

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.name = "民主党"
        mock_row2.members_list_url = "https://example.com/members2"

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_with_members_url()

        assert len(result) == 2
        assert result[0].members_list_url is not None
        assert result[1].members_list_url is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_members_url_empty(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_with_members_url returns empty list when no parties with URL."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_with_members_url()

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_name(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test search_by_name with pattern matching."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自由民主党"
        mock_row.members_list_url = "https://example.com/members"

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.search_by_name("自由")

        assert len(result) == 1
        assert result[0].name == "自由民主党"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_name_no_match(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test search_by_name returns empty list when no match."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.search_by_name("存在しない")

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns all parties."""
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.name = "自由民主党"
        mock_row1.members_list_url = None

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.name = "民主党"
        mock_row2.members_list_url = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 2
        assert result[0].name == "自由民主党"
        assert result[1].name == "民主党"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all with limit and offset."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自由民主党"
        mock_row.members_list_url = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_empty(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns empty list when no parties."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when party is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自由民主党"
        mock_row.members_list_url = "https://example.com/members"

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "自由民主党"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: PoliticalPartyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when party is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    def test_row_to_entity(self, repository: PoliticalPartyRepositoryImpl) -> None:
        """Test _row_to_entity converts row to entity correctly."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自由民主党"
        mock_row.members_list_url = "https://example.com/members"

        entity = repository._row_to_entity(mock_row)

        assert isinstance(entity, PoliticalParty)
        assert entity.id == 1
        assert entity.name == "自由民主党"
        assert entity.members_list_url == "https://example.com/members"

    def test_row_to_entity_without_url(
        self, repository: PoliticalPartyRepositoryImpl
    ) -> None:
        """Test _row_to_entity without members_list_url."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "自由民主党"
        # Simulate missing attribute
        del mock_row.members_list_url

        entity = repository._row_to_entity(mock_row)

        assert entity.members_list_url is None

    def test_to_entity(self, repository: PoliticalPartyRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = PoliticalPartyModel(
            id=1,
            name="自由民主党",
            members_list_url="https://example.com/members",
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, PoliticalParty)
        assert entity.id == 1
        assert entity.name == "自由民主党"
        assert entity.members_list_url == "https://example.com/members"

    def test_to_model(
        self,
        repository: PoliticalPartyRepositoryImpl,
        sample_party_entity: PoliticalParty,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_party_entity)

        assert isinstance(model, PoliticalPartyModel)
        assert model.id == 1
        assert model.name == "自由民主党"
        assert model.members_list_url == "https://example.com/members"

    def test_to_model_without_id(
        self, repository: PoliticalPartyRepositoryImpl
    ) -> None:
        """Test _to_model without id."""
        entity = PoliticalParty(
            name="自由民主党",
            members_list_url="https://example.com/members",
        )

        model = repository._to_model(entity)

        assert isinstance(model, PoliticalPartyModel)
        assert not hasattr(model, "id") or model.id is None
        assert model.name == "自由民主党"

    def test_update_model(
        self,
        repository: PoliticalPartyRepositoryImpl,
        sample_party_entity: PoliticalParty,
    ) -> None:
        """Test _update_model updates model fields from entity."""
        model = PoliticalPartyModel(
            id=1,
            name="旧政党名",
            members_list_url="https://old.com/members",
        )

        repository._update_model(model, sample_party_entity)

        assert model.name == "自由民主党"
        assert model.members_list_url == "https://example.com/members"

    def test_update_model_with_none_url(
        self, repository: PoliticalPartyRepositoryImpl
    ) -> None:
        """Test _update_model with None members_list_url."""
        entity = PoliticalParty(
            id=1,
            name="自由民主党",
            members_list_url=None,
        )
        model = PoliticalPartyModel(
            id=1,
            name="旧政党名",
            members_list_url="https://old.com/members",
        )

        repository._update_model(model, entity)

        assert model.members_list_url is None
