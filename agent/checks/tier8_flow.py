"""Tier 8 — multi-step flow consistency via Groq (text reasoning over recorded page states)."""

import json
import os
import sys

from groq import Groq

from findings import Finding
from metrics import RunMetrics

PROMPT_TEMPLATE = """You are a QA engineer reviewing a recorded sequence of page states from a
multi-step user flow (e.g. signup, checkout, pagination) on the same site.

Each entry has: step index, url, action taken to reach it, and a short DOM/text summary.
Look for: the flow breaking midway, session/state loss on navigation, back-button breaking
state, or broken pagination.

Sequence:
{sequence_json}

Respond with ONLY a JSON array (no markdown fences). Each element:
{{"title": str, "description": str, "severity": "low"|"medium"|"high"|"critical", "page_url": str}}
Return [] if the flow is consistent."""


def _get_client() -> Groq | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def check_flow_consistency(page_states: list[dict], metrics: RunMetrics | None = None) -> list[Finding]:
    """`page_states` is a list of {step, url, action, summary} dicts recorded during the run.

    No-ops (returns []) without GROQ_API_KEY or with fewer than 2 recorded steps — flow
    consistency is meaningless for a single page.
    """
    if len(page_states) < 2:
        return []

    client = _get_client()
    if client is None:
        return []

    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    prompt = PROMPT_TEMPLATE.format(sequence_json=json.dumps(page_states, indent=2))

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
    except Exception as exc:
        # Same principle as tier 7: a Groq failure here must not discard everything
        # already recorded for this run.
        print(f"tier8: Groq call failed, skipping: {exc}", file=sys.stderr)
        return []

    if metrics is not None:
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) or 0
        metrics.record_groq(tokens)
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()

    try:
        issues = json.loads(text)
    except json.JSONDecodeError:
        return []

    return [
        Finding(
            tier=8,
            category="flow",
            severity=issue.get("severity", "medium"),
            page_url=issue.get("page_url", page_states[-1]["url"]),
            title=issue.get("title", "Flow consistency issue"),
            description=issue.get("description", ""),
            repro_steps="Replay the recorded step sequence for this flow.",
        )
        for issue in issues
    ]
