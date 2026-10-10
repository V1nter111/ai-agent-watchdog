import json
import os
import subprocess
import sys

import pytest

from agent_sentinel import integration


def test_windows_simple_paths_avoid_runner_quote_escaping(monkeypatch):
    monkeypatch.setattr(integration, "_WINDOWS", True)
    command = integration.hook_command("C:\\tools\\python.exe", "C:\\tools\\config.json", "Stop")
    assert command == ("C:/tools/python.exe -m agent_sentinel --config C:/tools/config.json "
                       "hook --event Stop")


@pytest.mark.parametrize("event", ["PreInvocation", "PostToolUse", "Stop"])
def test_hook_command_executes_with_spaces_and_shell_characters(tmp_path, event):
    directory = tmp_path / "space & quote's $config"
    directory.mkdir()
    config = directory / "config.json"
    config.write_text(json.dumps({"provider": {"state_directory": "states"}}))
    command = integration.hook_command(sys.executable, str(config), event)
    argv = ["cmd.exe", "/d", "/c", command] if os.name == "nt" else ["sh", "-c", command]
    env = {**os.environ, "PYTHONPATH": os.path.abspath("src")}
    result = subprocess.run(argv, check=False, input=json.dumps({"conversationId": "synthetic-hook-test",
                            "fullyIdle": True}), text=True, capture_output=True, env=env, timeout=15)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ({"decision": "stop"} if event == "Stop" else {})
    snapshot = json.loads(next((directory / "states").glob("*.json")).read_text())
    assert snapshot["status"] == ("completed" if event == "Stop" else "running")


@pytest.mark.parametrize("control", ["\0", "\n", "\r"])
def test_hook_path_control_characters_rejected(control):
    with pytest.raises(ValueError):
        integration.hook_command("python" + control, "config.json", "Stop")
