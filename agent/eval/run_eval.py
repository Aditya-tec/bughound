"""Runs BugHound against its own deliberately-broken eval fixtures (apps/web/app/eval/)
and reports recall against the documented planted bugs in expected_findings.json.

Usage:
    python agent/eval/run_eval.py [--api-base URL] [--site-base URL] [--out FILE]

Only measures recall (did we catch each planted bug). Precision is NOT
auto-scored -- that requires knowing every real bug on a page, not just the
planted ones -- so each fixture's non-matching findings are printed for
manual review instead of being scored as false positives.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

DEFAULT_API_BASE = "https://bughound-api.vercel.app"
DEFAULT_SITE_BASE = "https://bughound-web.vercel.app"
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 240


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--site-base", default=DEFAULT_SITE_BASE)
    parser.add_argument("--out", default=str(Path(__file__).parent / "last_run_results.json"))
    return parser.parse_args()


def create_job(api_base: str, target_url: str) -> str:
    resp = requests.post(
        f"{api_base}/api/jobs",
        json={"target_url": target_url, "mode": "scan"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["job_id"]


def poll_job(api_base: str, job_id: str) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        resp = requests.get(f"{api_base}/api/jobs/{job_id}", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        status = data["job"]["status"]
        if status in ("completed", "failed"):
            return data
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"Job {job_id} did not finish within {POLL_TIMEOUT_SECONDS}s")


def match_planted_bug(findings: list[dict], tier: int, keywords: list[str]) -> dict | None:
    for finding in findings:
        if finding.get("tier") != tier:
            continue
        title = (finding.get("title") or "").lower()
        if any(kw.lower() in title for kw in keywords):
            return finding
    return None


def main() -> int:
    args = parse_args()
    manifest = json.loads((Path(__file__).parent / "expected_findings.json").read_text())

    results = []
    total_planted = 0
    total_found = 0

    for fixture in manifest["fixtures"]:
        target_url = urljoin(args.site_base + "/", fixture["path"].lstrip("/"))
        print(f"\n=== {fixture['path']} (tier {fixture['tier']}) ===")
        print(f"scanning {target_url} ...")

        try:
            job_id = create_job(args.api_base, target_url)
            job_data = poll_job(args.api_base, job_id)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            results.append({"path": fixture["path"], "tier": fixture["tier"], "error": str(exc)})
            continue

        findings = job_data["findings"]
        status = job_data["job"]["status"]
        print(f"  job {job_id} -> {status}, {len(findings)} findings")

        matched_ids: set[str] = set()
        bug_results = []
        for bug in fixture["planted_bugs"]:
            match = match_planted_bug(findings, fixture["tier"], bug["keywords"])
            total_planted += 1
            if match:
                total_found += 1
                matched_ids.add(match["id"])
                bug_results.append({"label": bug["label"], "found": True, "matched_title": match["title"]})
                print(f"  [x] {bug['label']}  ->  \"{match['title']}\"")
            else:
                bug_results.append({"label": bug["label"], "found": False})
                print(f"  [ ] {bug['label']}  ->  NOT FOUND")

        extra = [f for f in findings if f["id"] not in matched_ids]
        if extra:
            print(f"  {len(extra)} additional finding(s) not in the planted set (review for precision, not auto-scored):")
            for f in extra:
                print(f"      - [tier {f['tier']}] {f['title']}")

        results.append({
            "path": fixture["path"],
            "tier": fixture["tier"],
            "job_id": job_id,
            "status": status,
            "planted_bugs": bug_results,
            "extra_findings": [{"tier": f["tier"], "title": f["title"]} for f in extra],
        })

    recall = total_found / total_planted if total_planted else 0.0
    print(f"\n=== Overall recall: {total_found}/{total_planted} ({recall:.0%}) ===")

    out_path = Path(args.out)
    out_path.write_text(json.dumps({
        "overall_recall": recall,
        "planted_total": total_planted,
        "planted_found": total_found,
        "fixtures": results,
    }, indent=2))
    print(f"Full results written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
