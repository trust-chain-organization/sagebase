"""Database backup command."""

import subprocess
import sys
from pathlib import Path
from typing import Any

from src.interfaces.cli.base import BaseCommand, Command


class BackupCommand(Command, BaseCommand):
    """Command to create database backup."""

    def execute(self, **kwargs: Any) -> None:
        """Create database backup."""
        gcs = kwargs.get("gcs", True)

        # Use GCS-enabled backup script
        script_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "scripts"
            / "backup-database-gcs.py"
        )

        self.show_progress("Creating database backup...")
        args = [sys.executable, str(script_path), "backup"]
        if not gcs:
            args.append("--no-gcs")

        result = subprocess.run(args)
        if result.returncode == 0:
            self.success("Backup completed successfully!")
        else:
            self.error("Backup failed")
