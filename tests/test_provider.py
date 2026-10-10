import json
import subprocess
import sys

import pytest

from agent_sentinel.config import ProviderConfig
from agent_sentinel.hooks import record_hook
from agent_sentinel.providers import antigravity
from agent_sentinel.providers.antigravity import AntigravityProvider, parse_state
from agent_sentinel.providers.base import ProviderError


def snapshot(**changes):
    return {"schema_version": 1, "conversation_id": "test-session", "status": "running",
            "last_progress_at": 0, "observed_at": 50, "progress_token": "step-1",
            "tool_running": True, **changes}


@pytest.mark.parametrize("changes", [
    {"conversation_id": "--help"}, {"status": "unknown"}, {"last_progress_at": 200},
    {"observed_at": -1}, {"last_progress_at": float("nan")}, {"process_alive": 1},
    {"tool_running": "true"}, {"progress_token": ""}, {"schema_version": 2},
])
def test_untrusted_snapshots(changes):
    with pytest.raises(ValueError):
        parse_state(snapshot(**changes), 100, 1000)


def test_expired_state():
    with pytest.raises(ValueError):
        parse_state(snapshot(), 10000, 100)


def test_discovery_invalid_and_duplicate(tmp_path):
    provider = AntigravityProvider(ProviderConfig(), tmp_path)
    (tmp_path / "one.json").write_text(json.dumps(snapshot()))
    (tmp_path / "invalid.json").write_text("{")
    assert len(provider.states(100)) == 1
    assert provider.invalid_states == 1
    (tmp_path / "duplicate.json").write_text(json.dumps(snapshot()))
    assert not provider.states(100)
    assert provider.invalid_states == 2


def test_missing_directory(tmp_path):
    provider = AntigravityProvider(ProviderConfig(), tmp_path / "missing")
    assert not provider.health()["ready"]
    with pytest.raises(ProviderError):
        provider.states(100)


def test_agentapi_delivery_argv(tmp_path):
    output = tmp_path / "captured.json"
    executable = tmp_path / "fake_api.py"
    executable.write_text("import json, pathlib, sys\npathlib.Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))")
    config = ProviderConfig(agentapi_command=[sys.executable, str(executable), str(output)])
    provider = AntigravityProvider(config, tmp_path)
    state = parse_state(snapshot(), 100, 1000)
    message = "safe prompt\nwith spaces & shell characters"
    provider.send_recovery(state, message)
    assert json.loads(output.read_text()) == ["send-message", "test-session", message]


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("redacted", 1), OSError(),
                                   subprocess.CalledProcessError(1, "redacted")])
def test_send_failure_sanitized(tmp_path, monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(ProviderError, match="agentapi_send_failed"):
        AntigravityProvider(ProviderConfig(), tmp_path).send_recovery(
            parse_state(snapshot(), 100, 1000), "message")


def test_hooks_discard_sensitive_payload_and_mark_completion(tmp_path):
    payload = {"conversationId": "test-session", "toolCall": {"name": "run_command",
               "args": {"secret": "DO_NOT_STORE"}}, "workspacePaths": ["DO_NOT_STORE"]}
    assert record_hook("PreToolUse", payload, tmp_path, 100) == {"decision": "ask"}
    provider = AntigravityProvider(ProviderConfig(), tmp_path)
    assert provider.states(100)[0].tool_running
    assert "DO_NOT_STORE" not in next(tmp_path.glob("*.json")).read_text()
    assert record_hook("PostToolUse", payload, tmp_path, 110) == {}
    assert not provider.states(110)[0].tool_running
    record_hook("Stop", {**payload, "fullyIdle": True}, tmp_path, 120)
    assert provider.states(120)[0].status == "completed"
    record_hook("Stop", {**payload, "fullyIdle": False}, tmp_path, 130)
    assert provider.states(130)[0].tool_running


def test_waiting_tool(tmp_path):
    record_hook("PreToolUse", {"conversationId": "test-session",
                              "toolCall": {"name": "ask_question"}}, tmp_path, 0)
    assert AntigravityProvider(ProviderConfig(), tmp_path).states(0)[0].status == "waiting_for_user"


def test_windows_bundled_agentapi_wrapper_uses_native_argv(tmp_path, monkeypatch):
    native = tmp_path / "install with spaces" / "language_server.exe"
    native.parent.mkdir()
    native.touch()
    native.chmod(0o700)
    wrapper = tmp_path / "agentapi.bat"
    wrapper.write_text(f'@echo off\n"{native}" agentapi %*\n')
    wrapper.chmod(0o700)
    monkeypatch.setattr(antigravity, "_WINDOWS", True)
    provider = AntigravityProvider(ProviderConfig(agentapi_command=[str(wrapper)]), tmp_path)
    captured = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: captured.append((args, kwargs)))
    prompt = 'line one\nquotes " & %PATH% $(command)'
    provider.send_recovery(parse_state(snapshot(), 100, 1000), prompt)
    args, kwargs = captured[0]
    assert args[0] == [str(native), "agentapi", "send-message", "test-session", prompt]
    assert kwargs["shell"] is False
    assert provider.health()["agentapi_available"]


def test_unknown_windows_batch_wrapper_is_not_executed(tmp_path, monkeypatch):
    wrapper = tmp_path / "agentapi.bat"
    wrapper.write_text('@echo off\necho unsafe %*\n')
    wrapper.chmod(0o700)
    monkeypatch.setattr(antigravity, "_WINDOWS", True)
    provider = AntigravityProvider(ProviderConfig(agentapi_command=[str(wrapper)]), tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("Unrecognized batch wrappers must not execute")
    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ProviderError, match="agentapi_wrapper_unsupported"):
        provider.send_recovery(parse_state(snapshot(), 100, 1000), "message")
    assert not provider.health()["ready"]
