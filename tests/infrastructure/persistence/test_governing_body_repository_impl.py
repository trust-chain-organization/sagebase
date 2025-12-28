"""Tests for GoverningBodyRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.governing_body import GoverningBody
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyModel,
    GoverningBodyRepositoryImpl,
)


class TestGoverningBodyRepositoryImpl:
    """Test cases for GoverningBodyRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> GoverningBodyRepositoryImpl:
        """Create governing body repository."""
        return GoverningBodyRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_body_entity(self) -> GoverningBody:
        """Sample governing body entity."""
        return GoverningBody(
            id=1,
            name="東京都",
            type="都道府県",
            organization_code="130001",
        )

    @pytest.mark.asyncio
    async def test_get_by_name_and_type_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name_and_type when body is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"
        mock_row.organization_code = "130001"

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_type("東京都", "都道府県")

        assert result is not None
        assert result.id == 1
        assert result.name == "東京都"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_type_not_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name_and_type when body is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_type("存在しない", "都道府県")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_organization_code_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_organization_code when body is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"
        mock_row.organization_code = "130001"

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_organization_code("130001")

        assert result is not None
        assert result.organization_code == "130001"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_name(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test search_by_name with pattern matching."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.search_by_name("東京")

        assert len(result) == 1
        assert result[0].name == "東京都"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_with_conferences(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count_with_conferences returns count."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=10)
        mock_session.execute.return_value = mock_result

        result = await repository.count_with_conferences()

        assert result == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_with_meetings(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count_with_meetings returns count."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_result

        result = await repository.count_with_meetings()

        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns total number."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
        mock_session.execute.assert_called_once()

    def test_to_entity(self, repository: GoverningBodyRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = GoverningBodyModel(
            id=1,
            name="東京都",
            type="都道府県",
            organization_code="130001",
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, GoverningBody)
        assert entity.id == 1
        assert entity.name == "東京都"

    def test_to_model(
        self,
        repository: GoverningBodyRepositoryImpl,
        sample_body_entity: GoverningBody,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_body_entity)

        assert isinstance(model, GoverningBodyModel)
        assert model.name == "東京都"
        assert model.type == "都道府県"

    @pytest.mark.asyncio
    async def test_get_all_returns_bodies(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns all governing bodies."""
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.name = "東京都"
        mock_row1.type = "都道府県"
        mock_row1.organization_code = "130001"

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.name = "大阪府"
        mock_row2.type = "都道府県"
        mock_row2.organization_code = "270000"

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 2
        assert result[0].name == "東京都"
        assert result[1].name == "大阪府"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit_offset(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all with limit and offset parameters."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_empty(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns empty list when no bodies exist."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when body is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"
        mock_row.organization_code = "130001"

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "東京都"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when body is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
        sample_body_entity: GoverningBody,
    ) -> None:
        """Test create successfully creates governing body."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"
        mock_row.organization_code = "130001"
        mock_row.organization_type = None

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.create(sample_body_entity)

        assert result.id == 1
        assert result.name == "東京都"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
        sample_body_entity: GoverningBody,
    ) -> None:
        """Test create raises RuntimeError when creation fails."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(RuntimeError, match="Failed to create governing body"):
            await repository.create(sample_body_entity)

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
        sample_body_entity: GoverningBody,
    ) -> None:
        """Test update successfully updates governing body."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都（更新）"
        mock_row.type = "都道府県"
        mock_row.organization_code = "130001"
        mock_row.organization_type = None

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        sample_body_entity.name = "東京都（更新）"
        result = await repository.update(sample_body_entity)

        assert result.name == "東京都（更新）"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
        sample_body_entity: GoverningBody,
    ) -> None:
        """Test update raises UpdateError when body not found."""
        from src.infrastructure.exceptions import UpdateError

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(UpdateError, match="GoverningBody with ID 1 not found"):
            await repository.update(sample_body_entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete successfully deletes governing body."""
        # Mock count check (no related conferences)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=0)

        # Mock delete result
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        # Setup execute to return different results for check and delete
        mock_session.execute.side_effect = [mock_count_result, mock_delete_result]

        result = await repository.delete(1)

        assert result is True
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_with_related_conferences(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete fails when body has related conferences."""
        # Mock count check (has related conferences)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_count_result

        result = await repository.delete(1)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_organization_code_not_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_organization_code when body is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_organization_code("999999")

        assert result is None
        mock_session.execute.assert_called_once()

    def test_update_model(
        self,
        repository: GoverningBodyRepositoryImpl,
        sample_body_entity: GoverningBody,
    ) -> None:
        """Test _update_model updates model fields from entity."""
        model = GoverningBodyModel(
            id=1,
            name="旧名称",
            type="旧タイプ",
            organization_code="000000",
            organization_type="旧組織タイプ",
        )

        repository._update_model(model, sample_body_entity)

        assert model.name == "東京都"
        assert model.type == "都道府県"
        assert model.organization_code == "130001"
