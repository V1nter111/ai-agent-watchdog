"""Provider-neutral state and interface. No engine knowledge of agent internals."""

from dataclasses import dataclass
from typing import Protocol


class ProviderError(RuntimeError):
    """A sanitized failure; never includes command output or personal paths."""


@dataclass(frozen=True)
class ConversationState:
    conversation_id: str
    status: str
    last_progress_at: float
    progress_token: str
    tool_running: bool = False
    process_alive: bool | None = None


class Provider(Protocol):
    def health(self) -> dict: ...
    def states(self, now: float) -> list[ConversationState]: ...
    def send_recovery(self, state: ConversationState, message: str) -> None: ...
