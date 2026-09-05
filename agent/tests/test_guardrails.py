"""Unit tests for agent/guardrails.py -- action budget, domain allowlist, and the
run-timeout clock. Rate limiting and robots.txt parsing touch real time/network and
are exercised live in CI runs instead; these are the parts that are pure and fast
to test in isolation.
"""

from unittest.mock import patch

import pytest

from guardrails import ActionBudget, ActionBudgetExhausted, DomainAllowlist, RunClock, RunTimedOut


def test_action_budget_allows_up_to_the_limit():
    budget = ActionBudget(max_actions=3)
    budget.consume()
    budget.consume()
    budget.consume()
    assert budget.remaining == 0


def test_action_budget_raises_once_exhausted():
    budget = ActionBudget(max_actions=2)
    budget.consume(2)
    with pytest.raises(ActionBudgetExhausted):
        budget.consume()


def test_action_budget_rejects_a_batch_that_would_overshoot():
    budget = ActionBudget(max_actions=5)
    budget.consume(3)
    with pytest.raises(ActionBudgetExhausted):
        budget.consume(3)  # would total 6, over the cap of 5
    assert budget.remaining == 2  # the rejected batch must not partially consume


def test_domain_allowlist_matches_same_host():
    allowlist = DomainAllowlist("https://example.com/page")
    assert allowlist.is_internal("https://example.com/other-page")


def test_domain_allowlist_rejects_different_host():
    allowlist = DomainAllowlist("https://example.com/")
    assert not allowlist.is_internal("https://evil.example/")


def test_domain_allowlist_rejects_subdomain_as_external():
    # A subdomain is a different netloc -- external links only ever get a HEAD check,
    # never followed, so this must not be treated as internal.
    allowlist = DomainAllowlist("https://example.com/")
    assert not allowlist.is_internal("https://mail.example.com/")


def test_run_clock_has_not_expired_immediately():
    clock = RunClock(timeout_seconds=60)
    clock.assert_not_expired()  # should not raise


def test_run_clock_raises_after_timeout():
    # Mocks the clock instead of sleeping a real, timing-sensitive margin -- a tight
    # real sleep here was flaky under load (passed standalone, failed in the full suite).
    with patch("guardrails.time.monotonic", side_effect=[100.0, 105.0]):
        clock = RunClock(timeout_seconds=1)  # started_at = 100.0
        with pytest.raises(RunTimedOut):
            clock.assert_not_expired()  # now = 105.0, elapsed 5s > 1s timeout
