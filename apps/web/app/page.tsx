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
    <main className="hero">
      <span className="pill-chip-label">Autonomous QA agent</span>

      <h1 style={{ fontSize: "clamp(2.2rem, 5vw, 3.6rem)", maxWidth: "16ch", margin: "1.25rem auto 0" }}>
        Every product has bugs it <span className="italic-accent">doesn&apos;t</span> know about.
      </h1>
      <p className="muted" style={{ fontSize: "1.05rem", fontWeight: 300, maxWidth: "52ch", margin: "1.25rem auto 0" }}>
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

        <div style={{ display: "flex", justifyContent: "center", marginTop: "1rem" }}>
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

        <p className="faint" style={{ marginTop: "1.25rem", fontSize: "0.8rem", lineHeight: 1.6 }}>
          <strong className="muted">Scan</strong> is read-only and never writes to your repo.{" "}
          <strong className="muted">Owner</strong> auto-files GitHub issues via a personal
          access token — use it only on sites you own.
        </p>
      </form>

      <div className="chip-row">
        {Object.entries(TIERS).map(([id, tier]) => (
          <div className="chip" key={id} style={{ "--tier-color": tier.color } as React.CSSProperties}>
            <span className="chip-dot" />
            <span className="chip-title">{tier.label}</span>
            <span className="chip-desc">{tier.description}</span>
          </div>
        ))}
      </div>

      <span className="mono-label" style={{ display: "block", textAlign: "center", marginBottom: "0.5rem" }}>
        Real findings, from real scans
      </span>
      <FindingsShowcase />
    </main>
  );
}
