"""Database restore command."""

import subprocess
import sys
from pathlib import Path
from typing import Any

from src.interfaces.cli.base import BaseCommand, Command


class RestoreCommand(Command, BaseCommand):
    """Command to restore database from backup."""

    def execute(self, **kwargs: Any) -> None:
        """Restore database from backup."""
        filename = kwargs.get("filename")
        if not filename:
            self.error("Error: filename required for restore")
            return

        # Use GCS-enabled backup script
        script_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "scripts"
            / "backup-database-gcs.py"
        )

        self.show_progress(f"Restoring from backup: {filename}")
        result = subprocess.run([sys.executable, str(script_path), "restore", filename])
        if result.returncode == 0:
            self.success("Restore completed successfully!")
        else:
            self.error("Restore failed")
