"""Tests for PromptVersionRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.prompt_version import PromptVersion
from src.infrastructure.persistence.prompt_version_repository_impl import (
    PromptVersionModel,
    PromptVersionRepositoryImpl,
)


class TestPromptVersionRepositoryImpl:
    """Test cases for PromptVersionRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> PromptVersionRepositoryImpl:
        """Create prompt version repository."""
        return PromptVersionRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_version_entity(self) -> PromptVersion:
        """Sample prompt version entity."""
        return PromptVersion(
            id=1,
            prompt_key="speaker_matching",
            template="プロンプト内容",
            version="1.0.0",
            is_active=True,
        )

    @pytest.mark.asyncio
    async def test_get_active_version_found(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_active_version when version is found."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.prompt_key = "speaker_matching"
        mock_model.template = "プロンプト内容"
        mock_model.version = "1.0.0"
        mock_model.description = None
        mock_model.variables = []
        mock_model.metadata = {}
        mock_model.created_by = None
        mock_model.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_model)
        mock_session.execute.return_value = mock_result

        result = await repository.get_active_version("speaker_matching")

        assert result is not None
        assert result.prompt_key == "speaker_matching"
        assert result.is_active is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_version_not_found(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_active_version when version is not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_active_version("nonexistent")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_key_and_version_found(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_key_and_version when version is found."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.prompt_key = "speaker_matching"
        mock_model.template = "プロンプト内容"
        mock_model.version = "1.0.0"
        mock_model.description = None
        mock_model.variables = []
        mock_model.metadata = {}
        mock_model.created_by = None
        mock_model.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_model)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_key_and_version("speaker_matching", "1.0.0")

        assert result is not None
        assert result.version == "1.0.0"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_versions_by_key(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_versions_by_key returns all versions."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.prompt_key = "speaker_matching"
        mock_model.template = "プロンプト内容"
        mock_model.version = "1.0.0"
        mock_model.description = None
        mock_model.variables = []
        mock_model.metadata = {}
        mock_model.created_by = None
        mock_model.is_active = True

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[mock_model]))
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_versions_by_key("speaker_matching")

        assert len(result) == 1
        assert result[0].prompt_key == "speaker_matching"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_active_versions(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all_active_versions returns all active versions."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.prompt_key = "speaker_matching"
        mock_model.template = "プロンプト内容"
        mock_model.version = "1.0.0"
        mock_model.description = None
        mock_model.variables = []
        mock_model.metadata = {}
        mock_model.created_by = None
        mock_model.is_active = True

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[mock_model]))
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_all_active_versions()

        assert len(result) == 1
        assert result[0].is_active is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_version_success(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test activate_version successfully activates version."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.activate_version("speaker_matching", "1.0.0")

        assert result is True
        assert mock_session.execute.call_count >= 2
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_activate_version_not_found(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test activate_version when version is not found."""
        # Mock check for existing version (returns None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.activate_version("nonexistent", "1.0.0")

        # When version is not found, should return False
        assert result is False
        mock_session.execute.assert_called_once()  # Only the check query is executed

    @pytest.mark.asyncio
    async def test_deactivate_all_versions(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test deactivate_all_versions deactivates all versions."""
        # Create 5 mock models
        mock_models = []
        for _i in range(5):
            model = MagicMock()
            model.is_active = True
            mock_models.append(model)

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=mock_models))
        )
        # Use AsyncMock for async execute
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.deactivate_all_versions("speaker_matching")

        assert result == 5
        # Verify all models were deactivated
        for model in mock_models:
            assert model.is_active is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_version_success(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
        sample_version_entity: PromptVersion,
    ) -> None:
        """Test create_version successfully creates version."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.prompt_key = "speaker_matching"
        mock_row.template = "プロンプト内容"
        mock_row.version = "1.0.0"
        mock_row.description = None
        mock_row.variables = []
        mock_row.metadata = {}
        mock_row.created_by = None
        mock_row.is_active = True

        # Mock deactivate_all_versions
        repository.deactivate_all_versions = AsyncMock(return_value=1)

        # Mock create method
        created_entity = PromptVersion(
            id=1,
            prompt_key="speaker_matching",
            template="プロンプト内容",
            version="1.0.0",
            is_active=True,
        )
        repository.create = AsyncMock(return_value=created_entity)

        result = await repository.create_version(
            prompt_key="speaker_matching",
            template="プロンプト内容",
            version="1.0.0",
            activate=True,
        )

        assert result.id == 1
        assert result.prompt_key == "speaker_matching"
        repository.deactivate_all_versions.assert_called_once_with("speaker_matching")
        repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_search(
        self,
        repository: PromptVersionRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test search returns matching versions."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.prompt_key = "speaker_matching"
        mock_model.template = "プロンプト内容"
        mock_model.version = "1.0.0"
        mock_model.description = None
        mock_model.variables = []
        mock_model.metadata = {}
        mock_model.created_by = None
        mock_model.is_active = True

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[mock_model]))
        )
        mock_session.execute.return_value = mock_result

        result = await repository.search(prompt_key="speaker")

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    def test_to_entity(self, repository: PromptVersionRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = PromptVersionModel(
            id=1,
            prompt_key="speaker_matching",
            template="プロンプト内容",
            version="1.0.0",
            is_active=True,
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, PromptVersion)
        assert entity.id == 1
        assert entity.prompt_key == "speaker_matching"

    def test_to_model(
        self,
        repository: PromptVersionRepositoryImpl,
        sample_version_entity: PromptVersion,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_version_entity)

        assert isinstance(model, PromptVersionModel)
        assert model.prompt_key == "speaker_matching"
        assert model.version == "1.0.0"
