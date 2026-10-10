"""Antigravity 2.x: explicit state snapshots and the documented agentapi CLI."""

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from ..config import ProviderConfig
from .base import ConversationState, ProviderError


def parse_state(data: dict, now: float, max_age: float) -> ConversationState:
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1):
        raise ValueError("Unsupported state schema")
    cid = data.get("conversation_id")
    # UUIDs and opaque IDs are accepted; option-looking IDs are never accepted.
    if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", cid):
        raise ValueError("Invalid conversation identity")
    status = data.get("status")
    if status not in {"running", "blocked", "idle", "completed", "waiting_for_user"}:
        raise ValueError("Unknown state")
    progress = data.get("last_progress_at")
    observed = data.get("observed_at")
    for timestamp in (progress, observed):
        if (type(timestamp) not in {int, float} or not math.isfinite(timestamp)
                or timestamp < 0 or timestamp > now):
            raise ValueError("Invalid timestamp")
    if progress > observed or now - observed > max_age:
        raise ValueError("Untrusted or expired state")
    token = data.get("progress_token")
    if not isinstance(token, str) or not token or len(token) > 256:
        raise ValueError("Invalid progress token")
    tool = data.get("tool_running", False)
    alive = data.get("process_alive")
    if type(tool) is not bool or (alive is not None and type(alive) is not bool):
        raise ValueError("Invalid liveness flags")
    return ConversationState(cid, status, progress, token, tool, alive)


class AntigravityProvider:
    def __init__(self, config: ProviderConfig, state_directory: Path):
        self.config = config
        self.state_directory = state_directory
        self.invalid_states = 0

    def health(self) -> dict:
        executable = shutil.which(self.config.agentapi_command[0])
        directory = self.state_directory.is_dir()
        return {"name": "antigravity", "agentapi_available": executable is not None,
                "state_source_available": directory,
                "ready": executable is not None and directory,
                "invalid_states": self.invalid_states}

    def states(self, now: float) -> list[ConversationState]:
        if not self.state_directory.is_dir():
            raise ProviderError("state_source_unavailable")
        self.invalid_states = 0
        states = {}
        duplicates = set()
        try:
            for path in sorted(self.state_directory.glob("*.json")):
                try:
                    if path.is_symlink() or path.stat().st_size > 65536:
                        raise ValueError()
                    state = parse_state(json.loads(path.read_text(encoding="utf-8")), now,
                                        self.config.max_state_age_seconds)
                    if state.conversation_id in states:
                        duplicates.add(state.conversation_id)
                    states[state.conversation_id] = state
                except (OSError, ValueError, TypeError):
                    self.invalid_states += 1
        except OSError as exc:
            raise ProviderError("state_source_unreadable") from exc
        for cid in duplicates:
            states.pop(cid)
            self.invalid_states += 1
        return list(states.values())

    def send_recovery(self, state: ConversationState, message: str) -> None:
        try:
            subprocess.run([*self.config.agentapi_command, "send-message",
                            state.conversation_id, message], check=True,
                           timeout=self.config.command_timeout_seconds,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, shell=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise ProviderError("agentapi_send_failed") from exc
