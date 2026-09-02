"""LangGraph exploration loop (spec section 11). Tiers 1/3/4/5/6 run once per page load in
main.py, outside this graph; this graph drives the interactive plan -> act -> check -> judge
loop that discovers additional pages/states within the action budget, plus tier 2 + tier 6
viewport checks after each action, and hands the recorded state sequence to tier 8 in
`main.py` once the graph finishes."""

import json
import os
from typing import Any, TypedDict

from groq import Groq
from langgraph.graph import END, StateGraph
from playwright.sync_api import Page

from checks import tier2_accessibility, tier6_responsive, tier7_visual_ux
from findings import Finding
from guardrails import ActionBudget, DomainAllowlist
from metrics import RunMetrics
from supabase_client import record_finding, upload_screenshot

PLAN_PROMPT = """You are exploring a web page to find testable interactive elements.
Given this simplified list of interactive elements, pick ONE next action to try that you
have not already tried this run: click a link/button, or fill+submit a form field.

Interactive elements:
{dom_summary}

Already tried this run: {tried}

Respond with ONLY JSON: {{"action": "click"|"fill_submit"|"none", "selector": str|null, "reason": str}}
Use "none" if there is nothing new worth testing.
"""


class ExplorerState(TypedDict):
    job_id: str
    page: Any  # playwright.sync_api.Page
    action_budget: ActionBudget
    metrics: RunMetrics
    allowlist: DomainAllowlist
    tried_selectors: list[str]
    planned_action: dict
    page_states: list[dict]
    done: bool


def _get_groq_client() -> Groq | None:
    api_key = os.environ.get("GROQ_API_KEY")
    return Groq(api_key=api_key) if api_key else None


def _dom_summary(page: Page) -> str:
    return page.evaluate(
        """
        () => Array.from(document.querySelectorAll('a, button, input, select, textarea'))
            .slice(0, 40)
            .map((e, i) => {
                if (!e.id) e.setAttribute('data-bh-idx', String(i));
                const sel = e.id ? '#' + e.id : `[data-bh-idx="${i}"]`;
                const label = (e.innerText || e.value || e.placeholder || '').slice(0, 40);
                return `${sel} <${e.tagName.toLowerCase()}> "${label}"`;
            })
            .join('\\n')
        """
    )


def plan_actions(state: ExplorerState) -> ExplorerState:
    if state["action_budget"].remaining <= 0:
        return {**state, "planned_action": {"action": "none"}, "done": True}

    client = _get_groq_client()
    if client is None:
        return {**state, "planned_action": {"action": "none"}, "done": True}

    page = state["page"]
    dom_summary = _dom_summary(page)
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": PLAN_PROMPT.format(
                    dom_summary=dom_summary, tried=", ".join(state["tried_selectors"]) or "none"
                ),
            }
        ],
        temperature=0,
    )
    usage = getattr(response, "usage", None)
    state["metrics"].record_groq(getattr(usage, "total_tokens", 0) or 0)
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        planned = json.loads(text)
    except json.JSONDecodeError:
        planned = {"action": "none"}

    return {**state, "planned_action": planned, "done": planned.get("action") == "none"}


def execute_action(state: ExplorerState) -> ExplorerState:
    action = state["planned_action"]
    if state["done"] or action.get("action") == "none":
        return state

    page = state["page"]
    selector = action.get("selector")
    tried = [*state["tried_selectors"]]
    before_url = page.url

    if selector:
        tried.append(selector)
        try:
            if action["action"] == "click":
                page.locator(selector).first.click(timeout=3000)
                page.wait_for_load_state("networkidle", timeout=5000)
            elif action["action"] == "fill_submit":
                page.locator(selector).first.fill("test@example.com")
        except Exception:
            pass  # element not actionable — still counts against the budget below

        # Domain allowlist applies to agent-driven navigation too (spec section 12): a click
        # can land on an external link Groq picked from the DOM summary. Never explore off-domain.
        if not state["allowlist"].is_internal(page.url):
            try:
                page.go_back(wait_until="networkidle", timeout=5000)
            except Exception:
                pass
            if not state["allowlist"].is_internal(page.url):
                page.goto(before_url, wait_until="networkidle")

    state["action_budget"].consume()
    return {**state, "tried_selectors": tried}


def run_tier_checks(state: ExplorerState) -> ExplorerState:
    page = state["page"]
    findings: list[Finding] = []
    findings += tier2_accessibility.check_accessibility(page, page.url)
    findings += tier6_responsive.check_viewport_meta(page, page.url)

    for finding in findings:
        record_finding(state["job_id"], finding)

    page_states = [
        *state["page_states"],
        {
            "step": len(state["page_states"]),
            "url": page.url,
            "action": state["planned_action"],
            "summary": page.title(),
        },
    ]
    return {**state, "page_states": page_states}


def judge_findings(state: ExplorerState) -> ExplorerState:
    if os.environ.get("GEMINI_API_KEY"):
        page = state["page"]
        screenshot = page.screenshot()
        try:
            screenshot_url = upload_screenshot(state["job_id"], screenshot)
        except Exception:
            screenshot_url = None
        findings = tier7_visual_ux.judge_screenshot(
            screenshot, page.url, screenshot_url=screenshot_url, metrics=state["metrics"]
        )
        for finding in findings:
            record_finding(state["job_id"], finding)
    return state


def should_continue(state: ExplorerState) -> str:
    if state["done"] or state["action_budget"].remaining <= 0:
        return END
    return "plan_actions"


def build_graph():
    graph = StateGraph(ExplorerState)
    graph.add_node("plan_actions", plan_actions)
    graph.add_node("execute_action", execute_action)
    graph.add_node("run_tier_checks", run_tier_checks)
    graph.add_node("judge_findings", judge_findings)

    graph.set_entry_point("plan_actions")
    graph.add_edge("plan_actions", "execute_action")
    graph.add_edge("execute_action", "run_tier_checks")
    graph.add_edge("run_tier_checks", "judge_findings")
    graph.add_conditional_edges(
        "judge_findings", should_continue, {"plan_actions": "plan_actions", END: END}
    )

    return graph.compile()


def run_exploration(
    job_id: str,
    page: Page,
    action_budget: ActionBudget,
    metrics: RunMetrics,
    allowlist: DomainAllowlist,
) -> list[dict]:
    """Runs the explore loop to completion and returns the recorded page-state sequence
    (input to tier 8, run separately in main.py once all pages have been explored)."""
    app = build_graph()
    initial_state: ExplorerState = {
        "job_id": job_id,
        "page": page,
        "action_budget": action_budget,
        "metrics": metrics,
        "allowlist": allowlist,
        "tried_selectors": [],
        "planned_action": {},
        "page_states": [],
        "done": False,
    }
    final_state = app.invoke(initial_state)
    return final_state["page_states"]
