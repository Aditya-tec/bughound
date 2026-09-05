"""Playwright-driven crawler: loads a page, extracts internal links, tracks console/network events."""

from dataclasses import dataclass, field
from urllib.parse import urldefrag, urlparse

from playwright.sync_api import Page, ConsoleMessage, Response

from guardrails import USER_AGENT, DomainAllowlist
from security import is_public_hostname


@dataclass
class ConsoleEvent:
    type: str
    text: str


@dataclass
class NetworkEvent:
    url: str
    status: int
    method: str
    duration_ms: float | None = None


@dataclass
class PageLoadResult:
    url: str
    console_events: list[ConsoleEvent] = field(default_factory=list)
    network_events: list[NetworkEvent] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)


def load_page(page: Page, url: str, allowlist: DomainAllowlist) -> PageLoadResult:
    """Navigates to `url`, recording console/network activity for tier 1 checks."""
    result = PageLoadResult(url=url)

    def on_console(msg: ConsoleMessage) -> None:
        result.console_events.append(ConsoleEvent(type=msg.type, text=msg.text))

    def on_response(response: Response) -> None:
        duration_ms = None
        try:
            timing = response.request.timing
            if timing and timing.get("responseEnd", -1) >= 0:
                duration_ms = timing["responseEnd"] - timing.get("requestStart", 0)
        except Exception:
            duration_ms = None
        result.network_events.append(
            NetworkEvent(
                url=response.url,
                status=response.status,
                method=response.request.method,
                duration_ms=duration_ms,
            )
        )

    def on_page_error(exc: Exception) -> None:
        result.page_errors.append(str(exc))

    page.on("console", on_console)
    page.on("response", on_response)
    page.on("pageerror", on_page_error)

    # networkidle never fires on sites with continuous background activity (polling,
    # analytics beacons, websockets) -- confirmed live: a real scan against an
    # unrelated site crashed the whole job on Page.goto: Timeout 30000ms exceeded.
    # A timeout here doesn't mean the page failed to load -- Playwright still
    # navigates, it just never sees 500ms of network silence -- so proceed with
    # whatever's there instead of losing the entire scan, and don't re-navigate
    # (the console/response listeners are already attached above; a second goto()
    # would duplicate every captured event).
    try:
        page.goto(url, wait_until="networkidle", timeout=15000)
    except Exception:
        pass

    anchors = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    for href in anchors:
        clean, _ = urldefrag(href)
        if not clean.startswith(("http://", "https://")):
            continue
        if allowlist.is_internal(clean):
            result.internal_links.append(clean)
        else:
            result.external_links.append(clean)

    page.remove_listener("console", on_console)
    page.remove_listener("response", on_response)
    page.remove_listener("pageerror", on_page_error)

    return result


def install_ssrf_route_guard(page: Page) -> None:
    """Blocks every main-frame navigation whose destination resolves off the public
    internet -- including mid-crawl redirects, which the entry-URL SSRF checks in
    agent/security.py and api/security.py never see. A malicious page can pass the
    initial validation, then 302 to http://169.254.169.254/ or an internal IP;
    Playwright follows redirects transparently during page.goto() and page.click(),
    so without this, that hop reaches the target unchecked. Applied once per page via
    page.route(), so it covers every navigation for the session -- the initial load,
    every redirect hop within it, and every later click-driven navigation in the
    explore loop.
    """

    def handle_route(route) -> None:
        request = route.request
        if request.is_navigation_request() and request.frame == page.main_frame:
            hostname = urlparse(request.url).hostname or ""
            if not hostname or not is_public_hostname(hostname):
                route.abort()
                return
        route.continue_()

    page.route("**/*", handle_route)


def new_context_page(browser):
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()
    install_ssrf_route_guard(page)
    return context, page
