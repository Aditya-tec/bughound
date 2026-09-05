# BugHound

An autonomous agent that explores a live website the way a real user would — clicking,
scrolling, filling forms — and reports real bugs across 8 categories: functional,
accessibility, performance, SEO, security hygiene, responsive design, visual/UX, and
multi-step flow consistency. On sites you own, it auto-files GitHub issues. On anyone
else's, it produces a read-only, shareable report and never touches their repo.

**Live:** [bughound-web.vercel.app](https://bughound-web.vercel.app) · **Full build spec:** [bughound-master-build-spec.md](bughound-master-build-spec.md)

## Found and fixed a critical RLS gap that let the public anon key bypass every server-side check

This is the finding worth reading first. The frontend ships a public Supabase anon key —
by design, Supabase expects that key to be public, protected entirely by Row Level
Security policies on the tables it can touch. RLS was never enabled on this project's
tables. That's not a theoretical gap: it was verified exploitable before it was fixed,
not just inferred from a checklist.

Using nothing but the anon key already sitting in the shipped client bundle, I inserted a
real row into `jobs` and updated a real row in `findings` directly via Supabase's
PostgREST API — no auth, no API call, completely bypassing the SSRF guard, the
owner-mode domain allowlist, and the rate limiter, because none of those checks live in
the database, only in the FastAPI layer in front of it. Every other security control in
this project was moot for anyone willing to open dev tools and talk to Supabase directly.

Fixed by enabling RLS with zero policies (default-deny for `anon`/`authenticated`) across
all four tables, verified safe because the frontend never talks to Supabase directly —
every real read/write already goes through the API's service-role key, which always
bypasses RLS by design. Reverified after the fix with the identical attack: the same
insert now returns `42501: new row violates row-level security policy` and the same
update is a confirmed no-op. Full writeup, including the exact requests, in
[bughound-master-build-spec.md](bughound-master-build-spec.md) §18.

This exact bug — a public anon key with RLS off — ships in a large number of real
production Supabase apps. It's the kind of gap that's invisible until someone actually
tries the anon key against the tables instead of trusting that "the API handles it."

## Why this exists

Momentic and Octomind sell versions of this. This is the open-source, self-hostable,
$0-forever version — no card required anywhere in the stack, because the expensive part
(headless browser automation) runs on GitHub Actions' free compute for public repos, not
on a paid always-on server. Vercel's serverless functions only orchestrate: create a job
row, fire a dispatch event, read Supabase, call the GitHub API. LLM reasoning is split
across two free tiers by workload — Groq for the frequent, cheap text-reasoning calls
(page planning, flow-consistency judgment), Gemini only for the handful of calls per run
that actually need vision (screenshot judgment).

## The three modes

| Mode | Who it's for | What happens |
|---|---|---|
| **Scan** | Anyone, on any URL | Fully read-only. Crawls and interacts with the page, produces a shareable report. Nothing is ever written anywhere. |
| **Owner** | The operator, on their own domains | Auto-files every finding as a GitHub issue — no selection step. Locked server-side to an operator-configured domain allowlist; rejected outright for anything else. |
| **Connect GitHub** (Mode B+) | A scan-mode report viewer who owns that site | Installs a narrowly-scoped GitHub App (`issues: write` only) on **their own** repo — they pick which one via GitHub's own install screen — then selectively files the findings they choose. BugHound never holds a credential to their account; GitHub's own consent screen is the trust boundary, not something built in-house. |

## The 8 tiers

1. **Functional** — uncaught JS exceptions, failed requests, broken links/images, forms that submit with empty required fields and no validation
2. **Accessibility** — axe-core: missing alt text, insufficient contrast, unlabeled inputs, ARIA issues
3. **Performance** — Core Web Vitals (LCP/CLS) via the `web-vitals` library, slow API responses
4. **SEO** — missing/duplicate title & H1, missing canonical, broken Open Graph, missing sitemap.xml/robots.txt
5. **Security hygiene** — passive only: missing CSP/X-Frame-Options/HSTS/X-Content-Type-Options, cookie flags, mixed content
6. **Responsive** — missing viewport meta, horizontal overflow, sub-44px touch targets at 3 breakpoints
7. **Visual/UX** — Gemini vision judgment: layout breakage, leftover placeholder content, misleading CTAs, dead-end navigation
8. **Flow consistency** — LangGraph-tracked multi-step state across pages: broken checkout/signup flows, back-button state loss

Tiers 1–6 are deterministic (free libraries, no LLM). Tier 7 uses Gemini vision. Tier 8
uses Groq text reasoning over recorded page states — no screenshots.

## Does it actually work? Proof, not claims

- **Real issues, filed automatically**: a single owner-mode run against a live site
  auto-filed 9 real GitHub issues on this repo with zero manual triage —
  [issue #1](https://github.com/Aditya-tec/bughound/issues/1),
  [#2](https://github.com/Aditya-tec/bughound/issues/2),
  [#5](https://github.com/Aditya-tec/bughound/issues/5),
  [#8](https://github.com/Aditya-tec/bughound/issues/8), and 5 more. They're live; click
  through.
- **Real findings on a real, unrelated project**: a scan-mode run against a second live
  deployment (not a fixture, not this repo) surfaced 25 genuine findings across 5 tiers
  in one pass — accessibility violations, missing SEO/security headers, sub-44px touch
  targets, real vision-judged UX issues.
- **A crawler crash, found by dogfooding against a third real project**: a scan against
  another live deployment crashed the entire job — `Page.goto: Timeout 30000ms
  exceeded` — because that site never satisfies Playwright's `networkidle` wait
  condition (continuous polling/analytics keep the network busy indefinitely). Root
  caused, fixed, and locked in with a regression test the same day it was found.
- **An eval suite, not a vibe check**: `apps/web/app/eval/` hosts 8 deliberately-broken
  fixture pages, one per tier, each with documented planted bugs
  (`agent/eval/expected_findings.json`). `agent/eval/run_eval.py` scans all 8 for real
  against the live deployment and scores recall against that ground truth — not a demo
  video, an actual repeatable measurement. Latest run: see
  [`agent/eval/last_run_results.json`](agent/eval/last_run_results.json) and §19 of the
  build spec for the full breakdown, including the misses and which ones turned out to
  be the eval's own bugs rather than the detector's.
- **A real security pass beyond RLS**: an SSRF guard checked independently at job
  creation and again right before the crawler connects, an owner-mode domain allowlist,
  per-IP rate limiting on the public API with idempotent issue-filing, and a cross-job
  data leak closed in the file-issues endpoint. Full writeup in §18 of the build spec.
- **Went looking for CSRF protection on the GitHub App install flow, found the feature
  was silently broken instead.** The install link set `?state=${jobId}`; GitHub echoes
  that back as `state` on the callback redirect — but the callback handler's signature
  expected a param literally named `job_id`, which GitHub never sends. Every real
  installation would have linked to `null`, forever. Fixed the actual bug and added the
  CSRF protection it needed anyway (a signed, 15-minute state token) in the same change
  — verifying against actual behavior instead of just applying a described fix is what
  surfaced this.
- **Redirect-based SSRF, and the agent's own prompt-injection surface, closed
  structurally, not by validating output.** Playwright follows HTTP redirects
  transparently, so the entry-URL SSRF checks never saw a malicious mid-crawl 302 to an
  internal IP — fixed with a route guard that re-validates every navigation hop, not
  just the first. Separately, the explore loop used to hand the model a free-form
  selector string to act on, built from page content it doesn't control — a page could
  embed instructions-shaped text a human would never see but the model's context window
  would. The fix isn't a smarter prompt: the model now picks only from a closed,
  numbered index the agent's own code enumerated that same iteration, and any
  index outside that set is ignored before it ever reaches `page.locator()`. Validating
  the model's *choice* against a server-side allowlist, rather than trusting its
  *output*, is the same shape as the SSRF fix — don't ask an untrusted actor to behave,
  constrain what it's structurally able to do.

## Architecture

```
Next.js dashboard (Vercel)
   │ user submits target_url + picks mode
   ▼
FastAPI functions (Vercel, same free tier)
   │ validates (SSRF, owner-mode allowlist, rate limit) → inserts a `jobs` row →
   │ fires repository_dispatch
   ▼
GitHub Actions runner (free compute for public repos)
   │ Playwright + LangGraph agent, Groq for text reasoning, Gemini for vision
   │ crawls the target, runs all 8 tiers, records findings immediately (not batched,
   │ so a timeout still leaves partial results)
   ▼
   ├─→ Supabase (jobs/findings/screenshots — dashboard polls this live)
   └─→ mode=owner  → GitHub REST API (operator's PAT)         → issues filed automatically
       mode=scan   → nothing filed, report renders from Supabase
       Connect GitHub → GitHub App installation token, issues:write only → user-selected findings filed
```

Two Vercel projects, not one — `bughound-web` (Next.js) and `bughound-api` (FastAPI,
Python serverless) — because combining a Next.js frontend and a Python API in a single
Vercel project runs into framework-detection conflicts; splitting them is the documented
fallback and turned out simpler in practice.

## Repo layout

```
apps/web/       Next.js frontend (Vercel) — dashboard, live scan view, public reports,
                 Connect GitHub flow, and apps/web/app/eval/ (the 8 eval fixtures)
api/            FastAPI serverless functions (Vercel) — job orchestration, GitHub App
                 auth, issue filing. Never runs an LLM call.
agent/          Playwright + LangGraph agent — runs ONLY inside GitHub Actions.
                 agent/checks/tier{1-8}_*.py, agent/eval/ (the eval runner)
supabase/       schema.sql + migrations/ (run once each via the Supabase SQL Editor —
                 no direct Postgres credentials are held anywhere in this stack, only
                 the REST API, so DDL can't be scripted)
.github/workflows/run_scan.yml   Triggered by repository_dispatch, never on a schedule
```

## Honest comparison

|  | Momentic / Octomind | BugHound |
|---|---|---|
| Cost | Paid, credit card required | $0, no card anywhere in the stack |
| Compute | Their infrastructure | GitHub Actions (free for public repos) |
| Self-hostable | No | Yes — it's this repo |
| Issue filing | Built-in integrations | Scoped GitHub App (Mode B+) or your own PAT (owner mode), never broader access than `issues: write` |
| Novelty pitch | — | None claimed. This is "the open-source, $0 version of what they charge for," not a new idea. |

## Tech stack

| Layer | Tool |
|---|---|
| Frontend | Next.js on Vercel |
| Backend API | FastAPI as Python serverless functions on Vercel |
| Heavy compute | GitHub Actions (Playwright, LangGraph) |
| Text reasoning | Groq |
| Vision | Google Gemini |
| Accessibility | axe-core via CDN injection + `page.evaluate` |
| DB + storage | Supabase (Postgres + Storage), RLS-locked |
| Issue filing | GitHub REST API — PAT (owner mode) or GitHub App installation token (Mode B+) |

## Local dev

**API:**
```
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r api/requirements.txt uvicorn
cp api/.env.example api/.env    # fill in SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
cd api && uvicorn index:app --reload
```

**Agent** (needs Supabase/Groq/Gemini credentials):
```
python -m venv .venv-agent
source .venv-agent/Scripts/activate
pip install -r agent/requirements.txt
playwright install --with-deps chromium
cd agent && python main.py --job-id <uuid> --target-url https://example.com --mode scan
```

**Frontend:**
```
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

**Eval suite** (scans the live deployment for real, no local server needed):
```
python agent/eval/run_eval.py
```

## Deliberately accepted, not overlooked

`npm audit` flags 2 vulnerabilities (1 high) in `postcss`, pulled in transitively by
Next.js — both are about processing attacker-controlled CSS content or
`sourceMappingURL` comments. Checked before deciding to defer: `npm ls postcss` shows
it's used only inside Next's own internal build pipeline, there's no `postcss.config.js`
and no direct usage anywhere in this app's code, and it only ever processes this
project's own static `globals.css` at build time — never user-supplied CSS or an
attacker-controlled source-map path at runtime. Not reachable in this app's actual usage.
The fix requires a Next 16 major-version upgrade, which is a bigger, less-understood risk
to take on this late in the build than a confirmed-unreachable transitive advisory.

## What's not finished yet

Tracked honestly in the build spec rather than glossed over here:
- Tiers 7/8's remaining eval misses are root-caused (Gemini's daily quota was being
  exhausted by the 3rd fixture in an 8-fixture batch — fixed at the code level by
  calling Gemini only on the first/last exploration pass instead of every iteration)
  but not yet reverified with a clean live re-run, since fixing it used up the same
  day's quota. §19 has the full story.
- No technical writeup video (Loom) yet
- CI now runs on every push (`.github/workflows/ci.yml`) but coverage is limited to the
  pure-logic modules (SSRF guard, owner-mode allowlist, action budget, domain
  allowlist, Gemini-call gating) — nothing exercises the FastAPI routes or the agent's
  Playwright-driven checks themselves yet, since those need real browser/DB
  infrastructure rather than unit-level mocks.

See [bughound-master-build-spec.md](bughound-master-build-spec.md) §16 for the full,
currently-accurate validation checklist.
