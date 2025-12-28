"""Tests for PoliticianRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician import Politician
from src.infrastructure.exceptions import UpdateError
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianModel,
    PoliticianRepositoryImpl,
)


class TestPoliticianRepositoryImpl:
    """Test cases for PoliticianRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> PoliticianRepositoryImpl:
        """Create politician repository."""
        return PoliticianRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_politician_dict(self) -> dict[str, Any]:
        """Sample politician data as dict."""
        return {
            "id": 1,
            "name": "山田太郎",
            "political_party_id": 10,
            "electoral_district": "東京1区",
            "profile_url": "https://example.com/yamada",
            "furigana": "やまだたろう",
            "prefecture": "東京都",
            "party_position": None,
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_politician_entity(self) -> Politician:
        """Sample politician entity."""
        return Politician(
            id=1,
            name="山田太郎",
            political_party_id=10,
            district="東京1区",
            profile_page_url="https://example.com/yamada",
            furigana="やまだたろう",
        )

    @pytest.mark.asyncio
    async def test_get_by_name_and_party_found(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test get_by_name_and_party when politician is found."""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_dict
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_party("山田太郎", 10)

        assert result is not None
        assert result.id == 1
        assert result.name == "山田太郎"
        assert result.political_party_id == 10
        assert result.district == "東京1区"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_party_not_found(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_name_and_party when politician is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_party("存在しない人", 10)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_party_without_party_id(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test get_by_name_and_party without party_id."""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_dict
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_party("山田太郎")

        assert result is not None
        assert result.name == "山田太郎"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_party(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test get_by_party returns list of politicians."""
        mock_row1 = MagicMock()
        mock_row1._mapping = sample_politician_dict
        mock_row2_dict = {**sample_politician_dict, "id": 2, "name": "鈴木花子"}
        mock_row2 = MagicMock()
        mock_row2._mapping = mock_row2_dict
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_party(10)

        assert len(result) == 2
        assert result[0].name == "山田太郎"
        assert result[1].name == "鈴木花子"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_party_empty(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_party returns empty list when no politicians."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_party(10)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_name(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test search_by_name with pattern matching."""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_dict
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.search_by_name("山田")

        assert len(result) == 1
        assert result[0].name == "山田太郎"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count returns total number of politicians."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_zero(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count returns 0 when no politicians."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_by_party(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count_by_party returns count for specific party."""
        mock_row = MagicMock()
        mock_row.count = 10
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.count_by_party(10)

        assert result == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_by_party_zero(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count_by_party returns 0 when no politicians in party."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.count_by_party(10)

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test get_all with limit and offset."""
        mock_row = MagicMock()
        mock_row._mapping = {**sample_politician_dict, "party_name": "自民党"}
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1
        assert result[0].name == "山田太郎"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_without_limit(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test get_all without limit."""
        mock_row = MagicMock()
        mock_row._mapping = {**sample_politician_dict, "party_name": "自民党"}
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test get_by_id when politician is found."""
        mock_row = MagicMock()
        mock_row._mapping = {**sample_politician_dict, "party_name": "自民党"}
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "山田太郎"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_id when politician is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_entity: Politician,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test create successfully creates a politician."""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_dict
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.create(sample_politician_entity)

        assert result.id == 1
        assert result.name == "山田太郎"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_entity: Politician,
    ) -> None:
        """Test create raises error when creation fails."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(RuntimeError, match="Failed to create politician"):
            await repository.create(sample_politician_entity)

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_entity: Politician,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test update successfully updates a politician."""
        mock_row = MagicMock()
        mock_row._mapping = {**sample_politician_dict, "name": "山田太郎（更新）"}
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        sample_politician_entity.name = "山田太郎（更新）"
        result = await repository.update(sample_politician_entity)

        assert result.name == "山田太郎（更新）"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(
        self,
        repository: PoliticianRepositoryImpl,
        mock_session: MagicMock,
        sample_politician_entity: Politician,
    ) -> None:
        """Test update raises error when politician not found."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(UpdateError) as exc_info:
            await repository.update(sample_politician_entity)

        assert "Politician with ID 1 not found" in str(exc_info.value)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete successfully deletes a politician."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete(1)

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete returns False when politician not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete(999)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_for_matching(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_all_for_matching returns politicians for matching."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "山田太郎"
        mock_row.position = "議員"
        mock_row.prefecture = "東京都"
        mock_row.electoral_district = "東京1区"
        mock_row.party_name = "自民党"
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all_for_matching()

        assert len(result) == 1
        assert result[0]["name"] == "山田太郎"
        assert result[0]["party_name"] == "自民党"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_party_statistics(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_party_statistics returns statistics for all parties."""
        mock_row = MagicMock()
        mock_row.party_id = 1
        mock_row.party_name = "自民党"
        mock_row.extracted_total = 100
        mock_row.extracted_pending = 10
        mock_row.extracted_reviewed = 20
        mock_row.extracted_approved = 30
        mock_row.extracted_rejected = 5
        mock_row.extracted_converted = 35
        mock_row.politicians_total = 50
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_party_statistics()

        assert len(result) == 1
        assert result[0]["party_name"] == "自民党"
        assert result[0]["politicians_total"] == 50
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_party_statistics_by_id_found(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_party_statistics_by_id when party is found."""
        mock_row = MagicMock()
        mock_row.party_id = 1
        mock_row.party_name = "自民党"
        mock_row.extracted_total = 100
        mock_row.extracted_pending = 10
        mock_row.extracted_reviewed = 20
        mock_row.extracted_approved = 30
        mock_row.extracted_rejected = 5
        mock_row.extracted_converted = 35
        mock_row.politicians_total = 50
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_party_statistics_by_id(1)

        assert result is not None
        assert result["party_name"] == "自民党"
        assert result["politicians_total"] == 50
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_party_statistics_by_id_not_found(
        self, repository: PoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_party_statistics_by_id when party is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_party_statistics_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    def test_to_entity(self, repository: PoliticianRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = PoliticianModel(
            id=1,
            name="山田太郎",
            political_party_id=10,
            electoral_district="東京1区",
            profile_url="https://example.com/yamada",
            furigana="やまだたろう",
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, Politician)
        assert entity.id == 1
        assert entity.name == "山田太郎"
        assert entity.political_party_id == 10
        assert entity.district == "東京1区"
        assert entity.profile_page_url == "https://example.com/yamada"

    def test_to_model(
        self, repository: PoliticianRepositoryImpl, sample_politician_entity: Politician
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_politician_entity)

        assert isinstance(model, PoliticianModel)
        assert model.name == "山田太郎"
        assert model.political_party_id == 10
        assert model.electoral_district == "東京1区"
        assert model.profile_url == "https://example.com/yamada"

    def test_update_model(
        self, repository: PoliticianRepositoryImpl, sample_politician_entity: Politician
    ) -> None:
        """Test _update_model updates model fields from entity."""
        model = PoliticianModel(
            id=1,
            name="旧名前",
            political_party_id=5,
            electoral_district="旧地区",
            profile_url="https://old.com",
            furigana="きゅうなまえ",
        )

        repository._update_model(model, sample_politician_entity)

        assert model.name == "山田太郎"
        assert model.political_party_id == 10
        assert model.electoral_district == "東京1区"
        assert model.profile_url == "https://example.com/yamada"
        assert model.furigana == "やまだたろう"

    def test_row_to_entity_with_mapping(
        self,
        repository: PoliticianRepositoryImpl,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test _row_to_entity with row._mapping."""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_dict

        entity = repository._row_to_entity(mock_row)

        assert isinstance(entity, Politician)
        assert entity.id == 1
        assert entity.name == "山田太郎"
        assert entity.district == "東京1区"

    def test_row_to_entity_with_dict(
        self,
        repository: PoliticianRepositoryImpl,
        sample_politician_dict: dict[str, Any],
    ) -> None:
        """Test _row_to_entity with dict."""
        entity = repository._row_to_entity(sample_politician_dict)

        assert isinstance(entity, Politician)
        assert entity.id == 1
        assert entity.name == "山田太郎"

    def test_row_to_entity_with_none(
        self, repository: PoliticianRepositoryImpl
    ) -> None:
        """Test _row_to_entity raises error with None."""
        with pytest.raises(
            ValueError, match="Cannot convert None to Politician entity"
        ):
            repository._row_to_entity(None)
