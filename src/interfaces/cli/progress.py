"""Progress indicators for long-running operations"""

import sys
import threading
import time

from collections.abc import Callable, Iterable
from contextlib import contextmanager
from types import TracebackType
from typing import Any, TypeVar

import click

T = TypeVar("T")


class Spinner:
    """Simple spinner for showing progress during long operations"""

    def __init__(self, message: str = "Processing"):
        self.message = message
        self.running = False
        self.thread = None
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current = 0

    def _spin(self):
        """Run the spinner animation"""
        while self.running:
            char = self.spinner_chars[self.current % len(self.spinner_chars)]
            sys.stdout.write(f"\r{char} {self.message}...")
            sys.stdout.flush()
            self.current += 1
            time.sleep(0.1)

    def start(self):
        """Start the spinner"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._spin)
            self.thread.daemon = True
            self.thread.start()

    def stop(self, final_message: str | None = None):
        """Stop the spinner and optionally show a final message"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
            sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
            sys.stdout.flush()
            if final_message:
                click.echo(final_message)


@contextmanager
def spinner(message: str = "Processing", final_message: str | None = None):
    """Context manager for showing a spinner during operations

    Usage:
        with spinner("Loading data"):
            # long running operation
            time.sleep(5)
    """
    s = Spinner(message)
    s.start()
    try:
        yield s
    finally:
        s.stop(final_message)


def progress_bar[T](
    iterable: Iterable[T],
    label: str = "Processing",
    length: int | None = None,
    fill_char: str = "█",
    empty_char: str = "░",
    width: int = 30,
) -> Any:
    """Create a progress bar for iterables

    Usage:
        for item in progress_bar(items, label="Processing items"):
            process(item)
    """
    return click.progressbar(
        iterable,
        label=label,
        length=length,
        fill_char=fill_char,
        empty_char=empty_char,
        width=width,
        show_percent=True,
        show_pos=True,
    )


def with_progress(
    message: str = "Processing", success_message: str | None = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to show progress spinner during function execution

    Usage:
        @with_progress("Loading data", "Data loaded successfully")
        def load_data():
            # long running operation
            time.sleep(5)
            return data
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with spinner(message, success_message):
                return func(*args, **kwargs)

        return wrapper

    return decorator


class ProgressTracker:
    """Track progress for multi-step operations"""

    def __init__(self, total_steps: int, description: str = "Progress"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.bar = None

    def __enter__(self):
        self.bar = click.progressbar(
            length=self.total_steps,
            label=self.description,
            show_percent=True,
            show_pos=True,
            fill_char="█",
            empty_char="░",
        )
        self.bar.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.bar:
            self.bar.__exit__(exc_type, exc_val, exc_tb)

    def update(self, steps: int = 1, message: str | None = None):
        """Update progress by given number of steps"""
        if self.bar:
            self.bar.update(steps)
            if message:
                # Clear the line and show the message
                sys.stdout.write("\r" + " " * 80 + "\r")
                click.echo(f"  → {message}")
                # Redraw the progress bar
                self.bar.render_progress()
        self.current_step += steps

    def set_description(self, description: str):
        """Update the progress description"""
        self.description = description
        if self.bar:
            self.bar.label = description
