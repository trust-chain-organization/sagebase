"""Database reset command."""

import subprocess
from typing import Any

from src.interfaces.cli.base import BaseCommand, Command


class ResetDatabaseCommand(Command, BaseCommand):
    """Command to reset database to initial state."""

    def execute(self, **kwargs: Any) -> None:
        """Reset database to initial state.

        WARNING: This will delete all data and restore to initial state!
        """
        if self.confirm(
            "Are you sure you want to reset the database? This will delete all data!"
        ):
            subprocess.run(["./reset-database.sh"])
            self.success("Database reset complete.")
        else:
            self.show_progress("Database reset cancelled.")
