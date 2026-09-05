"""Unit test for crawler.load_page's resilience to a networkidle timeout.

Real bug, found via a real scan: a site with continuous background network
activity (polling/analytics/websockets) never satisfies Playwright's networkidle
wait condition, so page.goto() throws and the entire job crashed uncaught. Confirmed
live against https://api-testing-platform-two.vercel.app -- Page.goto: Timeout
30000ms exceeded.
"""

from unittest.mock import MagicMock

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from crawler import load_page
from guardrails import DomainAllowlist


def test_load_page_survives_a_networkidle_timeout():
    page = MagicMock()
    page.goto.side_effect = PlaywrightTimeoutError("Page.goto: Timeout 30000ms exceeded.")
    page.eval_on_selector_all.return_value = []

    allowlist = DomainAllowlist("https://example.com/")

    result = load_page(page, "https://example.com/", allowlist)  # must not raise

    assert result.url == "https://example.com/"
    page.goto.assert_called_once()  # never re-navigates after the timeout


def test_load_page_does_not_call_goto_twice_on_timeout():
    # A second goto() after the first times out would re-attach the same event
    # listeners' worth of duplicate console/network events for one page load.
    page = MagicMock()
    page.goto.side_effect = PlaywrightTimeoutError("timed out")
    page.eval_on_selector_all.return_value = []
    allowlist = DomainAllowlist("https://example.com/")

    load_page(page, "https://example.com/", allowlist)

    assert page.goto.call_count == 1
