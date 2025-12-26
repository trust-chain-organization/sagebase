"""Presenter for process execution."""

import subprocess
from typing import Any

from src.application.usecases.execute_processes_usecase import (
    ExecuteProcessesUseCase,
    ProcessExecutionInputDto,
)
from src.common.logging import get_logger
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ProcessPresenter(BasePresenter[dict[str, Any]]):
    """Presenter for process execution."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)
        self.use_case = ExecuteProcessesUseCase()
        self.session = SessionManager()
        self.logger = get_logger(__name__)

    def load_data(self) -> dict[str, Any]:
        """Load available processes."""
        try:
            return self.use_case.get_available_processes()
        except Exception as e:
            self.logger.error(f"Failed to load processes: {e}")
            return {}

    def execute_process(
        self, process_type: str, command: str, parameters: dict[str, Any] | None = None
    ) -> tuple[bool, str | None]:
        """Execute a process."""
        try:
            result = self.use_case.execute_process(
                ProcessExecutionInputDto(
                    process_type=process_type,
                    command=command,
                    parameters=parameters,
                )
            )
            if result.success:
                return True, result.output
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to execute process: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def run_command(self, command: str) -> tuple[bool, str, str]:
        """Run a command and return success, stdout, stderr."""
        try:
            # In a real implementation, this would execute the actual command
            # For now, return a simulated result
            self.logger.info(f"Would execute command: {command}")
            return True, f"Command executed: {command}", ""
        except subprocess.CalledProcessError as e:
            return False, e.stdout or "", e.stderr or ""
        except Exception as e:
            return False, "", str(e)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions."""
        if action == "execute":
            return self.execute_process(
                kwargs.get("process_type", ""),
                kwargs.get("command", ""),
                kwargs.get("parameters"),
            )
        elif action == "list":
            return self.load_data()
        else:
            raise ValueError(f"Unknown action: {action}")
