"""Files findings as GitHub issues. Owner mode uses a PAT; Mode B+ uses a GitHub App
installation token (see api/routers/github_app.py for the JWT/token-exchange flow)."""

import requests

from findings import Finding

GITHUB_API = "https://api.github.com"
MAX_ISSUE_TEXT = 2000


def _plain_text(value: str | None) -> str:
    text = (value or "").replace("\r", " ").replace("\n", " ")[:MAX_ISSUE_TEXT]
    return text.translate(str.maketrans("", "", "`*_[]()#!>|~"))


def _issue_body(finding: Finding) -> str:
    lines = [
        _plain_text(finding.description),
        "",
        f"Page: {_plain_text(finding.page_url)}",
        f"Tier: {finding.tier} ({_plain_text(finding.category)})",
        f"Severity: {_plain_text(finding.severity)}",
    ]
    if finding.repro_steps:
        lines += ["", "Repro steps:", _plain_text(finding.repro_steps)]
    lines += ["", "Filed automatically by BugHound."]
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
            "title": _plain_text(f"[BugHound][Tier {finding.tier}] {finding.title}"),
            "body": _issue_body(finding),
            "labels": ["bughound", finding.category, finding.severity],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]
