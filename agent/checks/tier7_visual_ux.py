"""Tier 7 — visual & UX judgment via Gemini vision. Only step in the loop that needs to see the page."""

import json
import os
import sys
import time

from google import genai
from google.genai import types

from findings import Finding
from metrics import RunMetrics

PROMPT = """You are a QA engineer reviewing a screenshot of a live web page for bugs.
Look for: layout breakage, silent form-submit failures, dead-end navigation,
state inconsistency, leftover placeholder content (e.g. "Lorem ipsum", "TODO"),
and misleading call-to-action buttons.

Respond with ONLY a JSON array (no markdown fences). Each element:
{"title": str, "description": str, "severity": "low"|"medium"|"high"|"critical"}
Return [] if nothing notable is found."""

MODEL = "gemini-2.5-flash"
_MAX_RETRIES = 3


def _get_client() -> genai.Client | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def judge_screenshot(
    screenshot_bytes: bytes,
    page_url: str,
    screenshot_url: str | None = None,
    metrics: RunMetrics | None = None,
) -> list[Finding]:
    """Sends a screenshot to Gemini for tier 7 visual/UX judgment. No-ops without GEMINI_API_KEY."""
    client = _get_client()
    if client is None:
        return []

    issues = []
    succeeded = False
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=[
                    PROMPT,
                    types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png"),
                ],
            )
            if metrics is not None:
                usage = getattr(response, "usage_metadata", None)
                tokens = getattr(usage, "total_token_count", 0) or 0
                metrics.record_gemini(tokens)
            text = (response.text or "").strip()
            if text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            issues = json.loads(text)
            succeeded = True
            break
        except Exception as exc:  # retry/backoff on rate limits or transient failures
            # A per-day quota (as opposed to a per-minute rate limit) won't recover within
            # this run — retrying just burns the run's time budget for nothing.
            if "PerDay" in str(exc):
                print(f"tier7: Gemini daily quota exhausted, skipping: {exc}", file=sys.stderr)
                break
            print(f"tier7: Gemini call failed (attempt {attempt + 1}/{_MAX_RETRIES}): {exc}", file=sys.stderr)
            time.sleep(2**attempt)

    if not succeeded:
        # One failed vision call must not discard the deterministic tier 1-6 findings
        # already recorded for this run -- degrade this tier, don't crash the scan.
        return []

    findings: list[Finding] = []
    for issue in issues:
        findings.append(
            Finding(
                tier=7,
                category="visual_ux",
                severity=issue.get("severity", "medium"),
                page_url=page_url,
                title=issue.get("title", "Visual/UX issue"),
                description=issue.get("description", ""),
                repro_steps=f"Load {page_url} and compare against the captured screenshot.",
                screenshot_url=screenshot_url,
            )
        )
    return findings
