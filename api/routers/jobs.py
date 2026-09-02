from fastapi import APIRouter, HTTPException

from api.github_dispatch import fire_run_scan
from api.models.job import CreateJobRequest, CreateJobResponse
from api.supabase_client import get_supabase

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=CreateJobResponse)
def create_job(body: CreateJobRequest) -> CreateJobResponse:
    supabase = get_supabase()
    result = (
        supabase.table("jobs")
        .insert({"target_url": str(body.target_url), "mode": body.mode})
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")

    job_id = result.data[0]["id"]

    try:
        fire_run_scan(job_id, str(body.target_url), body.mode)
    except Exception as exc:
        supabase.table("jobs").update({"status": "failed"}).eq("id", job_id).execute()
        raise HTTPException(status_code=502, detail=f"Failed to dispatch scan: {exc}") from exc

    return CreateJobResponse(job_id=job_id)


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    supabase = get_supabase()
    job_result = supabase.table("jobs").select("*").eq("id", job_id).execute()
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    findings_result = (
        supabase.table("findings").select("*").eq("job_id", job_id).execute()
    )
    return {"job": job_result.data[0], "findings": findings_result.data}


@router.get("/{job_id}/report")
def get_job_report(job_id: str) -> dict:
    """Public, read-only report data — same shape as get_job, served at a route the
    frontend's public /reports/[jobId] page can hit without auth."""
    return get_job(job_id)
