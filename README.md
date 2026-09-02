# BugHound

Autonomous AI agent that explores websites, detects bugs across 8 categories, and auto-files GitHub issues (owner mode) or generates a shareable report (scan mode). Full spec: [bughound-master-build-spec.md](bughound-master-build-spec.md).

## Status

Everything buildable **without live third-party accounts** (Supabase project, Groq/Gemini keys, a real GitHub repo/App) is scaffolded and locally verified. What's left is account creation + live end-to-end wiring — see "What's not verified" below.

### `supabase/`
- `schema.sql` — `jobs`, `findings`, `runs_meta`, `installations` tables (spec section 7)
- The `screenshots` storage bucket has to be created via the Supabase dashboard/CLI — not SQL. Do this when you create the project.

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

## What's not verified yet (needs live accounts/network)

This sandbox has no outbound network access beyond package registries, so none of the following have been run for real — only code-reviewed and import/syntax-checked:
- An actual Supabase insert/query (env vars aren't set — no project exists yet)
- Playwright against a live or local page (the `playwright` Python package installed, but browser binaries need `playwright install`, which needs network)
- Any Groq or Gemini API call (no keys)
- `repository_dispatch` actually reaching GitHub Actions, or the Actions run itself
- Filing a real GitHub issue (needs a PAT or installed GitHub App)

## Next steps (build order, spec section 15)

1. Create the Supabase project, run `supabase/schema.sql`, create the `screenshots` bucket, set `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` in both Vercel and GitHub Actions secrets
2. Get free Groq + Gemini API keys, add as GitHub Actions secrets
3. Push to a public GitHub repo, set `GITHUB_DISPATCH_TOKEN` (Vercel) + confirm `run_scan.yml` fires on a test job
4. Import into Vercel, set env vars, confirm the Next.js + Python functions deploy together (or split into two projects per spec section 4's fallback)
5. Run the crawler against `fixtures/broken-test-site/` to validate each tier fires at least one finding (checklist item 1)
6. Register the GitHub App for Mode B+, generate a PAT for owner mode
7. First real end-to-end run in owner mode against one of your own projects

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
