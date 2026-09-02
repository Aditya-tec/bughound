"""Files findings as GitHub issues. Owner mode uses a PAT; Mode B+ uses a GitHub App
installation token (see api/routers/github_app.py for the JWT/token-exchange flow)."""

import requests

from findings import Finding

GITHUB_API = "https://api.github.com"


def _issue_body(finding: Finding) -> str:
    lines = [
        finding.description or "",
        "",
        f"**Page:** {finding.page_url}",
        f"**Tier:** {finding.tier} ({finding.category})",
        f"**Severity:** {finding.severity}",
    ]
    if finding.repro_steps:
        lines += ["", "**Repro steps:**", finding.repro_steps]
    if finding.screenshot_url:
        lines += ["", f"![screenshot]({finding.screenshot_url})"]
    lines += ["", "_Filed automatically by [BugHound](https://github.com)._"]
    return "\n".join(lines)


def file_issue(token: str, owner: str, repo: str, finding: Finding) -> str:
    """Files one finding as a GitHub issue. Returns the created issue's HTML URL."""
    resp = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": f"[BugHound][Tier {finding.tier}] {finding.title}",
            "body": _issue_body(finding),
            "labels": ["bughound", finding.category, finding.severity],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]
