"""Main CLI entry point for Sagebase using Clean Architecture."""

import logging
import sys

from collections.abc import Callable

import click

from src.common.logging import setup_logging
from src.infrastructure.config.sentry import init_sentry
from src.infrastructure.config.settings import get_settings
from src.interfaces.cli.commands.conference_member_commands import (
    get_conference_member_commands,
)
from src.interfaces.cli.commands.coverage_commands import get_coverage_commands
from src.interfaces.cli.commands.di_example_commands import get_di_example_commands
from src.interfaces.cli.commands.evaluation_commands import get_evaluation_commands
from src.interfaces.cli.commands.parliamentary_group_commands import (
    get_parliamentary_group_commands,
)
from src.interfaces.cli.commands.parliamentary_group_member_commands import (
    get_parliamentary_group_member_commands,
)
from src.interfaces.cli.commands.prompt_commands import get_prompt_commands
from src.interfaces.cli.commands.proposal_commands import get_proposal_commands
from src.interfaces.cli.commands.seed_commands import get_seed_commands


# Initialize settings
settings = get_settings()

# Initialize structured logging with Sentry integration
setup_logging(
    log_level=settings.log_level, json_format=settings.is_production, enable_sentry=True
)

# Initialize Sentry SDK
init_sentry()

# Get logger after setup
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Sagebase - Political Activity Tracking Application.

    政治活動追跡アプリケーション
    """
    pass


def register_clean_architecture_commands(cli_group: click.Group) -> None:
    """Register Clean Architecture-based commands.

    Args:
        cli_group: Click group to register commands to
    """
    # Import database commands individually to maintain compatibility
    from src.interfaces.cli.commands.database import (
        backup,
        list_backups,
        reset,
        restore,
        test_connection,
    )

    # Register database commands individually for now
    cli_group.add_command(test_connection)
    cli_group.add_command(backup, "backup-database")
    cli_group.add_command(restore, "restore-database")
    cli_group.add_command(list_backups, "list-backups")
    cli_group.add_command(reset, "reset-database")

    # Register commands from other groups that remain unchanged
    from src.interfaces.cli.commands.minutes_commands import MinutesCommands
    from src.interfaces.cli.commands.scraping_commands import ScrapingCommands
    from src.interfaces.cli.commands.ui_commands import UICommands

    cli_group.add_command(MinutesCommands.process_minutes, "process-minutes")
    cli_group.add_command(MinutesCommands.update_speakers, "update-speakers")
    cli_group.add_command(ScrapingCommands.scrape_minutes, "scrape-minutes")
    cli_group.add_command(ScrapingCommands.batch_scrape, "batch-scrape")
    cli_group.add_command(UICommands.streamlit, "streamlit")


def register_legacy_commands(cli_group: click.Group) -> None:
    """Register legacy commands that haven't been migrated yet.

    Args:
        cli_group: Click group to register commands to
    """
    # Commands still using the old structure
    command_getters: list[Callable[[], list[click.Command]]] = [
        get_conference_member_commands,
        get_parliamentary_group_commands,
        get_parliamentary_group_member_commands,
        get_proposal_commands,
        get_seed_commands,
        get_coverage_commands,
        get_evaluation_commands,
        get_prompt_commands,
        get_di_example_commands,
    ]

    for getter in command_getters:
        try:
            commands: list[click.Command] = getter()
            for command in commands:
                cli_group.add_command(command)
        except Exception as e:
            logger.error(f"Failed to register commands from {getter.__name__}: {e}")


# Register all commands
register_clean_architecture_commands(cli)
register_legacy_commands(cli)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
