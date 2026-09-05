import requests
from fastapi import APIRouter, HTTPException, Query

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
def app_callback(installation_id: int, state: str = Query(...)) -> dict:
    """GitHub redirects here after a user installs the App (Mode B+, spec section 10).

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
    return {"status": "connected", "installation_id": installation_id, "repo_full_name": repo_full_name}


@router.post("/webhook")
def webhook() -> dict:
    """Stub for GitHub App lifecycle events (installation removed, etc.) — spec marks this optional."""
    return {"status": "ignored"}
