"""Capture documented Antigravity hook metadata without transcripts or tool arguments."""

import hashlib
import re
import time
from pathlib import Path

from .logger import atomic_json
from .runtime import FileLock

EVENTS = ("PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop")


def record_hook(event: str, payload: dict, directory: Path, now: float | None = None) -> dict:
    if event not in EVENTS or not isinstance(payload, dict):
        raise ValueError("Invalid hook event")
    cid = payload.get("conversationId")
    if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", cid):
        raise ValueError("Invalid hook identity")
    now = time.time() if now is None else now
    status = "running"
    # PostInvocation may be followed by tool execution; use the longer grace conservatively.
    tool = event in {"PreToolUse", "PostInvocation"}
    if event == "PreToolUse":
        tool_call = payload.get("toolCall")
        if not isinstance(tool_call, dict) or not isinstance(tool_call.get("name"), str):
            raise ValueError("Missing tool metadata")
        if tool_call["name"] in {"ask_question", "ask_permission"}:
            status = "waiting_for_user"
    if event == "Stop":
        if type(payload.get("fullyIdle")) is not bool:
            raise ValueError("Missing Stop liveness")
        status = "completed" if payload["fullyIdle"] else "running"
        tool = not payload["fullyIdle"]
    data = {"schema_version": 1, "conversation_id": cid, "status": status,
            "observed_at": now, "last_progress_at": now,
            "progress_token": f"{event}:{now}", "tool_running": tool,
            "process_alive": None}
    filename = hashlib.sha256(cid.encode()).hexdigest()
    # Concurrent hook writers never expose a partial snapshot. A busy hook fails rather than gates work.
    with FileLock(directory / (filename + ".lock")):
        atomic_json(directory / (filename + ".json"), data)
    # PreToolUse requires a decision: ask respects existing grants, never auto-allows a tool.
    if event == "PreToolUse":
        return {"decision": "ask"}
    if event == "Stop":
        return {"decision": "stop"}
    return {}
