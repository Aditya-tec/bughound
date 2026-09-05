import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.github_app_auth import get_installation_token
from api.github_issue_filer import file_issue
from api.rate_limit import enforce_scan_rate_limit, get_client_ip
from api.supabase_client import get_supabase

router = APIRouter(prefix="/api/jobs", tags=["issues"])


class FileIssuesRequest(BaseModel):
    finding_ids: list[str]


@router.post("/{job_id}/file-issues")
def file_issues(job_id: str, body: FileIssuesRequest, request: Request) -> dict:
    # Report pages are public/shareable links with no auth -- anyone who has one could
    # otherwise call this repeatedly. Reuse the same per-IP cap as job creation, and
    # (below) never re-file a finding that's already filed, so repeat calls can't spam
    # duplicate issues even from different IPs.
    supabase = get_supabase()
    enforce_scan_rate_limit(supabase, get_client_ip(request))
    job_result = supabase.table("jobs").select("*").eq("id", job_id).execute()
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_result.data[0]

    if job["mode"] == "owner":
        token = os.environ.get("GITHUB_PAT")
        owner_repo = os.environ.get("OWNER_MODE_REPO", "")
        if not token or "/" not in owner_repo:
            raise HTTPException(status_code=500, detail="Owner-mode filing is not configured")
        owner, repo = owner_repo.split("/", 1)
    else:
        installation_result = (
            supabase.table("installations")
            .select("*")
            .eq("linked_job_id", job_id)
            .execute()
        )
        if not installation_result.data:
            raise HTTPException(
                status_code=400,
                detail="No connected GitHub App installation for this job. Connect GitHub first.",
            )
        installation = installation_result.data[0]
        repo_full_name = installation.get("repo_full_name") or ""
        if "/" not in repo_full_name:
            raise HTTPException(
                status_code=500,
                detail="This installation is missing repo info. Reconnect GitHub and try again.",
            )
        token = get_installation_token(installation["installation_id"])
        owner, repo = repo_full_name.split("/", 1)

    filed: list[dict] = []
    for finding_id in body.finding_ids:
        # Scoped to job_id, not just id -- otherwise a caller could pass a finding_id
        # from an unrelated job and have it filed against whatever repo this job_id
        # resolves to.
        finding_result = (
            supabase.table("findings")
            .select("*")
            .eq("id", finding_id)
            .eq("job_id", job_id)
            .execute()
        )
        if not finding_result.data:
            continue
        finding = finding_result.data[0]
        if finding.get("filed_as_issue"):
            continue  # idempotent: never file the same finding twice, no matter how many times this is called
        issue_url = file_issue(token, owner, repo, finding)
        supabase.table("findings").update(
            {"filed_as_issue": True, "issue_url": issue_url}
        ).eq("id", finding_id).execute()
        filed.append({"finding_id": finding_id, "issue_url": issue_url})

    return {"filed": filed}
