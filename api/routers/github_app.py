import requests
from fastapi import APIRouter, HTTPException, Query

from api.github_app_auth import get_installation_token
from api.supabase_client import get_supabase

router = APIRouter(prefix="/api/github", tags=["github_app"])

GITHUB_API = "https://api.github.com"


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
def app_callback(installation_id: int, job_id: str | None = Query(default=None)) -> dict:
    """GitHub redirects here after a user installs the App (Mode B+, spec section 10)."""
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
