"""Tier 6 — responsive/mobile: viewport meta, horizontal overflow, touch target size."""

from playwright.sync_api import Page

from findings import Finding

VIEWPORTS = {
    "mobile": {"width": 375, "height": 667},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1280, "height": 800},
}

MIN_TOUCH_TARGET_PX = 44


def check_viewport_meta(page: Page, page_url: str) -> list[Finding]:
    has_viewport = page.evaluate(
        "() => !!document.querySelector('meta[name=\"viewport\"]')"
    )
    if not has_viewport:
        return [
            Finding(
                tier=6, category="responsive", severity="medium", page_url=page_url,
                title="Missing viewport meta tag",
                description="No <meta name=\"viewport\"> tag found; mobile rendering may be unreliable.",
                repro_steps=f"View source of {page_url}.",
            )
        ]
    return []


def check_responsive_at_breakpoints(page: Page, page_url: str) -> list[Finding]:
    findings: list[Finding] = []

    for name, size in VIEWPORTS.items():
        page.set_viewport_size(size)
        page.wait_for_timeout(150)

        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > window.innerWidth"
        )
        if overflow:
            findings.append(
                Finding(
                    tier=6, category="responsive", severity="medium", page_url=page_url,
                    title=f"Horizontal overflow at {name} width ({size['width']}px)",
                    description="document.documentElement.scrollWidth exceeds the viewport width.",
                    repro_steps=f"Load {page_url} at {size['width']}x{size['height']}.",
                )
            )

        if name != "desktop":
            small_targets = page.eval_on_selector_all(
                "a, button, input[type=submit], input[type=button]",
                """
                els => els.filter(e => {
                    const r = e.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && (r.width < 44 || r.height < 44);
                }).length
                """,
            )
            if small_targets > 0:
                findings.append(
                    Finding(
                        tier=6, category="responsive", severity="low", page_url=page_url,
                        title=f"{small_targets} touch target(s) under {MIN_TOUCH_TARGET_PX}px at {name} width",
                        description="Clickable elements smaller than the recommended 44x44px touch target.",
                        repro_steps=f"Load {page_url} at {size['width']}x{size['height']} and inspect bounding boxes.",
                    )
                )

    page.set_viewport_size(VIEWPORTS["desktop"])
    return findings
