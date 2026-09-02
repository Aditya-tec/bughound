"""Tier 3 — Core Web Vitals (LCP/CLS via web-vitals) and slow response detection."""

from playwright.sync_api import Page

from crawler import PageLoadResult
from findings import Finding

WEB_VITALS_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/web-vitals/4.2.4/web-vitals.iife.js"

LCP_THRESHOLD_MS = 2500
CLS_THRESHOLD = 0.1
SLOW_RESPONSE_THRESHOLD_MS = 1500


def measure_web_vitals(page: Page) -> dict:
    page.add_script_tag(url=WEB_VITALS_CDN_URL)
    return page.evaluate(
        """
        () => new Promise((resolve) => {
            const result = {};
            let settled = false;
            const finish = () => {
                if (!settled) {
                    settled = true;
                    resolve(result);
                }
            };
            webVitals.onLCP((metric) => { result.lcp = metric.value; });
            webVitals.onCLS((metric) => { result.cls = metric.value; });
            setTimeout(finish, 2000);
        })
        """
    )


def check_performance(page: Page, load_result: PageLoadResult) -> list[Finding]:
    findings: list[Finding] = []

    try:
        vitals = measure_web_vitals(page)
    except Exception:
        vitals = {}

    lcp = vitals.get("lcp")
    if lcp is not None and lcp > LCP_THRESHOLD_MS:
        findings.append(
            Finding(
                tier=3,
                category="performance",
                severity="high" if lcp > LCP_THRESHOLD_MS * 1.6 else "medium",
                page_url=load_result.url,
                title=f"LCP is {lcp:.0f}ms (threshold {LCP_THRESHOLD_MS}ms)",
                description="Largest Contentful Paint exceeds the recommended threshold.",
                repro_steps=f"Load {load_result.url} and measure LCP via web-vitals.",
            )
        )

    cls = vitals.get("cls")
    if cls is not None and cls > CLS_THRESHOLD:
        findings.append(
            Finding(
                tier=3,
                category="performance",
                severity="medium",
                page_url=load_result.url,
                title=f"CLS is {cls:.2f} (threshold {CLS_THRESHOLD})",
                description="Cumulative Layout Shift exceeds the recommended threshold.",
                repro_steps=f"Load {load_result.url} and measure CLS via web-vitals.",
            )
        )

    for event in load_result.network_events:
        if event.status < 400 and event.duration_ms and event.duration_ms > SLOW_RESPONSE_THRESHOLD_MS:
            findings.append(
                Finding(
                    tier=3,
                    category="performance",
                    severity="medium",
                    page_url=load_result.url,
                    title=f"Slow response: {event.url} took {event.duration_ms:.0f}ms",
                    description=f"Response exceeded {SLOW_RESPONSE_THRESHOLD_MS}ms.",
                    repro_steps=f"Load {load_result.url} and inspect network timing for {event.url}.",
                )
            )

    return findings
