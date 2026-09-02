"""Tier 2 — accessibility via axe-core, injected via CDN and run through page.evaluate."""

from playwright.sync_api import Page

from findings import Finding

AXE_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"

IMPACT_TO_SEVERITY = {
    "critical": "critical",
    "serious": "high",
    "moderate": "medium",
    "minor": "low",
}


def check_accessibility(page: Page, page_url: str) -> list[Finding]:
    page.add_script_tag(url=AXE_CDN_URL)
    results = page.evaluate("async () => await axe.run()")

    findings: list[Finding] = []
    for violation in results.get("violations", []):
        impact = violation.get("impact") or "minor"
        severity = IMPACT_TO_SEVERITY.get(impact, "low")
        nodes = violation.get("nodes", [])
        targets = ", ".join(
            t for node in nodes[:5] for t in node.get("target", [])
        )
        findings.append(
            Finding(
                tier=2,
                category="a11y",
                severity=severity,
                page_url=page_url,
                title=f"{violation.get('id')}: {violation.get('help')}",
                description=violation.get("description", ""),
                repro_steps=f"axe-core rule '{violation.get('id')}' failed on: {targets}",
            )
        )
    return findings
