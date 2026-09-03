"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createJob, type Mode } from "@/lib/api";
import { TIERS } from "@/lib/tiers";
import FindingsShowcase from "@/components/FindingsShowcase";

export default function HomePage() {
  const router = useRouter();
  const [targetUrl, setTargetUrl] = useState("");
  const [mode, setMode] = useState<Mode>("scan");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { job_id } = await createJob(targetUrl, mode);
      router.push(`/scan/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start scan");
      setSubmitting(false);
    }
  }

  return (
    <>
      <main className="hero" id="scan">
        <div className="atmosphere atmosphere-hero" aria-hidden="true" />

        <span className="pill-chip-label">Autonomous QA agent</span>

        <h1 style={{ fontSize: "clamp(2.4rem, 6vw, 4.6rem)", maxWidth: "17ch", margin: "1.5rem auto 0" }}>
          Every product has bugs it <span className="italic-accent">doesn&apos;t</span> know about.
        </h1>
        <p className="muted" style={{ fontSize: "1.05rem", fontWeight: 400, maxWidth: "54ch", margin: "1.5rem auto 0", lineHeight: 1.6 }}>
          Submit a URL. BugHound explores it like a real user and reports real bugs across
          8 categories — functional, accessibility, performance, SEO, security, responsive,
          visual/UX, and multi-step flows.
        </p>

        <form onSubmit={handleSubmit} className="hero-form" style={{ marginTop: "2.5rem" }}>
          <div className="ai-input-row">
            <input
              className="ai-input mono"
              type="url"
              required
              placeholder="https://example.com"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
            />
            <button type="submit" className="ai-input-submit" disabled={submitting} aria-label="Run scan">
              {submitting ? "…" : "→"}
            </button>
          </div>

          <div style={{ display: "flex", justifyContent: "center", marginTop: "1.1rem" }}>
            <div className="segmented">
              <button type="button" className={mode === "scan" ? "active" : ""} onClick={() => setMode("scan")}>
                Scan
              </button>
              <button type="button" className={mode === "owner" ? "active" : ""} onClick={() => setMode("owner")}>
                Owner
              </button>
            </div>
          </div>

          {error && (
            <p style={{ color: "var(--danger)", marginTop: "0.9rem", fontSize: "0.85rem" }}>{error}</p>
          )}

          <p className="faint" style={{ marginTop: "1.4rem", fontSize: "0.8rem", lineHeight: 1.6 }}>
            <strong className="muted">Scan</strong> is read-only and never writes to your repo.{" "}
            <strong className="muted">Owner</strong> auto-files GitHub issues via a personal
            access token — use it only on sites you own.
          </p>
        </form>
      </main>

      <section id="how-it-works">
        <div className="section-head">
          <span className="eyebrow">How it works</span>
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", marginTop: "0.9rem" }}>
            From a URL to a filed issue, in one pass.
          </h2>
        </div>

        <div className="pipeline">
          <span className="pipeline-node">🔗 Any URL</span>
          <span className="pipeline-arrow">→</span>
          <span className="pipeline-node is-hub">
            <span className="pipeline-hub-glow" aria-hidden="true" />
            🐕 BugHound agent
          </span>
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-tiers">
            {Object.entries(TIERS).map(([id, tier]) => (
              <span className="pipeline-tier-node" key={id}>
                <span className="pipeline-tier-dot" style={{ "--tier-color": tier.color } as React.CSSProperties} />
                {tier.short}
              </span>
            ))}
          </div>
          <span className="pipeline-arrow">→</span>
          <span className="pipeline-node">📋 Report or filed issues</span>
        </div>
      </section>

      <section id="findings" className="tight">
        <div className="section-head">
          <span className="eyebrow">Real findings, from real scans</span>
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", marginTop: "0.9rem" }}>
            Not mockups. Actual output.
          </h2>
        </div>
        <FindingsShowcase />
      </section>

      <section>
        <div className="section-head">
          <span className="eyebrow">Why teams run it</span>
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", marginTop: "0.9rem" }}>
            Built to actually catch what you missed.
          </h2>
        </div>

        <div className="feature-grid">
          <div className="feature-card">
            <span className="feature-icon">🧭</span>
            <h3>Explores like a user</h3>
            <p>
              Clicks, scrolls, fills forms, and follows multi-step flows the way a real visitor
              would — not just a static crawl of your sitemap.
            </p>
          </div>
          <div className="feature-card is-elevated">
            <span className="feature-icon">🎯</span>
            <h3>Eight categories, zero guesswork</h3>
            <p>
              Functional, accessibility, performance, SEO, security, responsive, visual/UX, and
              flow issues — tiered and scored automatically, no manual triage.
            </p>
          </div>
          <div className="feature-card">
            <span className="feature-icon">🔐</span>
            <h3>Scan safely, or ship fixes</h3>
            <p>
              Scan mode is read-only — run it against any site with confidence. Owner mode files
              only the findings you select, straight to GitHub issues.
            </p>
          </div>
        </div>
      </section>

      <section>
        <div className="section-head" id="faq">
          <span className="eyebrow">FAQ</span>
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", marginTop: "0.9rem" }}>
            Questions worth answering upfront.
          </h2>
        </div>

        <div className="faq">
          <details className="faq-item" open>
            <summary>
              Is a Scan safe to run on a site I don&apos;t own?
              <span className="chevron">↓</span>
            </summary>
            <p>
              Yes. Scan mode is fully read-only — BugHound crawls and interacts with the page
              to surface findings, but it never writes to your repository or files anything
              automatically.
            </p>
          </details>
          <details className="faq-item">
            <summary>
              What does Owner mode do differently?
              <span className="chevron">↓</span>
            </summary>
            <p>
              Owner mode connects a GitHub App scoped to a single repository — you pick exactly
              which one via GitHub&apos;s own install screen — so you can review findings and
              file only the ones you select, with <code className="mono">issues:write</code> on
              that repo alone.
            </p>
          </details>
          <details className="faq-item">
            <summary>
              What actually counts as a &ldquo;bug&rdquo; here?
              <span className="chevron">↓</span>
            </summary>
            <p>
              Anything across the 8 tiers above — from console errors and broken links to
              axe-core accessibility violations, Core Web Vitals regressions, missing SEO
              hygiene, header/cookie security gaps, sub-44px touch targets, vision-judged
              visual/UX problems, and multi-step flows that silently drop state.
            </p>
          </details>
          <details className="faq-item">
            <summary>
              Why is this free?
              <span className="chevron">↓</span>
            </summary>
            <p>
              The heavy compute — the actual browser automation — runs on GitHub Actions, which
              is free for public repos. That&apos;s an architectural choice, not a trial: nothing
              in the stack asks for payment details.
            </p>
          </details>
        </div>
      </section>

      <section>
        <div className="cta-band">
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.4rem)" }}>Point it at your site.</h2>
          <p>Takes one URL and a few minutes. Read-only by default — nothing to lose.</p>
          <div className="cta-actions">
            <a href="#scan">
              <button className="btn-primary">Run a scan →</button>
            </a>
            <a href="https://github.com/Aditya-tec/bughound" target="_blank" rel="noreferrer">
              <button className="ghost-btn">View source ↗</button>
            </a>
          </div>
        </div>
      </section>

      <footer>
        <span>BugHound — autonomous QA agent</span>
        <span>Built in the open on GitHub Actions, Supabase, Groq &amp; Gemini</span>
      </footer>
    </>
  );
}
