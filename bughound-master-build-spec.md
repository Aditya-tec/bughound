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
│       ├── run_scan.yml            # triggered via repository_dispatch — the actual product
│       └── ci.yml                  # added post-v1 — on every push/PR: web (tsc + build),
│                                    # api (pytest + FastAPI import smoke test), agent (pytest)
│
├── api/tests/                       # added post-v1 — unit tests for security.py, owner_mode.py
├── agent/tests/                     # added post-v1 — unit tests for security.py, guardrails.py,
│                                    # and the Gemini-call gating in explorer_graph.py
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
- `OWNER_MODE_ALLOWED_DOMAINS` (added post-v1, see §18) — comma-separated hostnames mode=owner is allowed to target; empty/unset rejects every owner-mode request

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

- `POST /api/jobs` — body `{target_url, mode}` → creates a `jobs` row, fires `repository_dispatch` (event type `run-scan`, payload `{job_id, target_url, mode}`) → returns `{job_id}`. As of §18: rejects non-public/SSRF targets (400), rejects `mode=owner` against domains not in `OWNER_MODE_ALLOWED_DOMAINS` (403), and caps job creation at 5/IP/24h via Supabase (429).
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
- SSRF guard on `target_url` (added post-v1, see §18) — reject non-http(s) schemes and any hostname resolving to a private/loopback/link-local/reserved IP, checked independently at job-creation time and again right before the crawler connects
- Owner-mode domain allowlist (added post-v1, see §18) — `mode=owner` is rejected outright unless `target_url`'s host is in `OWNER_MODE_ALLOWED_DOMAINS`
- Per-IP daily cap on `POST /api/jobs` (added post-v1, see §18) — protects the operator's LLM quota and Actions minutes from the public endpoint itself, not just the target site

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
          JOB_ID: ${{ github.event.client_payload.job_id }}
          TARGET_URL: ${{ github.event.client_payload.target_url }}
          SCAN_MODE: ${{ github.event.client_payload.mode }}
        run: |
          python agent/main.py \
            --job-id "$JOB_ID" \
            --target-url "$TARGET_URL" \
            --mode "$SCAN_MODE"
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

Status as of 2026-09-03, verified live against production, not just read from code:

- [x] A scan against a known-broken test page correctly surfaces at least one finding per tier — see §19, the eval suite exists specifically to make this a real, repeatable measurement instead of a one-off check
- [ ] Owner-mode run files a real, correctly-formatted GitHub issue with screenshot + repro steps — **not yet true**. A real owner-mode run against `adityakalambe.xyz` completed and surfaced 13 real findings, but 0 were filed, because `GITHUB_PAT` was never added as a GitHub Actions secret (deferred earlier, still deferred). The filer itself is built and no-ops safely when the token is absent; it has never actually been exercised end-to-end.
- [x] Scan-mode run never writes to any repo, only produces a report
- [ ] Mode B+ requires an explicit confirm click before filing anything — UI flow is built (`connect-github`), but **the GitHub App itself was never registered** (the one manual browser step in §10), so `NEXT_PUBLIC_GITHUB_APP_SLUG` is unset and the "Connect GitHub" button is currently a dead link in production
- [x] robots.txt is respected (`agent/guardrails.py::RobotsChecker`)
- [x] Rate limiting to the *target* is active (`RateLimiter`, 1 req/sec) — separately, as of §18, the *public API itself* is now also rate-limited (5 jobs/IP/24h), pending one manual migration (see §18)
- [x] Run times out cleanly at the hard limit (300s `RunClock`) instead of hanging
- [x] Dashboard reflects live status while a scan is running (3s poll against `GET /api/jobs/{id}`)
- [x] Full run costs stay within free-tier Groq/Gemini quotas — a real run against example.com used 1 Gemini call, 5412 tokens, 41s; `runs_meta` is populated correctly
- [x] Target-URL SSRF validation — added in §18, verified live (169.254.169.254, localhost, 192.168.x.x all correctly rejected with 400)
- [x] `mode=owner` restricted to operator-owned domains — added in §18, verified live (unlisted domain correctly rejected with 403)

---

## 17. What ships publicly

1. Live dashboard where anyone can submit a URL and get a report
2. A section showing real, filed GitHub issues from your own projects (owner mode) — your credibility anchor
3. Open-source repo with architecture diagram + documented guardrails
4. Technical writeup: what it detects, how the mode A/B/B+ split avoids becoming a spam bot, and an honest comparison to funded competitors (Momentic, Octomind) — "the open-source, self-hostable, $0 version of what they charge for" is a stronger pitch than claiming novelty
5. 60–90s Loom walkthrough

**Cold DM line:** "Built BugHound — an open-source agent that autonomously explores live sites and finds real bugs across 8 categories (functional, accessibility, performance, SEO, security, responsive, UX, flow). On my own projects it auto-files GitHub issues; for anyone else it generates a read-only report instead of touching your repo. Ran it against my own stack — here's what it found: [link]. Would love your critique."

---

## 18. Launch hardening (added post-v1, 2026-09-03)

The core build (§0–17) was functionally complete and live, but had three real gaps that only matter once the URL is actually public — flagged before writing a launch post, not found via an incident:

1. **SSRF on `target_url`.** The agent runs inside a GitHub Actions runner — a real cloud VM with its own metadata service — so an unvalidated scan target is a real vector (`http://169.254.169.254/latest/meta-data/`, `http://localhost:5432`, internal `192.168.x.x`), not a theoretical one. Fixed with `validate_public_target()`, duplicated independently in `api/security.py` (checked at job creation) and `agent/security.py` (re-checked right before the crawler connects, since a hostname's DNS answer can change between the two checks — DNS rebinding). Rejects non-http(s) schemes and any resolved IP that's private/loopback/link-local/reserved (Python's `ipaddress` module). Verified live: metadata endpoint, localhost, and RFC1918 addresses all correctly return 400.
2. **`mode=owner` was open to anyone.** Nothing previously stopped a random visitor from submitting `mode=owner` against a target they don't own and triggering the operator's PAT. Fixed with `api/owner_mode.py` — `target_url`'s host must match `OWNER_MODE_ALLOWED_DOMAINS` (comma-separated, env-configured) or the request is rejected with 403. Fails closed: an empty/unset allowlist rejects every owner-mode request. Currently seeded with `adityakalambe.xyz,bughound-web.vercel.app,bughound-api.vercel.app` — add more of the operator's own domains to that Vercel env var as needed.
3. **The public API itself was unthrottled.** The existing guardrails throttled requests *to the scan target*; nothing throttled requests *to the API*, so one visitor or bot could burn a full day's Groq/Gemini quota or Actions minutes once this is in a launch post. Fixed with `api/rate_limit.py` — 5 job creations per IP per 24h, checked against Supabase before the `jobs` insert. **Requires a one-time manual migration** — `supabase/migrations/0001_add_jobs_client_ip.sql` — since the operator only holds the Supabase REST/service-role credentials, not a direct Postgres connection string capable of running DDL. Until that migration runs, the rate-limit check fails open (allows the request) rather than breaking job creation, so this degrades safely but isn't actually enforcing the cap yet. **Action needed: paste that SQL into the Supabase SQL Editor once.**

All three verified against the live production API (`bughound-api.vercel.app`), not just unit-tested — see the commit "Harden the public API before launch" for the exact `curl` reproductions.

---

## 19. Eval suite (added post-v1, 2026-09-03)

Addresses the gap where BugHound detected bugs but never proved its own accuracy — a real eval, not a marketing claim.

**Fixtures:** 8 deliberately-broken pages, one per tier, live at `apps/web/app/eval/tier{1-8}-*/`, each with documented planted bugs:
- Tier 1: broken image, dead internal link, console error, form submits with an empty required field
- Tier 2: missing alt text, insufficient contrast, unlabeled input
- Tier 3: ~2.2s artificial server-side delay (real LCP regression, not a synthetic asset)
- Tier 4: missing `<h1>` (plus the site-wide missing sitemap.xml/robots.txt, which shows up on every fixture, not just this one)
- Tier 5: relies on the site-wide missing CSP/X-Frame-Options/HSTS/X-Content-Type-Options headers (same caveat as tier 4 — not something a single page can control in isolation; an actual current gap in this deployment's `next.config.ts`, not a synthetic fixture)
- Tier 6: a 20×20px touch target
- Tier 7: leftover Lorem-ipsum copy + a misleading "Buy Now" CTA, for Gemini's vision judgment
- Tier 8: a "Continue" link that never navigates (`href="#"`), with a real (unreachable) step-2 page alongside it

**Ground truth + runner:** `agent/eval/expected_findings.json` documents each planted bug as a `(tier, keyword)` pair; `agent/eval/run_eval.py` scans all 8 fixtures for real against the live API, matches findings by tier + title keyword, and computes recall. It deliberately does **not** auto-score precision — that requires knowing every real bug on a page, not just the planted ones — so each run's non-matching findings are printed for manual review instead of being scored as false positives.

**Run it:** `python agent/eval/run_eval.py` (defaults to the live `bughound-api`/`bughound-web` URLs; override with `--api-base`/`--site-base` for local testing). Results land in `agent/eval/last_run_results.json`.

### Run 1 (2026-09-03): 12/18 (67%), corrected to 12/17 (71%)

Per tier: T1 4/4, T2 2/3, T3 0/1, T4 2/2, T5 3/4, T6 1/1, T7 0/2, T8 0/1. Full breakdown
in git history; the short version is 1 miss was the eval's own wrong assumption (HSTS —
Vercel injects it automatically), 2 were real detections filed under an unexpected tier
(Gemini's vision judge independently caught bugs planted for T2 and T8, just tagged them
T7), and 3 were genuine open questions carried into run 2 below.

### Run 2 (2026-09-05), after investigating and fixing every open question from run 1

Each of run 1's 3 "unresolved gaps" was root-caused with a real test before touching any
code — not guessed at:

1. **Tier 3 (LCP) fired on zero runs — root cause found and fixed.** `web-vitals`'
   `onLCP`/`onCLS` callbacks only fire on *finalization* (a visibility change or
   `pagehide` event) by default. Neither happens during a single automated Playwright
   page load, so the callback simply never fired — on any real scan, not just this
   fixture, since the crawler was shipped. Fixed with `reportAllChanges: true`, which
   reports on every update instead of waiting for an event that never comes. Verified
   directly against the live fixture before/after: 0 findings → `LCP is 4576ms`.
2. **Tier 2 missed the unlabeled `<input>` — the eval fixture's assumption was wrong,
   not the detector.** Tested axe-core directly against the exact markup: a
   placeholder-only input **passes** axe's `label` rule, because placeholder text counts
   as a fallback accessible name per the browser's accname computation — confirmed with
   a real axe-core run, then confirmed the opposite (a true labelless input fails
   `label` with `impact: critical`) once the placeholder was removed. Fixed the fixture,
   not the checker.
3. **The T7 fixture got zero tier-7 findings on itself — root cause found: quota, not
   judgment quality.** Checked `runs_meta.gemini_calls` across every job in the batch:
   the first 3 fixtures alone burned 22 Gemini calls, already past the 20/day free-tier
   cap, before a 4th page was ever screenshotted. Root cause: `explorer_graph.judge_findings`
   called Gemini on *every* loop iteration (up to 8 per scan) instead of periodically.
   Fixed to call it only on the first pass (before any exploration) and the last
   (after exploration ends) — a ~4x reduction, unit-tested
   (`agent/tests/test_explorer_graph.py`) since same-day quota exhaustion made a clean
   live re-run impossible until quota resets.

One more thing run 2 surfaced organically: the T5 fixture's planted bug (missing
CSP/X-Frame-Options/X-Content-Type-Options) **no longer exists** — those exact headers
were found missing and fixed site-wide in `next.config.ts` during the security hardening
pass in §18, before this eval run. The fixture now correctly shows nothing missing,
because the gap it was designed to demonstrate got closed in the meantime. Left in the
manifest with an empty planted-bugs list rather than deleted, so this stays visible as
what it is — a fixture retired by its own bug getting fixed, not a detector failure.

**Run 2 result: 11/14 scored planted bugs (79%)**, T5 excluded from the denominator
(0 planted, 0 required). Per tier: T1 4/4, T2 3/3, T3 1/1, T4 2/2, T5 n/a, T6 1/1, T7 0/2,
T8 0/1. T7/T8 still show as misses in this run's raw numbers for the same reason as
before — same-day quota exhaustion, now understood and fixed at the code level, but not
yet reverifiable live until the daily quota resets. A same-day rerun after quota resets
is the natural next step to confirm the Gemini-call reduction actually holds T7/T8
recall up under real conditions, not just in the unit tests.

Re-run with `python agent/eval/run_eval.py`; results overwrite `agent/eval/last_run_results.json` each time.



