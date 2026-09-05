"""Files a finding row (as read from Supabase) as a GitHub issue. Kept separate from
agent/github_issue_filer.py on purpose — api/ and agent/ are deployed independently and
never share imports."""

import requests

GITHUB_API = "https://api.github.com"
MAX_ISSUE_TEXT = 2000


def _plain_text(value: str | None) -> str:
    text = (value or "").replace("\r", " ").replace("\n", " ")[:MAX_ISSUE_TEXT]
    return text.translate(str.maketrans("", "", "`*_[]()#!>|~"))


def _issue_body(finding: dict) -> str:
    lines = [
        _plain_text(finding.get("description")),
        "",
        f"Page: {_plain_text(finding['page_url'])}",
        f"Tier: {finding['tier']} ({_plain_text(finding['category'])})",
        f"Severity: {_plain_text(finding['severity'])}",
    ]
    if finding.get("repro_steps"):
        lines += ["", "Repro steps:", _plain_text(finding["repro_steps"])]
    lines += ["", "Filed via BugHound."]
    return "\n".join(lines)


def file_issue(token: str, owner: str, repo: str, finding: dict) -> str:
    resp = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": _plain_text(f"[BugHound][Tier {finding['tier']}] {finding['title']}"),
            "body": _issue_body(finding),
            "labels": ["bughound", finding["category"], finding["severity"]],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]
