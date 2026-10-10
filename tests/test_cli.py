import json

from agent_sentinel.__main__ import main


def config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"runtime_directory": "runtime",
                               "provider": {"state_directory": "states"}}))
    return str(path)


def test_generate_passive_integration(tmp_path, capsys):
    assert main(["--config", config(tmp_path), "integration"]) == 0
    capsys.readouterr()
    hooks = json.loads((tmp_path / "runtime" / "hooks.json").read_text())["agent-sentinel"]
    assert "PreToolUse" not in hooks
    assert set(hooks) == {"PostToolUse", "PreInvocation", "PostInvocation", "Stop"}
    sidecar = json.loads((tmp_path / "runtime" / "sidecar.json").read_text())
    assert sidecar["args"][-1] == "run"


def test_status_validates_snapshots_and_omits_private_paths(tmp_path, capsys):
    path = config(tmp_path)
    (tmp_path / "states").mkdir()
    (tmp_path / "states" / "bad.json").write_text("{")
    assert main(["--config", path, "status"]) == 0
    output = capsys.readouterr().out
    status = json.loads(output)
    assert status["running"] is False
    assert status["provider"]["invalid_states"] == 1
    assert status["provider"]["snapshot_count"] == 0
    assert str(tmp_path) not in output
