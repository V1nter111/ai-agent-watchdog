"""Shell-specific hook commands for Antigravity's hook runner."""

import base64
import os
import re
import shlex
import subprocess

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
    executable_literal = "'" + argv[0].replace("'", "''") + "'"
    arguments_literal = "'" + subprocess.list2cmdline(argv[1:]).replace("'", "''") + "'"
    # Copy the original stdin bytes: PowerShell's text pipeline and Console.In
    # decoding vary with the host console's encoding (including on CI runners).
    script = ("$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue'; "
              "[Console]::InputEncoding = [Text.UTF8Encoding]::new($false); "
              "$start = [Diagnostics.ProcessStartInfo]::new(); "
              "$start.FileName = " + executable_literal + "; "
              "$start.Arguments = " + arguments_literal + "; "
              "$start.UseShellExecute = $false; $start.RedirectStandardInput = $true; "
              "$process = [Diagnostics.Process]::Start($start); "
              "[Console]::OpenStandardInput().CopyTo($process.StandardInput.BaseStream); "
              "$process.StandardInput.BaseStream.Close(); "
              "$process.WaitForExit(); exit $process.ExitCode")
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return "powershell.exe -NoProfile -NonInteractive -OutputFormat Text -EncodedCommand " + encoded
