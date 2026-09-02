from fastapi import APIRouter, Query

from supabase_client import get_supabase

router = APIRouter(prefix="/api/github", tags=["github_app"])


@router.get("/app/callback")
def app_callback(installation_id: int, job_id: str | None = Query(default=None)) -> dict:
    """GitHub redirects here after a user installs the App (Mode B+, spec section 10)."""
    supabase = get_supabase()
    supabase.table("installations").insert(
        {
            "installation_id": installation_id,
            "repo_full_name": "",  # filled in by the webhook, or a follow-up API call, once known
            "linked_job_id": job_id,
        }
    ).execute()
    return {"status": "connected", "installation_id": installation_id}


@router.post("/webhook")
def webhook() -> dict:
    """Stub for GitHub App lifecycle events (installation removed, etc.) — spec marks this optional."""
    return {"status": "ignored"}
