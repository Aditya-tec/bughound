"""Entrypoint invoked by .github/workflows/run_scan.yml inside the GitHub Actions runner."""

import argparse
import os
import sys
import time
import traceback

from playwright.sync_api import sync_playwright

from checks import tier1_functional, tier2_accessibility, tier3_performance, tier4_seo, tier5_security, tier6_responsive
from checks import tier8_flow
from crawler import load_page, new_context_page
from explorer_graph import run_exploration
from findings import Finding
from github_issue_filer import file_issue
from guardrails import (
    ActionBudget,
    DomainAllowlist,
    RateLimiter,
    RobotsChecker,
    RobotsDisallowed,
    RunClock,
    RunTimedOut,
)
from metrics import RunMetrics
from security import SSRFValidationError, validate_public_target
from supabase_client import get_supabase, record_finding, record_run_meta, update_job

RUN_TIMEOUT_SECONDS = 300
# 15 (the spec's example figure) is too many for real Groq+Gemini latency per iteration --
# a live run against example.com averaged ~25s/action and blew through the 300s timeout.
# 8 leaves headroom for the tier 1-6 pass plus tier 8 after the loop.
ACTION_BUDGET = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--mode", required=True, choices=["scan", "owner"])
    parser.add_argument("--owner-repo", default=os.environ.get("OWNER_MODE_REPO", ""))
    return parser.parse_args()


def run_page_checks(page, main_response, load_result, allowlist, rate_limiter) -> list[Finding]:
    findings: list[Finding] = []
    findings += tier1_functional.check_console_and_network(load_result)
    findings += tier1_functional.check_links(load_result, rate_limiter)
    findings += tier1_functional.check_broken_images(page, load_result.url)
    findings += tier1_functional.check_empty_form_submit(page, load_result.url)
    findings += tier2_accessibility.check_accessibility(page, load_result.url)
    findings += tier3_performance.check_performance(page, load_result)
    findings += tier4_seo.check_seo(page, load_result.url)
    findings += tier4_seo.check_site_files(load_result.url)
    if main_response is not None:
        findings += tier5_security.check_security_headers(main_response, load_result.url)
    findings += tier5_security.check_mixed_content(page.content(), load_result.url)
    findings += tier6_responsive.check_viewport_meta(page, load_result.url)
    findings += tier6_responsive.check_responsive_at_breakpoints(page, load_result.url)
    return findings


def file_issues_for_findings(job_id: str, findings_with_ids: list[tuple[str, Finding]], owner_repo: str) -> None:
    token = os.environ.get("GITHUB_PAT")
    if not token or not owner_repo or "/" not in owner_repo:
        return
    owner, repo = owner_repo.split("/", 1)
    supabase = get_supabase()

    for finding_id, finding in findings_with_ids:
        try:
            issue_url = file_issue(token, owner, repo, finding)
            supabase.table("findings").update(
                {"filed_as_issue": True, "issue_url": issue_url}
            ).eq("id", finding_id).execute()
        except Exception:
            traceback.print_exc()


def main() -> int:
    args = parse_args()
    job_id = args.job_id
    target_url = args.target_url

    # Re-check right before the crawler connects, independent of the check already
    # done at job-creation time in api/security.py -- a hostname's DNS answer can
    # change between the two (DNS rebinding), and this runner is the cloud VM with
    # its own metadata service, so this is the check that actually matters.
    try:
        validate_public_target(target_url)
    except SSRFValidationError as exc:
        print(f"Refusing to scan non-public target: {exc}", file=sys.stderr)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        update_job(job_id, status="failed", started_at=now, finished_at=now)
        return 1

    started_at = time.time()
    update_job(job_id, status="running", started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    clock = RunClock(RUN_TIMEOUT_SECONDS)
    allowlist = DomainAllowlist(target_url)
    rate_limiter = RateLimiter()
    action_budget = ActionBudget(ACTION_BUDGET)
    robots = RobotsChecker(target_url)
    metrics = RunMetrics()

    all_findings_with_ids: list[tuple[str, Finding]] = []
    page_states: list[dict] = []
    pages_crawled = 0
    status = "completed"

    try:
        robots.assert_allowed(target_url)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context, page = new_context_page(browser)

            main_response = None

            def capture_main_response(response):
                nonlocal main_response
                if response.url == target_url or main_response is None:
                    main_response = response

            page.on("response", capture_main_response)
            rate_limiter.wait()
            load_result = load_page(page, target_url, allowlist)
            page.remove_listener("response", capture_main_response)
            pages_crawled += 1

            clock.assert_not_expired()
            findings = run_page_checks(page, main_response, load_result, allowlist, rate_limiter)
            for finding in findings:
                row = record_finding(job_id, finding)
                all_findings_with_ids.append((row.get("id"), finding))

            clock.assert_not_expired()
            page_states = run_exploration(job_id, page, action_budget, metrics, allowlist)

            update_job(job_id, pages_crawled=pages_crawled, actions_taken=action_budget.actions_taken)

            clock.assert_not_expired()
            flow_findings = tier8_flow.check_flow_consistency(page_states, metrics)
            for finding in flow_findings:
                row = record_finding(job_id, finding)
                all_findings_with_ids.append((row.get("id"), finding))

            browser.close()

        if args.mode == "owner":
            file_issues_for_findings(job_id, all_findings_with_ids, args.owner_repo)

    except RobotsDisallowed as exc:
        status = "failed"
        print(f"robots.txt disallowed the scan: {exc}", file=sys.stderr)
    except RunTimedOut as exc:
        status = "failed"
        print(f"Run timed out: {exc}", file=sys.stderr)
    except Exception:
        status = "failed"
        traceback.print_exc()
    finally:
        duration = int(time.time() - started_at)
        update_job(
            job_id,
            status=status,
            finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            pages_crawled=pages_crawled,
            actions_taken=action_budget.actions_taken,
        )
        record_run_meta(
            job_id,
            duration_seconds=duration,
            gemini_calls=metrics.gemini_calls,
            tokens_used=metrics.tokens_used,
        )

    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
