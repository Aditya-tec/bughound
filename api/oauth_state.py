"""Signed, time-bound state tokens for the GitHub App install flow.

Two problems, found on the same read of github_app.py:

1. A real functional bug: the install link sets `?state=${jobId}`, which GitHub
   echoes back on the callback redirect as a `state` query param -- but the callback
   handler's signature expected a param literally named `job_id`, which GitHub never
   sends. Every real installation would have landed with `linked_job_id = null`.
2. A real security gap: even once read correctly, a raw job_id in `state` is a
   classic OAuth/App-install CSRF target. Nothing stopped a direct
   `GET /app/callback?installation_id=<attacker's own>&state=<victim's job_id>`
   from linking the attacker's installation to someone else's job.

Fixed by generating this token server-side (the frontend can't hold the signing
secret) and verifying it on the way back, single-purpose and time-bound rather than
trusting the raw job_id.
"""

import hashlib
import hmac
import os
import time

STATE_MAX_AGE_SECONDS = 900  # 15 minutes -- long enough to complete a real install, short enough to bound replay


class InvalidStateError(ValueError):
    """Raised when a state token is malformed, forged, or expired."""


def _secret() -> bytes:
    secret = os.environ.get("GITHUB_APP_STATE_SECRET", "")
    if not secret:
        raise InvalidStateError("GITHUB_APP_STATE_SECRET is not configured")
    return secret.encode()


def sign_state(job_id: str) -> str:
    timestamp = str(int(time.time()))
    payload = f"{job_id}.{timestamp}"
    signature = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_state(state: str) -> str:
    """Returns the job_id if `state` is a genuine, unexpired token this server issued."""
    parts = state.split(".")
    if len(parts) != 3:
        raise InvalidStateError("Malformed state token")
    job_id, timestamp, signature = parts

    payload = f"{job_id}.{timestamp}"
    expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise InvalidStateError("State token signature does not match")

    try:
        age = time.time() - int(timestamp)
    except ValueError:
        raise InvalidStateError("Malformed state token timestamp") from None
    if age > STATE_MAX_AGE_SECONDS or age < -30:  # small negative allowance for clock skew
        raise InvalidStateError("State token expired")

    return job_id
