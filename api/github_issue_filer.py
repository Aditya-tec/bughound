"""Files a finding row (as read from Supabase) as a GitHub issue. Kept separate from
agent/github_issue_filer.py on purpose — api/ and agent/ are deployed independently and
never share imports."""

import requests

GITHUB_API = "https://api.github.com"


def _issue_body(finding: dict) -> str:
    lines = [
        finding.get("description") or "",
        "",
        f"**Page:** {finding['page_url']}",
        f"**Tier:** {finding['tier']} ({finding['category']})",
        f"**Severity:** {finding['severity']}",
    ]
    if finding.get("repro_steps"):
        lines += ["", "**Repro steps:**", finding["repro_steps"]]
    if finding.get("screenshot_url"):
        lines += ["", f"![screenshot]({finding['screenshot_url']})"]
    lines += ["", "_Filed via BugHound._"]
    return "\n".join(lines)


def file_issue(token: str, owner: str, repo: str, finding: dict) -> str:
    resp = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": f"[BugHound][Tier {finding['tier']}] {finding['title']}",
            "body": _issue_body(finding),
            "labels": ["bughound", finding["category"], finding["severity"]],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]
