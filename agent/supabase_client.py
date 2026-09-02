import os
import time
import uuid
from functools import lru_cache

from supabase import Client, create_client

from findings import Finding

SCREENSHOTS_BUCKET = "screenshots"


@lru_cache
def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def record_finding(job_id: str, finding: Finding) -> dict:
    """Writes a single finding immediately — findings are never batched, so a run that times
    out mid-scan still leaves partial results in Supabase."""
    supabase = get_supabase()
    result = supabase.table("findings").insert(finding.to_row(job_id)).execute()
    return result.data[0] if result.data else {}


def update_job(job_id: str, **fields) -> None:
    get_supabase().table("jobs").update(fields).eq("id", job_id).execute()


def record_run_meta(job_id: str, **fields) -> None:
    get_supabase().table("runs_meta").insert({"job_id": job_id, **fields}).execute()


def upload_screenshot(job_id: str, screenshot_bytes: bytes) -> str:
    """Uploads a screenshot to the `screenshots` bucket and returns its public URL."""
    supabase = get_supabase()
    path = f"{job_id}/{int(time.time())}-{uuid.uuid4().hex[:8]}.png"
    supabase.storage.from_(SCREENSHOTS_BUCKET).upload(
        path, screenshot_bytes, file_options={"content-type": "image/png"}
    )
    return supabase.storage.from_(SCREENSHOTS_BUCKET).get_public_url(path)
