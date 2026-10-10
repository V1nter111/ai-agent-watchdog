from dataclasses import replace

import pytest

from agent_sentinel.config import Config
from agent_sentinel.detector import Detector
from agent_sentinel.providers.base import ConversationState


def state(**changes):
    return replace(ConversationState("test-session", "running", 0, "step-1"), **changes)


def test_stale_requires_observation_window_and_confirmation():
    detector = Detector(Config())
    assert not detector.suspicious(state(), 1000)
    assert not detector.suspicious(state(), 1119)
    assert not detector.suspicious(state(), 1120)
    assert detector.suspicious(state(), 1240)


@pytest.mark.parametrize("status", ["idle", "completed", "waiting_for_user"])
def test_inactive_or_human_wait_never_recovers(status):
    detector = Detector(Config())
    assert not detector.suspicious(state(status=status), 0)
    assert not detector.suspicious(state(status=status), 5000)
    assert not detector.suspicious(state(status=status), 6000)


def test_live_process_and_long_tool_grace():
    detector = Detector(Config())
    tool = state(tool_running=True)
    assert not detector.suspicious(tool, 0)
    assert not detector.suspicious(tool, 3599)
    assert not detector.suspicious(tool, 3600)
    assert detector.suspicious(tool, 3720)
    assert not detector.suspicious(replace(tool, process_alive=True), 4000)


def test_progress_resets_confirmation_and_future_timestamp_safe():
    detector = Detector(Config())
    assert not detector.suspicious(state(), 0)
    assert not detector.suspicious(state(), 120)
    newer = state(progress_token="step-2", last_progress_at=240)
    assert not detector.suspicious(newer, 240)
    assert not detector.suspicious(newer, 360)
    assert detector.suspicious(newer, 480)
    assert not detector.suspicious(state(last_progress_at=9999), 600)


def test_missing_state_forces_new_observation():
    detector = Detector(Config(confirmation_checks=1))
    detector.suspicious(state(), 0)
    assert detector.suspicious(state(), 120)
    detector.retain(set())
    assert not detector.suspicious(state(), 1000)
