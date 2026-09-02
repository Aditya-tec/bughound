"""Playwright-driven crawler: loads a page, extracts internal links, tracks console/network events."""

from dataclasses import dataclass, field
from urllib.parse import urldefrag

from playwright.sync_api import Page, ConsoleMessage, Response

from guardrails import USER_AGENT, DomainAllowlist


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

    page.goto(url, wait_until="networkidle")

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


def new_context_page(browser):
    context = browser.new_context(user_agent=USER_AGENT)
    return context, context.new_page()
