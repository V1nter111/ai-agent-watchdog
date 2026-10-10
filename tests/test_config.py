import json

import pytest

from agent_sentinel.config import ConfigError, load_config, resolve_path


def write(tmp_path, data):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8-sig")
    return path


def test_defaults_and_relative_paths(tmp_path):
    path = write(tmp_path, {})
    cfg = load_config(path)
    assert cfg.interval_seconds == 120
    assert cfg.dry_run is True
    assert resolve_path(path, "runtime") == tmp_path / "runtime"


@pytest.mark.parametrize("data", [[], {"unknown": 1}, {"interval_seconds": 0},
    {"stale_seconds": -1}, {"enabled": "true"}, {"dry_run": 0},
    {"max_recovery_attempts": 1.5}, {"confirmation_checks": True},
    {"cooldown_seconds": float("nan")}, {"provider": []},
    {"provider": {"name": "codex"}}, {"provider": {"agentapi_command": "agentapi"}},
    {"provider": {"agentapi_command": []}}, {"provider": {"max_state_age_seconds": 120}},
    {"runtime_directory": ""}, {"tool_grace_seconds": None}])
def test_invalid_configuration(tmp_path, data):
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, data))


def test_unreadable_and_malformed(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.json")
    path = tmp_path / "bad.json"
    path.write_text("{")
    with pytest.raises(ConfigError):
        load_config(path)


def test_example_is_valid():
    assert load_config("config/sentinel.example.json").provider.name == "antigravity"
