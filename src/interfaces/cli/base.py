"""Base classes and decorators for CLI commands in Clean Architecture."""

import asyncio
import sys

from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import click

from src.application.exceptions import ConfigurationError, ProcessingError
from src.domain.exceptions import PolibaseError
from src.infrastructure.exceptions import APIKeyError, RecordNotFoundError
from src.infrastructure.exceptions import ConnectionError as InfraConnectionError


ValidationError = ProcessingError  # Alias for backward compatibility

# Type variables for methods that still need them
P = ParamSpec("P")
T = TypeVar("T")


class Command(ABC):
    """Abstract base class for all CLI commands following Clean Architecture."""

    @abstractmethod
    def execute(self, **kwargs: Any) -> None:
        """Execute the command with the given parameters."""
        pass


class BaseCommand:
    """Base class for CLI commands with common functionality."""

    @staticmethod
    def async_command(f: Callable[P, T]) -> Callable[P, T]:
        """Decorator to run async functions in CLI commands."""

        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return asyncio.run(f(*args, **kwargs))  # type: ignore

        return wrapper

    @staticmethod
    def handle_errors(f: Callable[P, T]) -> Callable[P, T]:
        """Decorator to handle common errors in CLI commands."""

        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return f(*args, **kwargs)
            except APIKeyError as e:
                click.echo(f"API Key Error: {str(e)}", err=True)
                click.echo(
                    "Please set the required API key in your environment variables.",
                    err=True,
                )
                sys.exit(2)
            except ConfigurationError as e:
                click.echo(f"Configuration Error: {str(e)}", err=True)
                click.echo("Please check your configuration settings.", err=True)
                sys.exit(2)
            except InfraConnectionError as e:
                click.echo(f"Connection Error: {str(e)}", err=True)
                click.echo(
                    "Please check your network connection and database settings.",
                    err=True,
                )
                sys.exit(3)
            except RecordNotFoundError as e:
                click.echo(f"Not Found: {str(e)}", err=True)
                sys.exit(4)
            except ValidationError as e:
                click.echo(f"Validation Error: {str(e)}", err=True)
                sys.exit(5)
            except PolibaseError as e:
                click.echo(f"Error: {str(e)}", err=True)
                sys.exit(1)
            except KeyboardInterrupt:
                click.echo("\nOperation cancelled by user", err=True)
                sys.exit(0)
            except Exception as e:
                click.echo(f"Unexpected Error: {str(e)}", err=True)
                click.echo(
                    "This is an unexpected error. Please report it.",
                    err=True,
                )
                sys.exit(99)

        return wrapper

    @staticmethod
    def show_progress(message: str) -> None:
        """Show a progress message."""
        click.echo(message)

    @staticmethod
    def success(message: str) -> None:
        """Show a success message."""
        click.echo(f"✓ {message}")

    @staticmethod
    def error(message: str, exit_code: int = 1) -> None:
        """Show an error message and optionally exit."""
        click.echo(f"✗ {message}", err=True)
        if exit_code:
            sys.exit(exit_code)

    @staticmethod
    def confirm(message: str) -> bool:
        """Ask for user confirmation."""
        return click.confirm(message)

    @staticmethod
    def warning(message: str) -> None:
        """Show a warning message."""
        click.echo(f"⚠ {message}", err=True)


def with_async_execution(f: Callable[..., T]) -> Callable[..., T]:  # noqa: UP047
    """Decorator to run async functions in CLI commands."""
    return BaseCommand.async_command(f)


def with_error_handling(f: Callable[..., T]) -> Callable[..., T]:  # noqa: UP047
    """Decorator to handle common errors in CLI commands."""
    return BaseCommand.handle_errors(f)
