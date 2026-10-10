"""Persist recovery reservations before sending to avoid retry storms on restart."""

import hashlib
import json
import math
from pathlib import Path

from .config import Config
from .logger import atomic_json
from .providers.base import ConversationState

RECOVERY_MESSAGE = """ANTI_HANG_RECOVERY:

Check current task state.

If process is still running:
continue monitoring.

If completed:
continue original task.

If blocked:
diagnose and recover safely.

Do not restart successful operations.
Do not perform destructive actions."""


def recovery_message() -> str:
    return RECOVERY_MESSAGE


def identity(state: ConversationState) -> str:
    return hashlib.sha256(state.conversation_id.encode()).hexdigest()


class Recovery:
    def __init__(self, config: Config, path: Path):
        self.config = config
        self.path = path
        self.records = {}
        if path.exists():
            try:
                self.records = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(self.records, dict):
                    raise TypeError()
                for key, record in self.records.items():
                    if (len(key) != 64 or not isinstance(record, dict)
                            or set(record) != {"episode", "attempts", "last_attempt"}
                            or not isinstance(record["episode"], str)
                            or type(record["attempts"]) is not int or record["attempts"] < 0
                            or type(record["last_attempt"]) not in {int, float}
                            or not math.isfinite(record["last_attempt"])):
                        raise ValueError()
            except (OSError, ValueError, TypeError) as exc:
                raise ValueError("Invalid recovery ledger; recovery disabled") from exc

    def reserve(self, state: ConversationState, now: float) -> bool:
        key = identity(state)
        episode = hashlib.sha256(
            f"{state.progress_token}:{state.last_progress_at}".encode()).hexdigest()
        old = self.records.get(key)
        # Cooldown applies even across progress episodes; clock rollback also suppresses sends.
        if old and now - old["last_attempt"] < self.config.cooldown_seconds:
            return False
        attempts = old["attempts"] if old and old["episode"] == episode else 0
        if attempts >= self.config.max_recovery_attempts:
            return False
        self.records[key] = {"episode": episode, "attempts": attempts + 1, "last_attempt": now}
        atomic_json(self.path, self.records)
        return True
