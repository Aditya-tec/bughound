"""Guardrails shared by every tier: robots.txt, rate limiting, timeouts, domain allowlist."""

import time
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlparse

USER_AGENT = "BugHoundBot (contact: aditya.kalambe@chat360.io)"

DEFAULT_MAX_ACTIONS = 15
DEFAULT_RUN_TIMEOUT_SECONDS = 300
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 1.0


class RobotsDisallowed(Exception):
    """Raised when robots.txt disallows crawling a path."""


class ActionBudgetExhausted(Exception):
    """Raised when the agent has used its full action budget for the run."""


class RunTimedOut(Exception):
    """Raised when the run exceeds its hard wall-clock timeout."""


class RobotsChecker:
    """Wraps urllib's RobotFileParser for a single target domain."""

    def __init__(self, base_url: str, user_agent: str = USER_AGENT):
        parsed = urlparse(base_url)
        self.robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        self.user_agent = user_agent
        self._parser = urllib.robotparser.RobotFileParser()
        self._parser.set_url(self.robots_url)
        self._loaded = False

    def load(self) -> None:
        try:
            self._parser.read()
            self._loaded = True
        except Exception:
            # If robots.txt is unreachable/malformed, fail open to "no rules found"
            # rather than blocking the entire scan.
            self._loaded = False

    def can_fetch(self, url: str) -> bool:
        if not self._loaded:
            self.load()
        return self._parser.can_fetch(self.user_agent, url)

    def assert_allowed(self, url: str) -> None:
        if not self.can_fetch(url):
            raise RobotsDisallowed(f"robots.txt disallows fetching {url}")


class RateLimiter:
    """Enforces a minimum interval between outbound requests to the target."""

    def __init__(self, min_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS):
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at: float | None = None

    def wait(self) -> None:
        if self._last_request_at is not None:
            elapsed = time.monotonic() - self._last_request_at
            remaining = self.min_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at = time.monotonic()


@dataclass
class ActionBudget:
    """Bounds how many agent-driven actions (clicks, fills, submits) a run may take."""

    max_actions: int = DEFAULT_MAX_ACTIONS
    actions_taken: int = field(default=0, init=False)

    def consume(self, count: int = 1) -> None:
        if self.actions_taken + count > self.max_actions:
            raise ActionBudgetExhausted(
                f"Action budget of {self.max_actions} exhausted"
            )
        self.actions_taken += count

    @property
    def remaining(self) -> int:
        return max(0, self.max_actions - self.actions_taken)


class DomainAllowlist:
    """Only allows crawling pages on the target's own registrable domain (host match)."""

    def __init__(self, target_url: str):
        self.allowed_netloc = urlparse(target_url).netloc

    def is_internal(self, url: str) -> bool:
        return urlparse(url).netloc == self.allowed_netloc


class RunClock:
    """Tracks elapsed wall-clock time against a hard run timeout."""

    def __init__(self, timeout_seconds: int = DEFAULT_RUN_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds
        self.started_at = time.monotonic()

    def assert_not_expired(self) -> None:
        if time.monotonic() - self.started_at > self.timeout_seconds:
            raise RunTimedOut(f"Run exceeded {self.timeout_seconds}s hard timeout")

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at
