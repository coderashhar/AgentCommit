"""Tests for _run_agent's rate-limit retry budget.

Gemini's suggested retry delay scales with how exhausted the quota is. A brief burst
asks for a second or two; a spent free-tier request quota asks for nearly a minute:

    Quota exceeded for metric: ...generate_content_free_tier_requests, limit: 20
    Please retry in 57.681189045s.

Sleeping through that five times held one agent call for ~5 minutes, and the
dashboard runs three in sequence — ~15 minutes before anything reached the browser,
for a result the deterministic fallback produces in about a second.
"""

import time

import pytest

from app.agents import coordinator
from app.agents.coordinator import _extract_retry_delay


class _RateLimited(Exception):
    def __init__(self, delay_seconds):
        super().__init__(
            "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
            "generativelanguage.googleapis.com/generate_content_free_tier_requests, "
            f"limit: 20, model: gemini-2.5-flash\nPlease retry in {delay_seconds}s."
        )


@pytest.fixture
def no_sleep(monkeypatch):
    """Record sleeps instead of performing them, and advance a fake clock."""
    slept: list[float] = []
    clock = {"t": 0.0}

    async def fake_sleep(seconds):
        slept.append(seconds)
        clock["t"] += seconds

    monkeypatch.setattr(coordinator.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(coordinator.time, "monotonic", lambda: clock["t"])
    return slept


@pytest.fixture
def always_rate_limited(monkeypatch):
    """Make every agent run raise a 429 with the given suggested delay."""

    def _install(delay_seconds):
        calls = {"n": 0}

        class _Runner:
            def __init__(self, **kwargs):
                pass

            def run_async(self, **kwargs):
                calls["n"] += 1
                raise _RateLimited(delay_seconds)

        monkeypatch.setattr(coordinator, "Runner", _Runner)
        return calls

    return _install


class TestExtractRetryDelay:
    def test_reads_the_real_quota_message(self):
        msg = "Please retry in 57.681189045s."
        assert _extract_retry_delay(msg) == pytest.approx(57.681189045)

    def test_falls_back_to_20s_when_absent(self):
        assert _extract_retry_delay("429 RESOURCE_EXHAUSTED") == 20.0


class TestRetryBudget:
    async def test_long_delay_gives_up_immediately(self, no_sleep, always_rate_limited):
        """A 57.7s suggested wait exceeds the budget on its own — never sleep it."""
        always_rate_limited(57.681189045)

        with pytest.raises(Exception):
            await coordinator._run_agent(object(), "hi", "s1")

        assert no_sleep == [], "must not sleep when the first delay blows the budget"

    async def test_short_delays_still_retry(self, no_sleep, always_rate_limited):
        """A transient limit asking for ~2s should still be waited out."""
        always_rate_limited(2.0)

        with pytest.raises(Exception):
            await coordinator._run_agent(object(), "hi", "s1")

        assert len(no_sleep) >= 2
        assert all(s == pytest.approx(4.0) for s in no_sleep)

    async def test_total_wait_stays_inside_the_budget(self, no_sleep, always_rate_limited):
        always_rate_limited(5.0)

        with pytest.raises(Exception):
            await coordinator._run_agent(object(), "hi", "s1")

        assert sum(no_sleep) <= coordinator.AGENT_RETRY_BUDGET_SECONDS

    async def test_budget_is_configurable(self, no_sleep, always_rate_limited):
        always_rate_limited(5.0)

        with pytest.raises(Exception):
            await coordinator._run_agent(object(), "hi", "s1", retry_budget_seconds=0.0)

        assert no_sleep == []

    async def test_never_exceeds_max_retries(self, no_sleep, always_rate_limited):
        calls = always_rate_limited(0.1)

        with pytest.raises(Exception):
            await coordinator._run_agent(object(), "hi", "s1")

        assert calls["n"] <= 6  # range(max_retries + 1)

    async def test_non_rate_limit_error_is_not_retried(self, monkeypatch, no_sleep):
        calls = {"n": 0}

        class _Runner:
            def __init__(self, **kwargs):
                pass

            def run_async(self, **kwargs):
                calls["n"] += 1
                raise RuntimeError("bad request")

        monkeypatch.setattr(coordinator, "Runner", _Runner)

        with pytest.raises(RuntimeError):
            await coordinator._run_agent(object(), "hi", "s1")

        assert calls["n"] == 1
        assert no_sleep == []
