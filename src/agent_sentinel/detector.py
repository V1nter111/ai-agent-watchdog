"""Detect suspicion, never assert that elapsed time alone proves a hang."""

from dataclasses import dataclass

from .config import Config
from .providers.base import ConversationState


@dataclass
class Observation:
    token: str
    last_progress_at: float
    first_seen: float
    stale_checks: int = 0


class Detector:
    def __init__(self, config: Config):
        self.config = config
        self.observations: dict[str, Observation] = {}

    def suspicious(self, state: ConversationState, now: float) -> bool:
        old = self.observations.get(state.conversation_id)
        if (old is None or old.token != state.progress_token
                or old.last_progress_at != state.last_progress_at):
            old = Observation(state.progress_token, state.last_progress_at, now)
            self.observations[state.conversation_id] = old
        threshold = self.config.stale_seconds
        if state.tool_running:
            threshold = max(threshold, self.config.tool_grace_seconds)
        stale = (state.status in {"running", "blocked"}
                 and state.process_alive is not True
                 and now >= state.last_progress_at
                 and now - state.last_progress_at >= threshold
                 and now - old.first_seen >= self.config.stale_seconds)
        old.stale_checks = old.stale_checks + 1 if stale else 0
        return old.stale_checks >= self.config.confirmation_checks

    def retain(self, active_ids: set[str]) -> None:
        self.observations = {k: v for k, v in self.observations.items() if k in active_ids}
