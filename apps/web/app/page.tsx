"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createJob, type Mode } from "@/lib/api";
import { TIERS } from "@/lib/tiers";

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
    <main>
      <div className="eyebrow">Autonomous QA agent</div>
      <h1 style={{ fontSize: "clamp(2.4rem, 5vw, 3.4rem)", maxWidth: "14ch" }}>
        Ship less <span className="gradient-text">unseen</span> breakage.
      </h1>
      <p className="muted" style={{ fontSize: "1.05rem", maxWidth: "58ch", marginTop: "1rem" }}>
        Submit a URL. BugHound explores it like a real user and reports real bugs across
        8 categories — functional, accessibility, performance, SEO, security, responsive,
        visual/UX, and multi-step flows.
      </p>

      <div className="chip-row">
        {Object.entries(TIERS).map(([id, tier]) => (
          <span className="chip" key={id} style={{ "--tier-color": tier.color } as React.CSSProperties}>
            <span className="dot" />
            {tier.label}
          </span>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="panel">
        <label className="faint" style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
          Target URL
        </label>
        <div className="field-row" style={{ marginTop: "0.6rem" }}>
          <input
            className="input mono"
            type="url"
            required
            placeholder="https://example.com"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
          />
          <div className="segmented">
            <button
              type="button"
              className={mode === "scan" ? "active" : ""}
              onClick={() => setMode("scan")}
            >
              Scan
            </button>
            <button
              type="button"
              className={mode === "owner" ? "active" : ""}
              onClick={() => setMode("owner")}
            >
              Owner
            </button>
          </div>
        </div>

        <button type="submit" className="btn-primary btn-full" disabled={submitting} style={{ marginTop: "1rem" }}>
          {submitting ? "Starting scan…" : "Run scan →"}
        </button>

        {error && (
          <p style={{ color: "var(--danger)", marginTop: "0.75rem", fontSize: "0.85rem" }}>{error}</p>
        )}

        <p className="faint" style={{ marginTop: "1rem", fontSize: "0.8rem", lineHeight: 1.6 }}>
          <strong className="muted">Scan</strong> is read-only and never writes to your repo.{" "}
          <strong className="muted">Owner</strong> auto-files GitHub issues via a personal
          access token — use it only on sites you own.
        </p>
      </form>
    </main>
  );
}
