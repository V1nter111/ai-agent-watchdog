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
    # Code page 65001 makes .NET Framework's default native stdin writer emit a
    # UTF-8 BOM unless the launcher explicitly selects an encoding without it.
    argv = (["cmd.exe", "/d", "/c", "chcp 65001 >nul & " + command]
            if os.name == "nt" else ["sh", "-c", command])
    env = {**os.environ, "PYTHONPATH": os.path.abspath("src")}
    payload = json.dumps({"conversationId": "synthetic-hook-test", "fullyIdle": True,
                          "ignored": "Unicode: \u043f\u0440\u0438\u0432\u0435\u0442"}, ensure_ascii=False)
    result = subprocess.run(argv, check=False, input=payload, text=True, encoding="utf-8", capture_output=True,
                            env={**env, "PYTHONIOENCODING": "utf-8"}, timeout=15)
    if result.returncode:
        probe = tmp_path / "probe" / "agent_sentinel"
        probe.mkdir(parents=True)
        (probe / "__init__.py").touch()
        (probe / "__main__.py").write_text(
            "import json, sys\nprint(json.dumps({'stdin_hex': sys.stdin.buffer.read().hex()}))")
        diagnostic = subprocess.run(argv, check=False, input=payload, text=True, encoding="utf-8",
                                    capture_output=True, env={**env, "PYTHONPATH": str(probe.parent)},
                                    timeout=15)
        pytest.fail(result.stderr + "\nSynthetic stdin probe: " + diagnostic.stdout + diagnostic.stderr)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ({"decision": "stop"} if event == "Stop" else {})
    snapshot = json.loads(next((directory / "states").glob("*.json")).read_text())
    assert snapshot["status"] == ("completed" if event == "Stop" else "running")


@pytest.mark.parametrize("control", ["\0", "\n", "\r"])
def test_hook_path_control_characters_rejected(control):
    with pytest.raises(ValueError):
        integration.hook_command("python" + control, "config.json", "Stop")
