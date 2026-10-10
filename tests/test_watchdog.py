import json
from dataclasses import replace

from agent_sentinel.config import Config
from agent_sentinel.providers.base import ConversationState, ProviderError
from agent_sentinel.runtime import FileLock, is_running
from agent_sentinel.watchdog import Watchdog


class FakeProvider:
    def __init__(self):
        self.state = ConversationState("test-session", "running", 0, "step-1")
        self.sent = []
        self.fail = False

    def health(self):
        return {"ready": True}

    def states(self, now):
        return [self.state]

    def send_recovery(self, state, message):
        self.sent.append(message)
        if self.fail:
            raise ProviderError("failure")


def test_watchdog_cooldown_limit_and_persistence(tmp_path):
    config = Config(dry_run=False, confirmation_checks=1)
    provider = FakeProvider()
    watchdog = Watchdog(config, provider, tmp_path)
    assert watchdog.check(0)["recoveries"] == 0
    assert watchdog.check(120)["recoveries"] == 1
    assert watchdog.check(240)["recoveries"] == 0
    assert watchdog.check(720)["recoveries"] == 1
    watchdog = Watchdog(config, provider, tmp_path)
    watchdog.check(1000)
    assert watchdog.check(2000)["recoveries"] == 0
    assert len(provider.sent) == 2


def test_failed_send_consumes_attempt(tmp_path):
    provider = FakeProvider()
    provider.fail = True
    watchdog = Watchdog(Config(dry_run=False, confirmation_checks=1, max_recovery_attempts=1),
                        provider, tmp_path)
    watchdog.check(0)
    assert watchdog.check(120)["errors"] == 1
    assert watchdog.check(1000)["errors"] == 0
    assert len(provider.sent) == 1


def test_dry_run_and_disabled(tmp_path):
    provider = FakeProvider()
    watchdog = Watchdog(Config(confirmation_checks=1), provider, tmp_path)
    watchdog.check(0)
    assert watchdog.check(120)["suspicious"] == 1
    assert not provider.sent
    assert not (tmp_path / "recovery.json").exists()
    watchdog = Watchdog(Config(enabled=False, dry_run=False), provider, tmp_path)
    assert watchdog.check(1000)["checked"] == 0


def test_state_changed_before_send(tmp_path):
    provider = FakeProvider()
    watchdog = Watchdog(Config(dry_run=False, confirmation_checks=1), provider, tmp_path)
    watchdog.check(0)
    calls = 0
    def states(now):
        nonlocal calls
        calls += 1
        return [provider.state if calls == 1 else replace(provider.state, status="completed")]
    provider.states = states
    assert watchdog.check(120)["recoveries"] == 0
    assert not provider.sent


def test_provider_failure_does_not_recover(tmp_path):
    provider = FakeProvider()
    def fail(now):
        raise ProviderError("failure")
    provider.states = fail
    watchdog = Watchdog(Config(dry_run=False), provider, tmp_path)
    assert watchdog.check(1000)["errors"] == 1
    assert not provider.sent


def test_single_instance_and_run_once(tmp_path):
    with FileLock(tmp_path / "watchdog.lock"):
        assert is_running(tmp_path)
    assert not is_running(tmp_path)
    watchdog = Watchdog(Config(), FakeProvider(), tmp_path)
    watchdog.run(once=True)
    assert not is_running(tmp_path)


def test_logs_do_not_contain_raw_identity(tmp_path):
    provider = FakeProvider()
    watchdog = Watchdog(Config(confirmation_checks=1), provider, tmp_path)
    watchdog.check(0)
    watchdog.check(120)
    assert "test-session" not in (tmp_path / "sentinel.log").read_text()


def test_detection_precedes_automatic_recovery_with_sanitized_evidence(tmp_path):
    provider = FakeProvider()
    watchdog = Watchdog(Config(dry_run=False, confirmation_checks=2), provider, tmp_path)
    assert watchdog.check(0)["suspicious"] == 0
    assert watchdog.check(120)["recoveries"] == 0
    assert watchdog.check(240)["recoveries"] == 1
    events = [json.loads(line) for line in (tmp_path / "sentinel.log").read_text().splitlines()]
    detected = next(i for i, event in enumerate(events) if event["event"] == "stall_detected")
    sent = next(i for i, event in enumerate(events) if event["event"] == "recovery_sent")
    assert detected < sent
    assert events[detected]["check_time"] == 240
    assert events[detected]["stale_for_seconds"] == 240
    assert "test-session" not in json.dumps(events)
