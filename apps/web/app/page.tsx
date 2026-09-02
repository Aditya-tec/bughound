"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createJob, type Mode } from "@/lib/api";

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
      <h1>BugHound</h1>
      <p className="muted">
        Submit a URL. BugHound explores it like a real user and finds real bugs across 8
        categories — functional, accessibility, performance, SEO, security, responsive,
        visual/UX, and multi-step flows.
      </p>

      <form onSubmit={handleSubmit} style={{ marginTop: "1.5rem" }}>
        <div className="field-row">
          <input
            type="url"
            required
            placeholder="https://example.com"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
          />
          <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
            <option value="scan">Scan (report only)</option>
            <option value="owner">Owner (auto-file issues)</option>
          </select>
          <button type="submit" disabled={submitting}>
            {submitting ? "Starting…" : "Run scan"}
          </button>
        </div>
        {error && (
          <p style={{ color: "crimson", marginTop: "0.5rem" }}>{error}</p>
        )}
      </form>

      <p className="muted" style={{ marginTop: "2rem", fontSize: "0.9rem" }}>
        Scan mode is read-only and never writes to your repo. Owner mode auto-files GitHub
        issues via a personal access token — use it only on sites you own.
      </p>
    </main>
  );
}
