"""Restricts mode="owner" to domains the operator actually controls.

Without this, any visitor could submit mode=owner against a target they don't
own and trigger the operator's GitHub PAT to file issues wherever the agent
lands. Configure via OWNER_MODE_ALLOWED_DOMAINS (comma-separated hostnames,
e.g. "adityakalambe.xyz,bughound-web.vercel.app"). An empty/unset allowlist
rejects every owner-mode request -- this fails closed, not open.
"""

import os
from urllib.parse import urlparse

from fastapi import HTTPException


def _allowed_domains() -> set[str]:
    raw = os.environ.get("OWNER_MODE_ALLOWED_DOMAINS", "")
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


def assert_owner_mode_allowed(target_url: str) -> None:
    host = (urlparse(target_url).hostname or "").lower()
    allowed = _allowed_domains()
    if host and any(host == d or host.endswith(f".{d}") for d in allowed):
        return
    raise HTTPException(
        status_code=403,
        detail=(
            "Owner mode is restricted to the operator's own registered domains. "
            "Use Scan mode for any other target."
        ),
    )
