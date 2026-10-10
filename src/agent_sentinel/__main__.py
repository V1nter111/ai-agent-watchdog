"""Command line entry point."""

import argparse
import json
import signal
import sys
import time
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config, resolve_path
from .hooks import EVENTS, record_hook
from .logger import atomic_json
from .providers.antigravity import AntigravityProvider
from .providers.base import ProviderError
from .runtime import is_running
from .watchdog import Watchdog


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Agent Sentinel watchdog")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", default="config/sentinel.json")
    parser.add_argument("command", choices=["run", "check", "status", "validate", "stop", "hook", "integration"])
    parser.add_argument("--event", choices=EVENTS)
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        runtime = resolve_path(args.config, cfg.runtime_directory)
        source = resolve_path(args.config, cfg.provider.state_directory)
        provider = AntigravityProvider(cfg.provider, source)
        if args.command == "validate":
            print(json.dumps({"valid": True, "version": __version__}))
        elif args.command == "integration":
            config_path = str(Path(args.config).resolve())
            # Quotes here are for Antigravity's documented shell-based hook runner.
            if any(c in sys.executable + config_path for c in ('"', '$', '`', '\n', '\r')):
                raise ValueError("Unsupported shell characters in installation path")
            command = f'"{sys.executable}" -m agent_sentinel --config "{config_path}" hook --event '
            hooks = {}
            for event in EVENTS:
                if event == "PreToolUse":
                    continue  # Passive defaults must not change tool permission decisions.
                handler = {"type": "command", "command": command + event, "timeout": 10}
                hooks[event] = ([{"matcher": ".*", "hooks": [handler]}]
                                if event == "PostToolUse" else [handler])
            atomic_json(runtime / "hooks.json", {"agent-sentinel": hooks})
            atomic_json(runtime / "sidecar.json", {
                "command": sys.executable,
                "args": ["-m", "agent_sentinel", "--config", config_path, "run"],
                "restart_policy": "on-failure", "display_name": "Agent Sentinel",
                "description": "Watch for lack of agent progress"})
            print(json.dumps({"generated": ["hooks.json", "sidecar.json"],
                              "hint": "See docs/ANTIGRAVITY.md to enable the integration"}))
        elif args.command == "status":
            status = {}
            path = runtime / "status.json"
            if path.exists():
                status = json.loads(path.read_text(encoding="utf-8"))
            if "provider" in status:
                status["watchdog_provider"] = status["provider"]
            provider_status = provider.health()
            try:
                if source.is_dir():
                    snapshot_count = len(provider.states(time.time()))
                    provider_status = {**provider.health(), "snapshot_count": snapshot_count}
            except ProviderError:
                provider_status["ready"] = False
            status.update({"running": is_running(runtime), "provider": provider_status,
                           "configuration": {"enabled": cfg.enabled, "dry_run": cfg.dry_run,
                           "interval_seconds": cfg.interval_seconds, "stale_seconds": cfg.stale_seconds,
                           "cooldown_seconds": cfg.cooldown_seconds,
                           "max_recovery_attempts": cfg.max_recovery_attempts,
                           "tool_grace_seconds": cfg.tool_grace_seconds,
                           "confirmation_checks": cfg.confirmation_checks}})
            print(json.dumps(status, indent=2))
        elif args.command == "stop":
            if is_running(runtime):
                (runtime / "stop.request").touch()
            print(json.dumps({"stop_requested": True}))
        elif args.command == "hook":
            if not args.event:
                raise ValueError("hook requires --event")
            payload = json.loads(sys.stdin.read(1_048_576))
            print(json.dumps(record_hook(args.event, payload, source)))
        else:
            watchdog = Watchdog(cfg, provider, runtime)
            for signum in (signal.SIGINT, signal.SIGTERM):
                signal.signal(signum, lambda *_: watchdog.stop_event.set())
            watchdog.run(once=args.command == "check")
        return 0
    except (ConfigError, ValueError, OSError, RuntimeError) as exc:
        # Exception text may contain paths/IDs from third-party APIs: emit type only.
        print(json.dumps({"error": type(exc).__name__,
                          "hint": "See docs/TROUBLESHOOTING.md; validate config and runtime"}),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
