"""Unit tests for api/oauth_state.py -- the signed state token that replaces trusting
a raw job_id on the GitHub App install callback."""

import os
import time
from unittest.mock import patch

import pytest

from api.oauth_state import InvalidStateError, sign_state, verify_state

ENV = {"GITHUB_APP_STATE_SECRET": "test-secret-do-not-use-in-prod"}


def test_round_trip_returns_the_original_job_id():
    with patch.dict(os.environ, ENV):
        state = sign_state("job-123")
        assert verify_state(state) == "job-123"


def test_rejects_tampered_job_id():
    with patch.dict(os.environ, ENV):
        state = sign_state("job-123")
        # Swap the job_id but keep the original signature -- the classic forgery attempt.
        job_id, timestamp, signature = state.split(".")
        forged = f"attacker-job.{timestamp}.{signature}"
        with pytest.raises(InvalidStateError):
            verify_state(forged)


def test_rejects_tampered_signature():
    with patch.dict(os.environ, ENV):
        state = sign_state("job-123")
        job_id, timestamp, signature = state.split(".")
        forged = f"{job_id}.{timestamp}.{'0' * len(signature)}"
        with pytest.raises(InvalidStateError):
            verify_state(forged)


def test_rejects_malformed_state():
    with patch.dict(os.environ, ENV):
        with pytest.raises(InvalidStateError):
            verify_state("not-a-real-state-token")


def test_rejects_expired_state():
    with patch.dict(os.environ, ENV):
        old_timestamp = str(int(time.time()) - 3600)  # 1 hour ago, well past the 15-minute cap
        payload = f"job-123.{old_timestamp}"
        import hashlib
        import hmac

        sig = hmac.new(ENV["GITHUB_APP_STATE_SECRET"].encode(), payload.encode(), hashlib.sha256).hexdigest()
        with pytest.raises(InvalidStateError):
            verify_state(f"{payload}.{sig}")


def test_signed_with_one_secret_cannot_verify_with_another():
    with patch.dict(os.environ, ENV):
        state = sign_state("job-123")
    with patch.dict(os.environ, {"GITHUB_APP_STATE_SECRET": "a-different-secret"}):
        with pytest.raises(InvalidStateError):
            verify_state(state)


def test_missing_secret_fails_closed():
    with patch.dict(os.environ, {"GITHUB_APP_STATE_SECRET": ""}):
        with pytest.raises(InvalidStateError):
            sign_state("job-123")
