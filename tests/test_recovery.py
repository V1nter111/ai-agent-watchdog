import json
from dataclasses import replace

import pytest

from agent_sentinel.config import Config
from agent_sentinel.providers.base import ConversationState
from agent_sentinel.recovery import Recovery, recovery_message


def test_prompt():
    message = recovery_message()
    assert message.startswith("ANTI_HANG_RECOVERY:")
    assert "Do not restart successful operations." in message
    assert "Do not perform destructive actions." in message
    assert "continue monitoring." in message


def test_cooldown_limit_and_restart(tmp_path):
    path = tmp_path / "recovery.json"
    state = ConversationState("test-session", "running", 0, "step")
    recovery = Recovery(Config(), path)
    assert recovery.reserve(state, 1000)
    assert not recovery.reserve(state, 1599)
    recovery = Recovery(Config(), path)
    assert recovery.reserve(state, 1600)
    assert not recovery.reserve(state, 3000)
    assert "test-session" not in path.read_text()
    assert not recovery.reserve(replace(state, progress_token="new"), 1601)
    assert recovery.reserve(replace(state, progress_token="new"), 2200)


def test_disabled_attempts_and_clock_rollback(tmp_path):
    state = ConversationState("test-session", "blocked", 0, "step")
    assert not Recovery(Config(max_recovery_attempts=0), tmp_path / "zero.json").reserve(state, 0)
    recovery = Recovery(Config(), tmp_path / "normal.json")
    assert recovery.reserve(state, 1000)
    assert not recovery.reserve(state, 500)


@pytest.mark.parametrize("content", ["broken", "[]", '{"bad": {}}'])
def test_corrupt_ledger_fails_closed(tmp_path, content):
    path = tmp_path / "ledger.json"
    path.write_text(content)
    with pytest.raises(ValueError, match="recovery disabled"):
        Recovery(Config(), path)


def test_reservation_written_before_delivery(tmp_path):
    path = tmp_path / "ledger.json"
    recovery = Recovery(Config(), path)
    assert recovery.reserve(ConversationState("test-session", "running", 0, "step"), 1)
    assert next(iter(json.loads(path.read_text()).values()))["attempts"] == 1
