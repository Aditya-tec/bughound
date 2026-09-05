"""Unit tests for the Gemini-call gating in explorer_graph.judge_findings.

Real usage data (see the comment in explorer_graph.py) showed this loop burning
6-8 Gemini calls on a single page -- enough to exhaust the entire 20/day free-tier
quota within 3 scans. These tests lock in the fix: only the first and last pass
through the explore loop should ever reach Gemini, not every intermediate action.
"""

from unittest.mock import MagicMock, patch

from explorer_graph import judge_findings
from guardrails import ActionBudget


def _state(page_states, done, remaining):
    budget = ActionBudget(max_actions=remaining + 5)
    budget.consume(5)  # leaves `remaining` actions left, regardless of max_actions chosen
    return {
        "job_id": "test-job",
        "page": MagicMock(),
        "action_budget": budget,
        "metrics": MagicMock(),
        "page_states": page_states,
        "done": done,
        "planned_action": {},
        "tried_selectors": [],
        "allowlist": MagicMock(),
    }


@patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key-for-test"})
@patch("explorer_graph.tier7_visual_ux.judge_screenshot")
@patch("explorer_graph.upload_screenshot")
def test_first_pass_calls_gemini(mock_upload, mock_judge):
    state = _state(page_states=[{"step": 0}], done=False, remaining=3)
    judge_findings(state)
    mock_judge.assert_called_once()


@patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key-for-test"})
@patch("explorer_graph.tier7_visual_ux.judge_screenshot")
@patch("explorer_graph.upload_screenshot")
def test_intermediate_pass_skips_gemini(mock_upload, mock_judge):
    # Several page states already recorded, not done, budget remains -- this is an
    # intermediate iteration and must NOT burn a Gemini call.
    state = _state(page_states=[{"step": 0}, {"step": 1}, {"step": 2}], done=False, remaining=3)
    judge_findings(state)
    mock_judge.assert_not_called()


@patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key-for-test"})
@patch("explorer_graph.tier7_visual_ux.judge_screenshot")
@patch("explorer_graph.upload_screenshot")
def test_last_pass_via_done_flag_calls_gemini(mock_upload, mock_judge):
    state = _state(page_states=[{"step": 0}, {"step": 1}, {"step": 2}], done=True, remaining=3)
    judge_findings(state)
    mock_judge.assert_called_once()


@patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key-for-test"})
@patch("explorer_graph.tier7_visual_ux.judge_screenshot")
@patch("explorer_graph.upload_screenshot")
def test_last_pass_via_exhausted_budget_calls_gemini(mock_upload, mock_judge):
    state = _state(page_states=[{"step": 0}, {"step": 1}], done=False, remaining=0)
    judge_findings(state)
    mock_judge.assert_called_once()
