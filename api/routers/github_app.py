import os

import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from api.github_app_auth import get_installation_token
from api.oauth_state import InvalidStateError, sign_state, verify_state
from api.supabase_client import get_supabase

router = APIRouter(prefix="/api/github", tags=["github_app"])

GITHUB_API = "https://api.github.com"


@router.get("/app/install-state")
def install_state(job_id: str) -> dict:
    """Issues a signed, 15-minute state token for a real job, to embed in the GitHub
    App install link. Generated server-side because the frontend can't hold the
    signing secret -- the raw job_id was never safe to pass straight through as
    `state`, and a real GitHub redirect never even echoes back a param named
    `job_id` in the first place (see the callback below)."""
    supabase = get_supabase()
    if not supabase.table("jobs").select("id").eq("id", job_id).execute().data:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"state": sign_state(job_id)}


def _resolve_repo_full_name(installation_id: int) -> str:
    """Exchanges installation_id for a real installation token and asks GitHub which
    repo(s) it actually covers -- this also validates installation_id is a real,
    live installation, since a bogus id fails the token exchange and raises here.
    """
    token = get_installation_token(installation_id)
    resp = requests.get(
        f"{GITHUB_API}/installation/repositories",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    resp.raise_for_status()
    repos = resp.json().get("repositories", [])
    if not repos:
        raise ValueError("Installation has no accessible repositories")
    return repos[0]["full_name"]


@router.get("/app/callback")
def app_callback(installation_id: int, state: str = Query(...)) -> RedirectResponse:
    """GitHub's App Setup URL after a user installs the App.

    GitHub echoes back whatever was passed as `state` on the install link -- it does
    NOT send a param named `job_id` (an earlier version of this handler expected one
    and silently got `None` on every real install, since Query(default=None) never
    raised). `state` must be a token this server issued via /app/install-state:
    verifying it recovers the job_id and rules out a forged
    `?installation_id=<attacker's>&state=<victim's job_id>` request.
    """
    try:
        job_id = verify_state(state)
    except InvalidStateError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid or expired install link: {exc}") from exc

    try:
        repo_full_name = _resolve_repo_full_name(installation_id)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not verify this GitHub App installation: {exc}",
        ) from exc

    supabase = get_supabase()
    supabase.table("installations").insert(
        {
            "installation_id": installation_id,
            "repo_full_name": repo_full_name,
            "linked_job_id": job_id,
        }
    ).execute()
    web_url = os.environ.get("BUGHOUND_WEB_URL", "https://bughound-web.vercel.app").rstrip("/")
    return RedirectResponse(
        url=f"{web_url}/connect-github?jobId={job_id}&connected=true",
        status_code=303,
    )


@router.post("/webhook")
def webhook() -> dict:
    """Stub for GitHub App lifecycle events (installation removed, etc.) — spec marks this optional.

    SECURITY: this is safe ONLY because it's currently a no-op. The moment this reads
    the payload for anything beyond logging (e.g. deleting an `installations` row on
    an "installation deleted" event), it MUST verify GitHub's X-Hub-Signature-256 HMAC
    against a webhook secret first -- otherwise anyone can POST a forged event and
    corrupt that table. Do not wire real behavior into this function without adding
    that check in the same change.
    """
    return {"status": "ignored"}
