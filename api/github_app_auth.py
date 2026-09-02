"""GitHub App JWT signing + installation token exchange (spec section 10)."""

import base64
import os
import time

import jwt
import requests

GITHUB_API = "https://api.github.com"


def _signing_key() -> str:
    encoded = os.environ["GITHUB_APP_PRIVATE_KEY"]
    return base64.b64decode(encoded).decode("utf-8")


def _app_jwt() -> str:
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),  # GitHub caps this at 10 minutes
        "iss": os.environ["GITHUB_APP_ID"],
    }
    return jwt.encode(payload, _signing_key(), algorithm="RS256")


def get_installation_token(installation_id: int) -> str:
    """Exchanges a short-lived App JWT for an installation access token (~1hr, scoped to
    the granted repo and issues:write only)."""
    resp = requests.post(
        f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {_app_jwt()}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]
