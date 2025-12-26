"""Common type definitions used across the domain."""

from datetime import date, datetime
from typing import NewType


# Entity ID types
EntityId = NewType("EntityId", int)

# Timestamp types
Timestamp = NewType("Timestamp", datetime)

# Optional types commonly used
OptionalStr = str | None
OptionalInt = int | None
OptionalDate = date | None
