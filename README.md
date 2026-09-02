# BugHound

Autonomous AI agent that explores websites, detects bugs across 8 categories, and auto-files GitHub issues (owner mode) or generates a shareable report (scan mode). Full spec: [bughound-master-build-spec.md](bughound-master-build-spec.md).

## Status

**Scan mode works end-to-end for real** — a live GitHub Actions run against `https://example.com` completed with `status: completed`, produced 20 findings across tiers 2/4/5/6/7/8, uploaded working screenshots to Supabase Storage, and wrote real `gemini_calls`/`tokens_used` to `runs_meta`. That took 4 real CI runs to get right — see "Bugs found and fixed via real runs" below. Owner mode (auto-filing) and Mode B+ are still unproven; Vercel isn't deployed yet.

### `supabase/`
- `schema.sql` — `jobs`, `findings`, `runs_meta`, `installations` tables (spec section 7), applied to a live project
- The `screenshots` bucket exists and is confirmed serving real public PNGs (verified via direct HTTP fetch of an uploaded screenshot)

### `api/` (FastAPI on Vercel)
All endpoints from the spec's API contract (section 9) are implemented and verified to boot/route correctly with `TestClient`:
- `POST /api/jobs` — inserts a `jobs` row, fires `repository_dispatch` via `github_dispatch.py`
- `GET /api/jobs/{id}`, `GET /api/jobs/{id}/report`
- `POST /api/jobs/{id}/file-issues` — owner mode (PAT) or Mode B+ (GitHub App installation token via `github_app_auth.py`)
- `GET /api/github/app/callback`, `POST /api/github/webhook`
- `vercel.json` routes all `/api/*` to `api/index.py` so Vercel treats it as one function, not one per file

### `agent/` (runs only inside GitHub Actions)
All 8 tiers, guardrails, the crawler, and the LangGraph explore loop are implemented (spec sections 11–12):
- `guardrails.py` — robots.txt, rate limiting, action budget, domain allowlist, run timeout
- `crawler.py` — Playwright page load + console/network capture + link extraction
- `checks/tier1..tier6` — deterministic checks (functional, a11y via axe-core, performance via web-vitals, SEO, security headers, responsive)
- `checks/tier7_visual_ux.py` — Gemini vision judgment (uses the current `google-genai` SDK, not the deprecated `google-generativeai`)
- `checks/tier8_flow.py` — Groq-based multi-step flow consistency check
- `explorer_graph.py` — LangGraph plan→act→check→judge loop
- `github_issue_filer.py`, `supabase_client.py`, `main.py` (entrypoint)
- `agent/requirements.txt` is pinned to a set that installs cleanly together (`google-genai` needs `httpx>=0.28.1`, which forced a `supabase` bump to 2.31.0 — verified with a clean venv install)

### `.github/workflows/run_scan.yml`
Dispatches on `repository_dispatch: run-scan`, installs `agent/requirements.txt` + Playwright's Chromium, runs `agent/main.py` with the job's secrets/env.

### `apps/web/` (Next.js, App Router)
- `/` — URL submission form (scan vs. owner mode)
- `/scan/[jobId]` — live polling view
- `/reports/[jobId]` — public read-only report
- `/connect-github` — Mode B+ GitHub App install + consent-based issue filing UI

Verified: `tsc --noEmit` clean, `npm run build` produces all 5 routes successfully, and the
dev server actually serves the landing page (confirmed via curl — real HTTP 200 + rendered
markup, not just a successful build).

### `fixtures/broken-test-site/`
A deliberately-broken static page (`index.html` + `step2.html`) covering at least one issue per tier — console error, failed fetch, broken image/links, missing alt text, low contrast, unlabeled required field, no viewport meta, sub-44px touch target, horizontal overflow, missing meta description/canonical/OG tags, duplicate H1, leftover "Lorem ipsum", misleading CTA, and a 2-step flow that silently drops state. Serve it locally (`python -m http.server` from that folder) once the crawler is pointed at a live browser, to satisfy the validation checklist's "known-broken test page" item.

## Bugs found and fixed via real runs

Four live CI runs against `example.com` (not local mocks) surfaced four real bugs, each fixed and verified before moving on:

1. **CSP blocked CDN script injection** — `page.add_script_tag(url=...)` inserts a real `<script>` element, which is subject to the *target site's own* CSP. `example.com`'s CSP blocks `cdnjs.cloudflare.com`, so tier 2 (axe-core) and tier 3 (web-vitals) failed on any CSP-hardened site. Fixed by fetching the library once and injecting via `page.evaluate()` (`agent/inject.py`), which bypasses page CSP. Verified against a purpose-built `script-src 'self'` test page.
2. **Explore loop ignored the domain allowlist** — `crawler.py` and the tier 1 link checker respect it, but `explorer_graph.execute_action` didn't check it before clicking. A real run followed a link off `example.com` onto `iana.org` and then `afrinic.net`. Fixed by reverting any click that lands off-domain; verified with a two-port local test simulating cross-domain navigation.
3. **Action budget too slow for real LLM latency** — 15 actions (the spec's example figure) at ~25s/iteration with real Groq+Gemini calls blew through the 300s timeout guardrail (which itself fired correctly — the run failed cleanly, didn't hang). Dropped the default to 8.
4. **One LLM failure crashed the whole run** — Gemini's free tier caps `gemini-2.5-flash` at 20 requests/day; hitting that quota mid-run raised an uncaught exception that discarded every tier 1-6 finding already recorded. Fixed all three LLM call sites (tier 7 Gemini, tier 8 Groq, the explore loop's Groq planner) to log and degrade to empty instead of crashing.

Also fixed two silent gaps caught by re-reading the schema against the code: `findings.screenshot_url` was never populated (screenshots were captured but discarded), and `runs_meta.gemini_calls`/`tokens_used` stayed at their defaults forever. Both wired up via `agent/metrics.py` and `supabase_client.upload_screenshot`.

## Next steps

1. **Vercel** — not deployed. Needed to actually exercise `POST /api/jobs` and the dashboard against live data instead of direct script calls.
2. **Owner mode** — needs a `GITHUB_PAT` (deferred on purpose) to prove real issue-filing.
3. **Mode B+** — needs a registered GitHub App (github.com/settings/apps/new, can't be done via API).
4. Run against `fixtures/broken-test-site/` the same way `example.com` was tested, to confirm all 8 tiers fire on a known-broken page (checklist item 1) — tiers 1/2/4/6 already proven against it locally pre-CI; 3/5/7/8 only proven against `example.com` so far.

## Local dev

**API:**
```
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r api/requirements.txt uvicorn
cp api/.env.example api/.env    # fill in SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
cd api && uvicorn index:app --reload
```

**Agent (once you have Supabase/Groq/Gemini credentials):**
```
python -m venv .venv-agent
source .venv-agent/Scripts/activate
pip install -r agent/requirements.txt
playwright install --with-deps chromium
cp agent/.env.example agent/.env  # if you add one; otherwise export the vars from spec section 6
cd agent && python main.py --job-id <uuid> --target-url https://example.com --mode scan
```

**Frontend:**
```
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```
