# BugHound — Master Build Spec (v1, $0 budget, no card required)

This is the complete, standalone reference for building BugHound end to end. Feed this whole document to your AI coding agent as context/prompt — it contains everything needed: architecture, schema, API contracts, agent logic, deployment steps, and build order.

---

## 0. What BugHound is

An autonomous AI agent that explores any website like a real user, detects real bugs across 8 categories (functional, accessibility, performance, SEO, security hygiene, responsive design, visual/UX, and multi-step flows), and either auto-files GitHub issues (on repos you own) or generates a shareable read-only report (for sites you don't own) — with a consent-based upgrade path for site owners who want to authorize auto-filing. Fully self-hosted, fully free, no credit/debit card required anywhere in the stack.

---

## 1. Tech stack (verified free, no card, as of build time)

| Layer | Tool | Notes |
|---|---|---|
| Frontend | Next.js on **Vercel** (Hobby tier) | No card required |
| Backend API | **FastAPI as Python serverless functions on Vercel** — same project as frontend | Vercel officially supports the Python runtime (ASGI/FastAPI) via an `api/` directory. This replaces Hugging Face Spaces, which now requires a paid PRO plan for Docker/Gradio SDKs as of July 2026 — free accounts can no longer create Docker Spaces. |
| Heavy compute (the actual scan) | **GitHub Actions** | Free and effectively unlimited for public repos — this is where Playwright + the agent actually run, not on Vercel |
| LLM reasoning (text-only) | **Groq** (fast, free, no card — same provider used in your earlier RupeeRead/Workflow Agent projects) | Groq's catalog churns fast: `llama-3.3-70b-versatile` (used in your earlier projects) was deprecated June 17, 2026. Check `console.groq.com/docs/models` at build time for the current best free text model — `openai/gpt-oss-120b` or `qwen/qwen3.6-27b` were the recommended migrations as of the deprecation notice. No card, no phone verification, but exact RPM/RPD varies a lot by model — verify per-model limits before building. Read the model ID from an env var, don't hardcode it. |
| Vision (screenshot judgment) | **Google Gemini API** (Gemini 2.5 Flash) | Groq's only vision-capable model, Llama 4 Scout, was *also* deprecated June 17, 2026, with no confirmed free vision replacement on Groq as of this writing — so keep vision calls on Gemini, which has a stable, actively-supported multimodal free tier. This only covers Tiers 6-7, so Gemini's tighter free quota goes further than if it carried the whole agent. No card required. Free-tier rate limits are volatile (Google cut quotas in Dec 2025) — verify current RPM/RPD at ai.google.dev/pricing before building, and build with retry/backoff regardless. |
| Browser automation | **Playwright (Python)**, run inside the GitHub Actions runner | Free, open source |
| Accessibility | **axe-core** via CDN injection + `page.evaluate` | Free, same engine Lighthouse uses |
| DB + file storage | **Supabase** (Postgres + Storage), free tier | No card required |
| Issue filing (owner mode) | **GitHub REST API** with a personal access token | Always free |
| Issue filing (scan mode, consent-based) | **GitHub App** (installation tokens, `issues:write` scope only) | Free to register, no card |

**Why this works at $0 forever, not just a free trial:** GitHub Actions gives real compute (2 vCPU+) for the expensive part (browser automation) without needing an always-on paid server. Vercel's Python functions handle only lightweight orchestration (create a job row, fire a dispatch event, read Supabase, call the GitHub API) — well within free serverless limits. Nothing in this stack asks for payment details at signup.

---

## 2. Operating modes

**Mode A — Owner mode.** Used on repos you own (your own deployed projects). Full autopilot: agent finds a bug → auto-files a real GitHub issue via your personal access token. This is your flagship, verifiable demo.

**Mode B — Scan mode.** Used when anyone submits a public URL through your dashboard. Read-only, non-destructive exploration (like Lighthouse/PageSpeed). Findings go into a shareable report page. Nothing is filed anywhere automatically.

**Mode B+ — Consent-based filing (stretch, still free).** A report viewer who owns that site can click "Connect GitHub," install a GitHub App on their own repo (they pick exactly which repo via GitHub's own UI), then selectively file findings as issues. Always requires an explicit confirm step before writing anything.

---

## 3. Bug detection taxonomy — 8 mandatory tiers

Every tier ships in v1; these are categories, not a priority order. Tiers 1-6 are deterministic (free libraries, no LLM cost). Tier 7 uses Gemini (vision). Tier 8 uses Groq (text reasoning over recorded page states, no screenshots involved).

1. **Functional/console** — uncaught JS exceptions, failed network requests (4xx/5xx), broken internal/external links, broken images, forms that submit with empty required fields and no validation error.
2. **Accessibility** (via `axe-core`) — missing alt text, insufficient contrast, missing form labels, missing/incorrect ARIA, keyboard traps.
3. **Performance / Core Web Vitals** — LCP and CLS over threshold (via the `web-vitals` JS library injected into the page), render-blocking resources, oversized images, slow API responses.
4. **SEO & meta hygiene** — missing/duplicate `<title>`, missing meta description, missing/duplicate H1, missing canonical tag, broken Open Graph tags, missing/broken `sitemap.xml`/`robots.txt`.
5. **Security hygiene** (strictly passive — header/cookie inspection only, no active probing) — missing CSP/X-Frame-Options/HSTS/X-Content-Type-Options, cookies missing Secure/HttpOnly, mixed content, exposed `.map` files already linked from the page.
6. **Responsive/mobile** — missing viewport meta tag, horizontal overflow at mobile width, touch targets under 44px (all deterministic via Playwright viewport + bounding-box measurement), plus LLM-vision comparison across breakpoints for overlap/unreadable text.
7. **Visual & UX judgment** (Gemini vision call) — layout breakage, silent form-submit failures, dead-end navigation, state inconsistency (e.g. cart count not updating — before/after screenshot diff), leftover placeholder content, misleading CTAs.
8. **Multi-step flow consistency** (LangGraph-guided, spans multiple pages) — checkout/signup flow breaking midway, session/state loss on navigation, back-button breaking state, broken pagination.

---

## 4. Repo structure (single monorepo, matches your chosen setup)

```
bughound/
├── apps/
│   └── web/                       # Next.js frontend (Vercel)
│       ├── app/
│       │   ├── page.tsx           # landing + URL submission form
│       │   ├── scan/[jobId]/      # live run view
│       │   ├── reports/[jobId]/   # public shareable report
│       │   └── connect-github/    # Mode B+ install flow
│       ├── components/
│       └── package.json
│
├── api/                            # Vercel Python serverless functions (FastAPI/ASGI)
│   ├── index.py                    # FastAPI app entrypoint — Vercel auto-detects this
│   ├── routers/
│   │   ├── jobs.py
│   │   ├── github_app.py
│   │   └── issues.py
│   ├── models/
│   ├── requirements.txt
│   └── pyproject.toml              # declares FastAPI entrypoint for Vercel's Python runtime
│
├── agent/                          # Runs ONLY inside GitHub Actions, never deployed to Vercel
│   ├── main.py                     # entrypoint invoked by the Actions workflow
│   ├── crawler.py
│   ├── explorer_graph.py           # LangGraph agent definition
│   ├── checks/
│   │   ├── tier1_functional.py
│   │   ├── tier2_accessibility.py
│   │   ├── tier3_performance.py
│   │   ├── tier4_seo.py
│   │   ├── tier5_security.py
│   │   ├── tier6_responsive.py
│   │   ├── tier7_visual_ux.py
│   │   └── tier8_flow.py
│   ├── guardrails.py               # robots.txt, rate limit, timeout, domain allowlist
│   ├── github_issue_filer.py
│   ├── supabase_client.py
│   └── requirements.txt
│
├── .github/
│   └── workflows/
│       └── run_scan.yml            # triggered via repository_dispatch
│
├── supabase/
│   └── schema.sql
│
├── vercel.json                     # if needed to combine Next.js + Python functions in one project
└── README.md
```

**Note on Vercel + Python + Next.js in one project:** Vercel's Python runtime auto-detects a FastAPI app from `api/index.py` + `requirements.txt`/`pyproject.toml`. If combining this with the Next.js frontend in a single Vercel project causes framework-detection conflicts, the fallback (still 100% free, no card) is to deploy `api/` as a **second, separate Vercel project** pointed at that subfolder, and set `NEXT_PUBLIC_API_URL` in the frontend to that second project's URL. Check `vercel.com/docs/functions/runtimes/python` at build time since this page has been updated recently and specifics may shift.

---

## 5. Accounts to create (all free, none require a card)

1. **GitHub** — create a new public repo named `bughound`
2. **Supabase** — new project (free tier) → note the project URL, anon key, and service role key
3. **Google AI Studio** (aistudio.google.com) — generate a free Gemini API key
4. **Vercel** — sign up with GitHub, import the `bughound` repo
5. **GitHub Personal Access Token** (fine-grained, scoped to `issues:write` on your own repos) — for Mode A
6. **GitHub App** (github.com/settings/apps/new) — for Mode B+; see section 10

---

## 6. Environment variables / secrets

**GitHub repo secrets** (used by the Actions workflow — this is where every LLM call actually happens, not in Vercel):
- `GROQ_API_KEY` (text reasoning)
- `GROQ_MODEL` (e.g. `openai/gpt-oss-120b` — keep this as a var, not hardcoded, since Groq deprecates models often)
- `GEMINI_API_KEY` (vision only, Tiers 6-7)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side only, never exposed to frontend)
- `GITHUB_PAT` (for owner-mode issue filing)
- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY` (base64-encoded .pem contents)

**Vercel project env vars** (for the `api/` functions — these only orchestrate, they never call an LLM):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GITHUB_DISPATCH_TOKEN` (a PAT scoped to `repo` on `bughound`, used only to fire `repository_dispatch`)
- `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_CLIENT_SECRET`

**Vercel project env vars** (for the Next.js frontend, `NEXT_PUBLIC_` prefix = exposed to browser, keep minimal):
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (anon key only — never the service role key)

---

## 7. Supabase schema

```sql
create extension if not exists "pgcrypto";

create table jobs (
  id uuid primary key default gen_random_uuid(),
  target_url text not null,
  mode text not null check (mode in ('scan','owner')),
  status text not null default 'queued' check (status in ('queued','running','completed','failed')),
  pages_crawled int default 0,
  actions_taken int default 0,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz default now()
);

create table findings (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs(id) on delete cascade,
  tier int not null,               -- 1 through 8
  category text not null,          -- 'console_error','broken_link','a11y','performance','seo','security','responsive','visual_ux','flow'
  severity text not null check (severity in ('low','medium','high','critical')),
  page_url text not null,
  title text not null,
  description text,
  repro_steps text,
  screenshot_url text,
  filed_as_issue boolean default false,
  issue_url text,
  created_at timestamptz default now()
);

create table runs_meta (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs(id) on delete cascade,
  gemini_calls int default 0,
  tokens_used int default 0,
  estimated_cost_usd numeric default 0,
  duration_seconds int,
  created_at timestamptz default now()
);

create table installations (
  id uuid primary key default gen_random_uuid(),
  installation_id bigint not null,
  repo_full_name text not null,
  linked_job_id uuid references jobs(id),
  connected_at timestamptz default now()
);
```

Also create a **Storage bucket** named `screenshots` (public read, or served via signed URLs if you want tighter access control).

---

## 8. End-to-end flow

```
Next.js dashboard (Vercel)
   | user submits target_url + picks mode
   v
FastAPI functions (Vercel, same project)
   | inserts row into `jobs`, fires repository_dispatch to GitHub
   v
GitHub Actions runner (free compute)
   | Playwright + LangGraph agent, Gemini for reasoning/vision
   | crawls target site, runs all 8 tiers, captures screenshots
   v
   +--> Supabase (findings, screenshots, job status)
   |         ^
   |         |  dashboard polls this for live results
   |
   +--> IF mode=owner        -> GitHub REST API (PAT)        -> issue filed automatically
        IF mode=scan         -> nothing filed; report page renders from Supabase data
        IF mode=scan + Mode B+ opt-in -> GitHub App installation token -> issues filed on user-selected findings only, after explicit confirm
```

---

## 9. Backend API contract (FastAPI on Vercel)

- `POST /api/jobs` — body `{target_url, mode}` → creates a `jobs` row, fires `repository_dispatch` (event type `run-scan`, payload `{job_id, target_url, mode}`) → returns `{job_id}`
- `GET /api/jobs/{id}` — returns job status + findings (reads Supabase)
- `GET /api/jobs/{id}/report` — public report data for scan mode
- `POST /api/jobs/{id}/file-issues` — body `{finding_ids: [...]}` → uses PAT (owner mode) or stored installation token (Mode B+) to file selected issues via GitHub REST API, writes `issue_url` back to `findings`
- `GET /api/github/app/callback` — receives `installation_id` after a user installs the GitHub App, stores it in `installations` linked to the job
- `POST /api/github/webhook` — optional, for GitHub App lifecycle events (installation removed, etc.)

Keep every one of these endpoints fast (sub-few-seconds) — all heavy work happens in the GitHub Actions runner, never inside a Vercel function.

---

## 10. GitHub App setup (for Mode B+)

1. Go to `github.com/settings/apps/new`
2. Name it (e.g. "BugHound"), set Homepage URL to your Vercel frontend URL, set Callback URL to `.../api/github/app/callback`
3. Under **Repository permissions**, grant only **Issues: Read & write** — nothing else
4. Leave webhooks off unless you specifically need installation-removed events
5. Under "Where can this GitHub App be installed?" choose **Any account** (public)
6. Generate a private key (downloads a `.pem`) — base64-encode it and store as `GITHUB_APP_PRIVATE_KEY`
7. Note the App ID and Client ID
8. Installation URL for the "Connect GitHub" button: `https://github.com/apps/<your-app-slug>/installations/new`

**Filing flow:** sign a short-lived JWT with the App's private key (RS256, via `PyJWT` + `cryptography`) → exchange it at `POST /app/installations/{installation_id}/access_tokens` for an installation token (expires ~1hr, scoped only to the granted repo and `issues:write`) → use that token for `POST /repos/{owner}/{repo}/issues` calls.

---

## 11. Agent design (runs inside GitHub Actions, `agent/` folder)

**LangGraph loop (`explorer_graph.py`):**
1. `plan_actions` — **Groq** (text-only) reads the current page's accessibility tree/DOM structure and decides what's testable (forms, nav, buttons) — no screenshot needed for this step
2. `execute_action` — Playwright performs one action (click, fill, submit)
3. `run_tier_checks` — runs tiers 1–6 (deterministic, no LLM) after every page load/action
4. `judge_findings` — **Gemini** (vision) reviews the screenshot for tier 7 issues — the only step in the loop that needs to see the page visually
5. `record_finding` — writes any findings to Supabase immediately (don't batch — if the run times out, partial results are still useful)
6. Loop back to `plan_actions` until the action budget is exhausted or no more testable elements remain
7. `finalize_job` — for multi-page flows, run tier 8 checks (**Groq**, text-only reasoning over recorded page states) across the recorded page sequence; mark job `completed`

Two providers, two responsibilities: Groq handles every text-reasoning call (cheap, fast, generous), Gemini handles only the handful of calls per run that require actual vision (Tiers 6-7). This keeps both free tiers well within budget.

**Per-tier implementation notes:**
- Tier 1: `page.on("console")` and `page.on("response")` listeners; concurrent `HEAD` requests (rate-limited) to every extracted `<a href>` for link-checking; form check by submitting with empty required fields and pattern-matching for visible validation text.
- Tier 2: inject `axe-core` via `<script>` tag, call `axe.run()` through `page.evaluate`, parse the violations array directly.
- Tier 3: inject the `web-vitals` JS library, capture LCP/CLS callbacks via `page.evaluate`; track response timing through Playwright's request/response events (flag anything over ~1500ms).
- Tier 4: parse DOM for `<title>`, meta description, H1 count, canonical tag, OG tags; fetch `/robots.txt` and `/sitemap.xml` and check status codes.
- Tier 5: inspect the main document response headers and `Set-Cookie` headers only — derive checks from what the page itself returns, never probe paths the page doesn't already reference.
- Tier 6: `page.set_viewport_size()` at 375×667 (mobile), 768×1024 (tablet), 1280×800 (desktop); check `scrollWidth` vs viewport width for overflow; measure clickable-element bounding boxes for sub-44px targets.
- Tier 7: send the screenshot to Gemini with a prompt requesting structured JSON output describing any detected issues, matched against the categories in section 3.
- Tier 8: the LangGraph agent maintains flow state across a page sequence (e.g. signup step 1→2→3), checks expected state persists at the end (session cookie, URL pattern, confirmation element); test `page.go_back()` for back-button state integrity.

---

## 12. Guardrails (build these alongside Tier 1, not as an afterthought)

- Parse and respect `robots.txt` before crawling any page
- Rate-limit requests to the target (e.g. max 1 req/sec)
- Read-only by default — no real payment/destructive form submissions unless a page is explicitly marked test-safe
- Custom `User-Agent: BugHoundBot (contact: your-email)`
- Hard timeout on the whole run (e.g. 5 minutes), enforced with `asyncio.wait_for`
- Domain allowlist — only crawl pages on the target's own domain; external links get a `HEAD` check only, never followed
- Action budget cap (e.g. 15 actions per run) to bound run time and both Groq/Gemini usage

---

## 13. GitHub Actions workflow (`run_scan.yml` skeleton)

```yaml
name: Run Scan
on:
  repository_dispatch:
    types: [run-scan]

jobs:
  scan:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          pip install -r agent/requirements.txt
          playwright install --with-deps chromium
      - name: Run scan
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GROQ_MODEL: ${{ secrets.GROQ_MODEL }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          GITHUB_PAT: ${{ secrets.GITHUB_PAT }}
        run: |
          python agent/main.py \
            --job-id "${{ github.event.client_payload.job_id }}" \
            --target-url "${{ github.event.client_payload.target_url }}" \
            --mode "${{ github.event.client_payload.mode }}"
```

---

## 14. Deployment sequence (order of operations)

1. Create the Supabase project, run `schema.sql`, create the `screenshots` storage bucket, copy the URL + both keys
2. Get a free Groq API key from console.groq.com (check current model catalog first) and a free Gemini API key from Google AI Studio
3. Push the monorepo to a new public GitHub repo `bughound`
4. Add all GitHub repo secrets (section 6)
5. Import the repo into Vercel; confirm the Python `api/` functions deploy alongside the Next.js frontend (or as a second Vercel project if needed — see section 4 note)
6. Add all Vercel env vars (section 6)
7. Generate the GitHub PAT, add it as both a repo secret and a Vercel env var
8. Register the GitHub App (section 10), add its credentials as secrets/env vars, install it on the `bughound` repo itself (this enables owner-mode testing immediately)
9. Submit your first scan against one of your own live projects (e.g. RupeeRead) in **owner mode** to validate the entire pipeline end to end
10. Confirm: job appears in Supabase → Action triggers → findings get written → a real issue gets filed on your repo → the dashboard reflects live status throughout

---

## 15. Build order (dependency-ordered, no time estimates)

1. Supabase schema + a minimal FastAPI `POST /api/jobs` that just inserts a row — no scanning yet
2. Wire the GitHub Actions dispatch: confirm a "hello world" job round-trips from Vercel → Actions → back into Supabase before adding any real agent logic
3. Playwright crawler + Tier 1 checks — get one real, verifiable bug detected end to end
4. Tier 2 (axe-core), Tier 4 (SEO), Tier 5 (security headers) — all "load the page, run a check" style, fast to layer on
5. Tier 3 (performance) + Tier 6 (responsive)
6. LangGraph exploration agent + Gemini integration → Tier 7 (visual/UX)
7. Tier 8 (multi-step flow) — requires the agent to chain actions across pages
8. Owner-mode GitHub issue auto-filing
9. Scan-mode public report page + live dashboard polish
10. GitHub App registration + Mode B+ consent-based filing flow
11. Guardrails (robots.txt, rate limiting, timeouts, domain allowlist) — build this alongside step 3, don't defer it
12. Run against your own 5 existing live projects, confirm everything end to end, write the technical post

---

## 16. Validation checklist before calling it done

- [ ] A scan against a known-broken test page correctly surfaces at least one finding per tier (build a small deliberately-broken test page if needed to validate each tier)
- [ ] Owner-mode run files a real, correctly-formatted GitHub issue with screenshot + repro steps
- [ ] Scan-mode run never writes to any repo, only produces a report
- [ ] Mode B+ requires an explicit confirm click before filing anything
- [ ] robots.txt is respected — verify by pointing at a page with a disallow rule
- [ ] Rate limiting is active — verify request timing in logs
- [ ] Run times out cleanly at the hard limit instead of hanging
- [ ] Dashboard reflects live status while a scan is running, not just after completion
- [ ] Full run costs stay within both free-tier Groq and Gemini quotas (check `runs_meta` for calls/tokens per run, per provider)

---

## 17. What ships publicly

1. Live dashboard where anyone can submit a URL and get a report
2. A section showing real, filed GitHub issues from your own projects (owner mode) — your credibility anchor
3. Open-source repo with architecture diagram + documented guardrails
4. Technical writeup: what it detects, how the mode A/B/B+ split avoids becoming a spam bot, and an honest comparison to funded competitors (Momentic, Octomind) — "the open-source, self-hostable, $0 version of what they charge for" is a stronger pitch than claiming novelty
5. 60–90s Loom walkthrough

**Cold DM line:** "Built BugHound — an open-source agent that autonomously explores live sites and finds real bugs across 8 categories (functional, accessibility, performance, SEO, security, responsive, UX, flow). On my own projects it auto-files GitHub issues; for anyone else it generates a read-only report instead of touching your repo. Ran it against my own stack — here's what it found: [link]. Would love your critique."
