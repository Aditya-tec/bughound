"""Tier 1 — functional/console: JS errors, failed requests, broken links/images, unvalidated forms."""

import requests
from playwright.sync_api import Page

from crawler import PageLoadResult
from findings import Finding
from guardrails import USER_AGENT, RateLimiter

BROKEN_STATUS_THRESHOLD = 400


def check_console_and_network(load_result: PageLoadResult) -> list[Finding]:
    findings: list[Finding] = []

    for event in load_result.console_events:
        if event.type == "error":
            findings.append(
                Finding(
                    tier=1,
                    category="console_error",
                    severity="medium",
                    page_url=load_result.url,
                    title="Uncaught console error",
                    description=event.text,
                    repro_steps=f"Load {load_result.url} and open the browser console.",
                )
            )

    for error in load_result.page_errors:
        findings.append(
            Finding(
                tier=1,
                category="console_error",
                severity="high",
                page_url=load_result.url,
                title="Uncaught JS exception",
                description=error,
                repro_steps=f"Load {load_result.url}; an unhandled exception was thrown.",
            )
        )

    for event in load_result.network_events:
        if event.status >= BROKEN_STATUS_THRESHOLD:
            findings.append(
                Finding(
                    tier=1,
                    category="failed_request",
                    severity="high" if event.status >= 500 else "medium",
                    page_url=load_result.url,
                    title=f"{event.method} {event.url} returned {event.status}",
                    description=f"Request to {event.url} failed with status {event.status}.",
                    repro_steps=f"Load {load_result.url} and inspect the network tab.",
                )
            )

    return findings


def check_links(load_result: PageLoadResult, rate_limiter: RateLimiter) -> list[Finding]:
    """HEAD-checks every extracted link. External links get a HEAD check only, never followed."""
    findings: list[Finding] = []
    seen: set[str] = set()

    for link in [*load_result.internal_links, *load_result.external_links]:
        if link in seen:
            continue
        seen.add(link)
        rate_limiter.wait()
        try:
            resp = requests.head(
                link, headers={"User-Agent": USER_AGENT}, timeout=5, allow_redirects=True
            )
            status = resp.status_code
        except requests.RequestException as exc:
            findings.append(
                Finding(
                    tier=1,
                    category="broken_link",
                    severity="medium",
                    page_url=load_result.url,
                    title=f"Link unreachable: {link}",
                    description=str(exc),
                    repro_steps=f"From {load_result.url}, follow link to {link}.",
                )
            )
            continue

        if status >= BROKEN_STATUS_THRESHOLD:
            findings.append(
                Finding(
                    tier=1,
                    category="broken_link",
                    severity="medium",
                    page_url=load_result.url,
                    title=f"Broken link: {link} ({status})",
                    description=f"Link returned HTTP {status}.",
                    repro_steps=f"From {load_result.url}, follow link to {link}.",
                )
            )

    return findings


def check_broken_images(page: Page, page_url: str) -> list[Finding]:
    broken = page.eval_on_selector_all(
        "img",
        "els => els.filter(e => e.complete && e.naturalWidth === 0).map(e => e.src)",
    )
    return [
        Finding(
            tier=1,
            category="broken_image",
            severity="low",
            page_url=page_url,
            title=f"Broken image: {src}",
            description="Image element failed to load (naturalWidth is 0).",
            repro_steps=f"Load {page_url} and inspect <img src=\"{src}\">.",
        )
        for src in broken
    ]


def check_empty_form_submit(page: Page, page_url: str) -> list[Finding]:
    """Submits each form with empty required fields; flags forms with no visible validation error."""
    findings: list[Finding] = []
    form_count = page.eval_on_selector_all("form", "els => els.length")

    for index in range(form_count):
        form = page.locator("form").nth(index)
        required_inputs = form.locator("[required]")
        if required_inputs.count() == 0:
            continue

        submit_button = form.locator(
            "button[type=submit], input[type=submit]"
        ).first
        if submit_button.count() == 0:
            continue

        try:
            html_before = form.inner_html()
            submit_button.click(timeout=2000)
            page.wait_for_timeout(300)
            html_after = form.inner_html()
            still_on_page = page.locator("form").nth(index).count() > 0
            validation_shown = html_before != html_after
            native_validity = page.eval_on_selector_all(
                "form",
                "els => els.map(e => Array.from(e.querySelectorAll('[required]')).every(i => i.checkValidity()))",
            )[index]

            if still_on_page and not validation_shown and not native_validity:
                findings.append(
                    Finding(
                        tier=1,
                        category="form_no_validation",
                        severity="medium",
                        page_url=page_url,
                        title=f"Form #{index} submits with empty required fields and no visible error",
                        description="No DOM change or native validation message was detected after submitting.",
                        repro_steps=f"On {page_url}, submit form #{index} with required fields left blank.",
                    )
                )
        except Exception:
            # Submitting the form navigated away or the button was not actionable — skip rather
            # than crash the whole tier on one uncooperative form.
            continue

    return findings
