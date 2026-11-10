from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True)
class TenantContext:
    """Construct only after authentication and membership validation (P03)."""

    organization_id: UUID
    actor_id: UUID
    principal: Literal["user", "system"] = "user"


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
