"""Shell-specific hook commands for Antigravity's hook runner."""

import base64
import os
import re
import shlex

_WINDOWS = os.name == "nt"


def hook_command(executable: str, config_path: str, event: str) -> str:
    if any(c in executable + config_path for c in ("\0", "\n", "\r")):
        raise ValueError("Unsupported control characters in installation path")
    argv = [executable, "-m", "agent_sentinel", "--config", config_path, "hook", "--event", event]
    if not _WINDOWS:
        return shlex.join(argv)
    argv = [arg.replace("\\", "/") for arg in argv]
    # Antigravity's Windows runner escapes literal double quotes. Avoid unnecessary
    # quotes for simple paths; encode PowerShell when paths need shell protection.
    if all(re.fullmatch(r"[A-Za-z0-9_./:-]+", arg) for arg in argv):
        return " ".join(argv)
    quoted = ["'" + arg.replace("'", "''") + "'" for arg in argv]
    script = ("$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
              "$payload = [Console]::In.ReadToEnd(); "
              "$payload | & " + " ".join(quoted) + "; exit $LASTEXITCODE")
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + encoded
