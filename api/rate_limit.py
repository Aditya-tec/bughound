"""Per-IP daily cap on job creation.

The existing guardrails throttle requests the agent makes *to the scan
target*; nothing throttled requests *to this API*. Once the URL is public,
one enthusiastic visitor or bot could burn a full day's Groq/Gemini quota and
GitHub Actions minutes. This checks Supabase for how many jobs this IP has
created in the last 24h before a new job row is inserted.

Requires the `client_ip` column added to `jobs` (see supabase/schema.sql).
If that migration hasn't been applied yet, the count query fails and this
fails open (allows the request) rather than hard-breaking job creation.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

DAILY_LIMIT_PER_IP = 5


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_scan_rate_limit(supabase, client_ip: str) -> None:
    if not client_ip or client_ip == "unknown":
        return

    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        result = (
            supabase.table("jobs")
            .select("id", count="exact")
            .eq("client_ip", client_ip)
            .gte("created_at", since)
            .execute()
        )
    except Exception:
        return

    count = result.count if result.count is not None else len(result.data)
    if count >= DAILY_LIMIT_PER_IP:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached: max {DAILY_LIMIT_PER_IP} scans per IP per day. Try again tomorrow.",
        )
