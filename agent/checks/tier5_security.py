"""Tier 5 — passive security hygiene: response headers and cookies only, no active probing."""

from playwright.sync_api import Response

from findings import Finding

REQUIRED_HEADERS = {
    "content-security-policy": "Missing Content-Security-Policy header",
    "x-frame-options": "Missing X-Frame-Options header",
    "strict-transport-security": "Missing Strict-Transport-Security (HSTS) header",
    "x-content-type-options": "Missing X-Content-Type-Options header",
}


def check_security_headers(main_response: Response, page_url: str) -> list[Finding]:
    findings: list[Finding] = []
    headers = {k.lower(): v for k, v in main_response.headers.items()}

    for header, message in REQUIRED_HEADERS.items():
        if header not in headers:
            findings.append(
                Finding(
                    tier=5, category="security", severity="low", page_url=page_url,
                    title=message,
                    description=f"Response headers for {page_url} do not include '{header}'.",
                    repro_steps=f"Inspect response headers for {page_url}.",
                )
            )

    set_cookie_headers = main_response.all_headers().get("set-cookie", "")
    if set_cookie_headers and page_url.startswith("https://"):
        for cookie in set_cookie_headers.split("\n"):
            if not cookie.strip():
                continue
            lower = cookie.lower()
            missing = [
                flag for flag in ("secure", "httponly") if flag not in lower
            ]
            if missing:
                findings.append(
                    Finding(
                        tier=5, category="security", severity="medium", page_url=page_url,
                        title=f"Cookie missing {', '.join(missing)} flag(s)",
                        description=cookie.split("=")[0] + " is missing recommended cookie flags.",
                        repro_steps=f"Inspect Set-Cookie headers for {page_url}.",
                    )
                )

    return findings


def check_mixed_content(page_html: str, page_url: str) -> list[Finding]:
    if not page_url.startswith("https://"):
        return []
    if "src=\"http://" in page_html or "href=\"http://" in page_html:
        return [
            Finding(
                tier=5, category="security", severity="medium", page_url=page_url,
                title="Mixed content: insecure http:// resource on an https:// page",
                description="An http:// resource reference was found on an https:// page.",
                repro_steps=f"View source of {page_url} and search for src=\"http:// or href=\"http://.",
            )
        ]
    return []
