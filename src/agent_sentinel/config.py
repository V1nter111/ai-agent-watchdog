"""Strict configuration; relative paths are resolved against the configuration file."""

import json
import math
from dataclasses import dataclass, field, fields
from pathlib import Path


class ConfigError(ValueError):
    pass


def _positive(value, name, *, zero=False, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or (not zero and value == 0)
            or (integer and not isinstance(value, int))):
        raise ConfigError(f"Invalid {name}")


@dataclass(frozen=True)
class ProviderConfig:
    name: str = "antigravity"
    state_directory: str = "../.sentinel/conversations"
    agentapi_command: list[str] = field(default_factory=lambda: ["agentapi"])
    command_timeout_seconds: float = 30
    max_state_age_seconds: float = 86400


@dataclass(frozen=True)
class Config:
    enabled: bool = True
    interval_seconds: float = 120
    stale_seconds: float = 120
    cooldown_seconds: float = 600
    max_recovery_attempts: int = 2
    confirmation_checks: int = 2
    tool_grace_seconds: float = 3600
    dry_run: bool = True
    runtime_directory: str = "../.sentinel"
    provider: ProviderConfig = field(default_factory=ProviderConfig)


def load_config(path: str | Path) -> Config:
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ConfigError("Cannot read configuration JSON") from exc
    if not isinstance(data, dict):
        raise ConfigError("Configuration must be an object")
    unknown = data.keys() - {f.name for f in fields(Config)}
    if unknown:
        raise ConfigError("Unknown configuration keys")
    provider = data.pop("provider", {})
    if not isinstance(provider, dict) or provider.keys() - {f.name for f in fields(ProviderConfig)}:
        raise ConfigError("Invalid provider configuration")
    cfg = Config(**data, provider=ProviderConfig(**provider))
    if type(cfg.enabled) is not bool or type(cfg.dry_run) is not bool:
        raise ConfigError("enabled and dry_run must be booleans")
    for name in ("interval_seconds", "stale_seconds", "cooldown_seconds", "tool_grace_seconds"):
        _positive(getattr(cfg, name), name, zero=name in {"cooldown_seconds", "tool_grace_seconds"})
    _positive(cfg.max_recovery_attempts, "max_recovery_attempts", zero=True, integer=True)
    _positive(cfg.confirmation_checks, "confirmation_checks", integer=True)
    _positive(cfg.provider.command_timeout_seconds, "command_timeout_seconds")
    _positive(cfg.provider.max_state_age_seconds, "max_state_age_seconds")
    if cfg.provider.max_state_age_seconds <= max(cfg.stale_seconds, cfg.tool_grace_seconds):
        raise ConfigError("max_state_age_seconds must exceed stale_seconds and tool_grace_seconds")
    if cfg.provider.name != "antigravity":
        raise ConfigError("Unsupported provider")
    command = cfg.provider.agentapi_command
    if (not isinstance(command, list) or not command
            or any(not isinstance(x, str) or not x.strip() for x in command)):
        raise ConfigError("agentapi_command must be a nonempty argument array")
    for name, value in (("runtime_directory", cfg.runtime_directory),
                        ("state_directory", cfg.provider.state_directory)):
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"Invalid {name}")
    return cfg


def resolve_path(config_path: str | Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (Path(config_path).resolve().parent / path).resolve()
