"""Tests for prompt version management commands"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.domain.entities.prompt_version import PromptVersion
from src.interfaces.cli.commands.prompt_commands import PromptCommands


# Common patch paths
ASYNC_SESSION_PATH = "src.infrastructure.config.async_database.get_async_session"
REPO_IMPL_PATH = (
    "src.infrastructure.persistence.prompt_version_repository_impl."
    "PromptVersionRepositoryImpl"
)
MANAGER_PATH = (
    "src.infrastructure.external.versioned_prompt_manager.VersionedPromptManager"
)


@pytest.fixture
def runner():
    """Create a Click CLI runner"""
    return CliRunner()


@pytest.fixture
def sample_prompt_versions():
    """Sample prompt versions for testing"""
    return [
        PromptVersion(
            id=1,
            prompt_key="minutes_divide",
            template="Divide the following minutes: {text}",
            version="1.0.0",
            is_active=True,
            description="Initial version",
            variables=["text"],
            metadata={"author": "test"},
            created_by="system",
        ),
        PromptVersion(
            id=2,
            prompt_key="minutes_divide",
            template="Divide the following minutes: {text}\nContext: {context}",
            version="2.0.0",
            is_active=False,
            description="Added context",
            variables=["text", "context"],
            metadata={"author": "test"},
            created_by="system",
        ),
    ]


@pytest.fixture
def sample_active_versions():
    """Sample active versions for different prompt keys"""
    return [
        PromptVersion(
            id=1,
            prompt_key="minutes_divide",
            template="Divide: {text}",
            version="1.0.0",
            is_active=True,
            variables=["text"],
            created_by="system",
        ),
        PromptVersion(
            id=3,
            prompt_key="speaker_match",
            template="Match speaker: {name}",
            version="1.0.0",
            is_active=True,
            variables=["name"],
            created_by="system",
        ),
    ]


class TestPromptListCommand:
    """Tests for prompt-list command"""

    def test_list_all_active_prompts(self, runner, sample_active_versions):
        """Test listing all active prompt versions"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_all_active_versions = AsyncMock(
                return_value=sample_active_versions
            )

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(PromptCommands.prompt_list, [])

                # Assert
                assert result.exit_code == 0
                assert "Active prompt versions:" in result.output
                assert "minutes_divide" in result.output
                assert "speaker_match" in result.output
                assert "Found 2 prompt version(s)" in result.output

    def test_list_specific_prompt_versions(self, runner, sample_prompt_versions):
        """Test listing versions for a specific prompt key"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_versions_by_key = AsyncMock(
                return_value=sample_prompt_versions
            )

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_list, ["--prompt-key", "minutes_divide"]
                )

                # Assert
                assert result.exit_code == 0
                assert "Versions for prompt 'minutes_divide':" in result.output
                assert "1.0.0" in result.output
                assert "[ACTIVE]" in result.output
                assert "2.0.0" in result.output

    def test_list_no_versions_found(self, runner):
        """Test listing when no versions are found"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_versions_by_key = AsyncMock(return_value=[])

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_list, ["--prompt-key", "nonexistent"]
                )

                # Assert
                assert result.exit_code == 0
                assert "No versions found for prompt: nonexistent" in result.output

    def test_list_with_custom_limit(self, runner, sample_prompt_versions):
        """Test listing with custom limit parameter"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_versions_by_key = AsyncMock(
                return_value=sample_prompt_versions
            )

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_list,
                    ["--prompt-key", "minutes_divide", "--limit", "20"],
                )

                # Assert
                assert result.exit_code == 0
                mock_repo.get_versions_by_key.assert_called_once_with(
                    "minutes_divide", 20
                )


class TestPromptShowCommand:
    """Tests for prompt-show command"""

    def test_show_latest_version(self, runner, sample_prompt_versions):
        """Test showing the latest (active) version"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_active_version = AsyncMock(
                return_value=sample_prompt_versions[0]
            )

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_show, ["minutes_divide", "latest"]
                )

                # Assert
                assert result.exit_code == 0
                assert "Prompt: minutes_divide" in result.output
                assert "Version: 1.0.0" in result.output
                assert "Active: Yes" in result.output
                assert "Initial version" in result.output
                assert "Variables: text" in result.output

    def test_show_specific_version(self, runner, sample_prompt_versions):
        """Test showing a specific version"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_by_key_and_version = AsyncMock(
                return_value=sample_prompt_versions[1]
            )

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_show, ["minutes_divide", "2.0.0"]
                )

                # Assert
                assert result.exit_code == 0
                assert "Version: 2.0.0" in result.output
                assert "Active: No" in result.output
                assert "Added context" in result.output

    def test_show_version_not_found(self, runner):
        """Test showing when version is not found"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_active_version = AsyncMock(return_value=None)

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_show, ["nonexistent", "latest"]
                )

                # Assert
                assert result.exit_code == 0
                assert (
                    "No active version found for prompt: nonexistent" in result.output
                )


class TestPromptActivateCommand:
    """Tests for prompt-activate command"""

    def test_activate_version_success(self, runner):
        """Test successfully activating a version"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.activate_version = AsyncMock(return_value=True)

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_activate, ["minutes_divide", "2.0.0"]
                )

                # Assert
                assert result.exit_code == 0
                assert "Successfully activated minutes_divide:2.0.0" in result.output
                mock_repo.activate_version.assert_called_once_with(
                    "minutes_divide", "2.0.0"
                )

    def test_activate_version_failure(self, runner):
        """Test activating a version that doesn't exist"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.activate_version = AsyncMock(return_value=False)

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_activate, ["nonexistent", "1.0.0"]
                )

                # Assert
                assert result.exit_code == 0
                assert "Failed to activate version: nonexistent:1.0.0" in result.output


class TestPromptMigrateCommand:
    """Tests for prompt-migrate command"""

    def test_migrate_success(self, runner):
        """Test successful migration of prompts"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_all_active_versions = AsyncMock(return_value=[])

            mock_manager = Mock()
            mock_manager.migrate_existing_prompts = AsyncMock(return_value=5)

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                with patch(MANAGER_PATH) as mock_manager_class:
                    mock_manager_class.return_value = mock_manager

                    # Execute
                    result = runner.invoke(PromptCommands.prompt_migrate, [])

                    # Assert
                    assert result.exit_code == 0
                    assert "Successfully migrated 5 prompts" in result.output

    def test_migrate_with_existing_prompts(self, runner, sample_active_versions):
        """Test migration when existing prompts are found"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_all_active_versions = AsyncMock(
                return_value=sample_active_versions
            )

            mock_manager = Mock()
            mock_manager.migrate_existing_prompts = AsyncMock(return_value=2)

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                with patch(MANAGER_PATH) as mock_manager_class:
                    mock_manager_class.return_value = mock_manager

                    # Execute with auto-confirm
                    result = runner.invoke(
                        PromptCommands.prompt_migrate, [], input="y\n"
                    )

                    # Assert
                    assert result.exit_code == 0
                    assert "Found 2 existing prompt versions" in result.output

    def test_migrate_no_prompts(self, runner):
        """Test migration when no prompts are migrated"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_all_active_versions = AsyncMock(return_value=[])

            mock_manager = Mock()
            mock_manager.migrate_existing_prompts = AsyncMock(return_value=0)

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                with patch(MANAGER_PATH) as mock_manager_class:
                    mock_manager_class.return_value = mock_manager

                    # Execute
                    result = runner.invoke(PromptCommands.prompt_migrate, [])

                    # Assert
                    assert result.exit_code == 0
                    assert "No prompts were migrated" in result.output


class TestPromptHistoryCommand:
    """Tests for prompt-history command"""

    def test_history_success(self, runner, sample_prompt_versions):
        """Test showing prompt history"""
        # Add created_at to sample versions
        for i, version in enumerate(sample_prompt_versions):
            version.created_at = datetime(2024, 1, i + 1, 10, 0, 0)

        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_versions_by_key = AsyncMock(
                return_value=sample_prompt_versions
            )

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_history, ["minutes_divide"]
                )

                # Assert
                assert result.exit_code == 0
                assert "Version history for 'minutes_divide':" in result.output
                assert "1. Version 1.0.0 ACTIVE" in result.output
                assert "2. Version 2.0.0" in result.output
                assert "Displayed 2 version(s)" in result.output

    def test_history_no_versions(self, runner):
        """Test showing history when no versions exist"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_versions_by_key = AsyncMock(return_value=[])

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(PromptCommands.prompt_history, ["nonexistent"])

                # Assert
                assert result.exit_code == 0
                assert "No versions found for prompt: nonexistent" in result.output

    def test_history_with_custom_limit(self, runner, sample_prompt_versions):
        """Test showing history with custom limit"""
        with patch(ASYNC_SESSION_PATH) as mock_session:
            # Setup mock
            mock_repo = Mock()
            mock_repo.get_versions_by_key = AsyncMock(
                return_value=sample_prompt_versions
            )

            # Mock async context manager
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=Mock(spec=["add", "commit", "rollback", "close"])
            )
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(REPO_IMPL_PATH) as mock_repo_class:
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    PromptCommands.prompt_history, ["minutes_divide", "--limit", "5"]
                )

                # Assert
                assert result.exit_code == 0
                mock_repo.get_versions_by_key.assert_called_once_with(
                    "minutes_divide", 5
                )
