"""Fetches third-party JS libraries once and injects them via page.evaluate rather than
page.add_script_tag(url=...). Some target sites' own CSP (script-src) blocks loading a
<script src> from a CDN — a real failure seen scanning example.com. page.evaluate runs
through the browser automation protocol and is not subject to the page's CSP."""

from functools import lru_cache

import requests
from playwright.sync_api import Page

from guardrails import USER_AGENT

MAX_SCRIPT_BYTES = 2 * 1024 * 1024


@lru_cache
def _fetch_script(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    try:
        resp.raise_for_status()
        content_length = resp.headers.get("content-length")
        if content_length and int(content_length) > MAX_SCRIPT_BYTES:
            raise ValueError("Injected script exceeds response size limit")
        content = resp.content
        if len(content) > MAX_SCRIPT_BYTES:
            raise ValueError("Injected script exceeds response size limit")
        return content.decode(resp.encoding or "utf-8", errors="replace")
    finally:
        resp.close()


def inject_script(page: Page, url: str) -> None:
    source = _fetch_script(url)
    page.evaluate(source)
