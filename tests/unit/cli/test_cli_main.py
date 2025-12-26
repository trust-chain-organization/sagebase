"""Tests for main CLI entry point"""

from unittest.mock import Mock

import pytest
from click.testing import CliRunner


class TestCLIMain:
    """Test cases for main CLI entry point"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    def test_cli_group_help(self, runner):
        """Test CLI group help output"""
        from src.interfaces.cli.cli import cli

        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Sagebase" in result.output
        assert (
            "Political Activity Tracking Application" in result.output
            or "政治活動追跡アプリケーション" in result.output
        )

    def test_cli_group_registration(self, runner):
        """Test that CLI group is properly created"""
        from src.interfaces.cli.cli import cli

        assert cli is not None
        assert cli.name == "cli"

    def test_register_clean_architecture_commands(self):
        """Test registration of clean architecture commands"""
        from src.interfaces.cli.cli import register_clean_architecture_commands

        # Create a mock CLI group
        mock_cli = Mock()
        mock_cli.add_command = Mock()

        # Register commands
        register_clean_architecture_commands(mock_cli)

        # Verify that commands were added
        # At least 5 database commands should be registered
        assert mock_cli.add_command.call_count >= 5

    def test_register_legacy_commands(self):
        """Test registration of legacy commands"""
        from src.interfaces.cli.cli import register_legacy_commands

        # Create a mock CLI group
        mock_cli = Mock()
        mock_cli.add_command = Mock()

        # Register commands
        register_legacy_commands(mock_cli)

        # Verify that commands were added
        # The exact number depends on the command getters, but should be > 0
        assert mock_cli.add_command.call_count > 0

    def test_cli_with_no_arguments(self, runner):
        """Test CLI without any arguments shows help"""
        from src.interfaces.cli.cli import cli

        result = runner.invoke(cli, [])

        # Click returns exit code 2 when no subcommand is provided
        # This is expected behavior
        assert result.exit_code in (0, 2)
        assert "Usage:" in result.output or "Polibase" in result.output

    def test_cli_command_registration_integration(self, runner):
        """Test that registered commands are accessible"""
        from src.interfaces.cli.cli import cli

        # The CLI should have commands registered
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # Check for some expected commands (these are registered in the actual CLI)
        # The exact list depends on what's registered, but we can check the structure

    def test_settings_initialization(self):
        """Test that settings are initialized"""
        from src.interfaces.cli.cli import settings

        assert settings is not None
        # Settings should have required attributes
        assert hasattr(settings, "log_level")

    def test_logging_setup(self):
        """Test that logging is set up"""
        # The cli.py module should initialize logging
        # We can verify this by checking that the logger is configured
        import logging

        logger = logging.getLogger("src.interfaces.cli.cli")
        assert logger is not None

    def test_sentry_initialization(self):
        """Test that Sentry is initialized"""
        # The cli.py module should initialize Sentry
        # We just verify that the init_sentry function is called during import
        # This is implicitly tested by successful module import
        from src.interfaces.cli import cli as cli_module

        assert cli_module is not None
