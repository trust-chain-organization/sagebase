"""Database list backups command."""

import subprocess
import sys
from pathlib import Path
from typing import Any

from src.interfaces.cli.base import BaseCommand, Command


class ListBackupsCommand(Command, BaseCommand):
    """Command to list available database backups."""

    def execute(self, **kwargs: Any) -> None:
        """List available database backups."""
        gcs = kwargs.get("gcs", True)

        # Use GCS-enabled backup script
        script_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "scripts"
            / "backup-database-gcs.py"
        )

        args = [sys.executable, str(script_path), "list"]
        if not gcs:
            args.append("--no-gcs")

        subprocess.run(args)
