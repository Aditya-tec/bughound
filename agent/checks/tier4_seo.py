"""Tier 4 — SEO & meta hygiene."""

import requests
from playwright.sync_api import Page
from urllib.parse import urlparse

from findings import Finding
from guardrails import USER_AGENT


def check_seo(page: Page, page_url: str) -> list[Finding]:
    findings: list[Finding] = []

    meta = page.evaluate(
        """
        () => ({
            title: document.title || '',
            metaDescription: document.querySelector('meta[name="description"]')?.content || null,
            h1Count: document.querySelectorAll('h1').length,
            canonical: document.querySelector('link[rel="canonical"]')?.href || null,
            ogTitle: document.querySelector('meta[property="og:title"]')?.content || null,
            ogImage: document.querySelector('meta[property="og:image"]')?.content || null,
        })
        """
    )

    if not meta["title"].strip():
        findings.append(
            Finding(
                tier=4, category="seo", severity="medium", page_url=page_url,
                title="Missing <title>",
                description="The page has no <title> element or it is empty.",
                repro_steps=f"View source of {page_url}.",
            )
        )

    if not meta["metaDescription"]:
        findings.append(
            Finding(
                tier=4, category="seo", severity="low", page_url=page_url,
                title="Missing meta description",
                description="No <meta name=\"description\"> tag found.",
                repro_steps=f"View source of {page_url}.",
            )
        )

    if meta["h1Count"] == 0:
        findings.append(
            Finding(
                tier=4, category="seo", severity="medium", page_url=page_url,
                title="Missing H1",
                description="No <h1> element found on the page.",
                repro_steps=f"View source of {page_url}.",
            )
        )
    elif meta["h1Count"] > 1:
        findings.append(
            Finding(
                tier=4, category="seo", severity="low", page_url=page_url,
                title=f"Duplicate H1 ({meta['h1Count']} found)",
                description="Multiple <h1> elements found; expected exactly one.",
                repro_steps=f"View source of {page_url}.",
            )
        )

    if not meta["canonical"]:
        findings.append(
            Finding(
                tier=4, category="seo", severity="low", page_url=page_url,
                title="Missing canonical tag",
                description="No <link rel=\"canonical\"> tag found.",
                repro_steps=f"View source of {page_url}.",
            )
        )

    if not meta["ogTitle"] or not meta["ogImage"]:
        findings.append(
            Finding(
                tier=4, category="seo", severity="low", page_url=page_url,
                title="Incomplete Open Graph tags",
                description="Missing og:title and/or og:image.",
                repro_steps=f"View source of {page_url}.",
            )
        )

    return findings


def check_site_files(base_url: str) -> list[Finding]:
    """robots.txt and sitemap.xml presence, checked once per domain."""
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    findings: list[Finding] = []

    for path, label in (("/robots.txt", "robots.txt"), ("/sitemap.xml", "sitemap.xml")):
        url = origin + path
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=5)
            if resp.status_code >= 400:
                findings.append(
                    Finding(
                        tier=4, category="seo", severity="low", page_url=origin,
                        title=f"Missing or broken {label}",
                        description=f"{url} returned HTTP {resp.status_code}.",
                        repro_steps=f"Fetch {url}.",
                    )
                )
        except requests.RequestException as exc:
            findings.append(
                Finding(
                    tier=4, category="seo", severity="low", page_url=origin,
                    title=f"Missing or broken {label}",
                    description=str(exc),
                    repro_steps=f"Fetch {url}.",
                )
            )

    return findings
