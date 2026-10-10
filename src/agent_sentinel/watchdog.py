"""Periodic checking, confirmation, cooldown and bounded recovery."""

import os
import threading
import time
from pathlib import Path

from .config import Config
from .detector import Detector
from .logger import atomic_json, make_logger
from .providers.base import Provider, ProviderError
from .recovery import Recovery, identity, recovery_message
from .runtime import FileLock


class Watchdog:
    def __init__(self, config: Config, provider: Provider, runtime: Path):
        self.config = config
        self.provider = provider
        self.runtime = runtime
        self.detector = Detector(config)
        self.recovery = Recovery(config, runtime / "recovery.json")
        self.logger = make_logger(runtime)
        self.stop_event = threading.Event()
        self.last_check = None

    def _status(self, running: bool, provider_status: dict, **extra):
        atomic_json(self.runtime / "status.json", {
            "running": running, "pid": os.getpid(), "last_check": self.last_check,
            "provider": provider_status, "enabled": self.config.enabled,
            "dry_run": self.config.dry_run, **extra})

    def check(self, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        self.last_check = now
        result = {"checked": 0, "suspicious": 0, "recoveries": 0, "errors": 0}
        health = self.provider.health()
        if not self.config.enabled:
            self._status(True, health, **result)
            self.logger.info("watchdog_disabled")
            return result
        try:
            states = self.provider.states(now)
        except ProviderError:
            result["errors"] += 1
            self.detector.retain(set())
            self._status(True, {**health, "ready": False}, **result)
            self.logger.error("provider_check_failed")
            return result
        self.detector.retain({state.conversation_id for state in states})
        result["checked"] = len(states)
        for state in states:
            if self.stop_event.is_set() or (self.runtime / "stop.request").exists():
                break
            if not self.detector.suspicious(state, now):
                continue
            result["suspicious"] += 1
            data = {"conversation_hash": identity(state)[:16]}
            if self.config.dry_run:
                self.logger.info("would_recover", extra={"data": data})
                continue
            if not health.get("ready"):
                continue
            try:
                # Recheck immediately before reserving/sending: a completed command must be left alone.
                current = next((s for s in self.provider.states(now)
                                if s.conversation_id == state.conversation_id), None)
                if current != state:
                    self.logger.info("recovery_skipped_state_changed", extra={"data": data})
                    continue
                if not self.recovery.reserve(state, now):
                    self.logger.info("recovery_suppressed", extra={"data": data})
                    continue
                self.provider.send_recovery(state, recovery_message())
                result["recoveries"] += 1
                self.logger.info("recovery_sent", extra={"data": data})
            except ProviderError:
                # Failed/ambiguous sends consume the reservation; no automatic immediate retry.
                result["errors"] += 1
                self.logger.error("recovery_failed", extra={"data": data})
        health = self.provider.health()
        self._status(True, health, **result)
        self.logger.info("check_complete", extra={"data": result})
        return result

    def run(self, once: bool = False) -> None:
        with FileLock(self.runtime / "watchdog.lock"):
            (self.runtime / "stop.request").unlink(missing_ok=True)
            self.logger.info("watchdog_started")
            try:
                while not self.stop_event.is_set():
                    self.check()
                    if once:
                        break
                    deadline = time.monotonic() + self.config.interval_seconds
                    while time.monotonic() < deadline and not self.stop_event.is_set():
                        if (self.runtime / "stop.request").exists():
                            self.stop_event.set()
                            break
                        self.stop_event.wait(min(1, max(0, deadline - time.monotonic())))
            finally:
                self._status(False, self.provider.health())
                (self.runtime / "stop.request").unlink(missing_ok=True)
                self.logger.info("watchdog_stopped")
