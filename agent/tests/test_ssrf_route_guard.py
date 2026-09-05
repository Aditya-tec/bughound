"""Integration test: a real Playwright browser against a real local server, proving
the SSRF route guard actually stops a mid-crawl redirect to a blocked host.

This is the fix for the most common SSRF-guard bypass technique: api/security.py and
agent/security.py both validate target_url up front, but Playwright follows HTTP
redirects transparently during page.goto()/click(), and neither of those checks
re-runs on each hop. A malicious site can pass the entry check, then 302 to
http://169.254.169.254/ or an internal IP mid-navigation. install_ssrf_route_guard
(in crawler.py) intercepts every main-frame navigation, including each redirect hop,
and aborts any that resolve off the public internet.

Needs a real browser -- this is the one agent test that does, hence the separate
Playwright browser install step in .github/workflows/ci.yml.
"""

import http.server
import threading

import pytest
from playwright.sync_api import sync_playwright

from crawler import new_context_page


class _RedirectToBlockedHost(http.server.BaseHTTPRequestHandler):
    """A 'malicious' server: looks fine on the surface, 302s to a blocked host."""

    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "http://localhost:8999/internal")
        self.end_headers()

    def log_message(self, *args):
        pass  # quiet test output


@pytest.fixture(scope="module")
def redirect_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), _RedirectToBlockedHost)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def test_redirect_to_blocked_host_is_aborted(redirect_server, browser):
    context, page = new_context_page(browser)
    with pytest.raises(Exception):  # Playwright raises on an aborted navigation
        page.goto(f"http://127.0.0.1:{redirect_server}/", timeout=8000)
    context.close()


def test_legitimate_navigation_still_works(browser):
    context, page = new_context_page(browser)
    page.goto("https://example.com/", timeout=15000)
    assert "example.com" in page.url
    context.close()
