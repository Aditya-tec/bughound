import os

import requests

GITHUB_API = "https://api.github.com"
DISPATCH_REPO = os.environ.get("GITHUB_DISPATCH_REPO", "")  # "owner/bughound"


def fire_run_scan(job_id: str, target_url: str, mode: str) -> None:
    token = os.environ["GITHUB_DISPATCH_TOKEN"]
    owner_repo = DISPATCH_REPO or os.environ["GITHUB_DISPATCH_REPO"]
    resp = requests.post(
        f"{GITHUB_API}/repos/{owner_repo}/dispatches",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "event_type": "run-scan",
            "client_payload": {"job_id": job_id, "target_url": target_url, "mode": mode},
        },
        timeout=10,
    )
    resp.raise_for_status()
