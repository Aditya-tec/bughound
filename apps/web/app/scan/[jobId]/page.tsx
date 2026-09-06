"use client";

import { use, useEffect, useState } from "react";
import { getJob, type JobWithFindings } from "@/lib/api";
import FindingsList from "@/components/FindingsList";
import { TIERS } from "@/lib/tiers";

const POLL_INTERVAL_MS = 3000;

export default function ScanPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const [data, setData] = useState<JobWithFindings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const result = await getJob(jobId);
        if (cancelled) return;
        setData(result);
        if (result.job.status === "queued" || result.job.status === "running") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load job");
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId]);

  if (error) {
    return (
      <main>
        <p style={{ color: "var(--danger)" }}>{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main>
        <div className="skeleton" style={{ height: 140, marginBottom: "1rem" }} />
        <div className="skeleton" style={{ height: 90 }} />
      </main>
    );
  }

  const { job, findings } = data;
  const live = job.status === "queued" || job.status === "running";
  const completed = job.status === "completed";
  const progress = completed ? 100 : job.status === "failed" ? 100 : Math.min(94, Math.max(8, 12 + job.pages_crawled * 11 + job.actions_taken * 4 + findings.length * 3));
  const activeTier = Object.values(TIERS)[Math.min(7, Math.max(0, findings.length % 8))];
  const traceLines = live
    ? [
        job.pages_crawled > 0 ? `indexed ${job.pages_crawled} page${job.pages_crawled === 1 ? "" : "s"}` : "opening target and checking response",
        job.actions_taken > 0 ? `replayed ${job.actions_taken} browser action${job.actions_taken === 1 ? "" : "s"}` : "mapping links, forms, and interactive controls",
        findings.length > 0 ? `queued ${findings.length} finding${findings.length === 1 ? "" : "s"} for verification` : `running ${activeTier.label.toLowerCase()} checks`,
      ]
    : [
        `completed ${job.pages_crawled} page${job.pages_crawled === 1 ? "" : "s"} across the target`,
        `recorded ${job.actions_taken} browser action${job.actions_taken === 1 ? "" : "s"} without writing to the site`,
        completed ? `verified ${findings.length} finding${findings.length === 1 ? "" : "s"} and prepared the report` : "preserved partial results from the interrupted run",
      ];

  return (
    <main>
      <div className="scan-heading">
        <div>
          <div className="eyebrow"><span className={live ? "live-dot" : "status-dot"} />{live ? "Scan in progress" : "Scan finished"}</div>
          <h1 className="mono" style={{ fontSize: "1.6rem", wordBreak: "break-all" }}>{job.target_url}</h1>
        </div>
        <div className="scan-index mono">RUN / {job.id.slice(0, 8)}</div>
      </div>

      <div style={{ marginTop: "0.9rem" }}>
        <span className="badge badge-status" data-status={job.status}>
          {live && <span className="pulse" />}
          {job.status}
        </span>
        <span className="badge">{job.pages_crawled} pages crawled</span>
        <span className="badge">{job.actions_taken} actions taken</span>
      </div>

      <section className="scan-progress" aria-label="Scan progress">
        <div className="progress-head">
          <span className="mono-label">Agent pipeline</span>
          <span className="mono progress-value">{progress}%</span>
        </div>
        <div className="progress-track"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>
        <div className="pipeline-steps">
          <span className={job.pages_crawled > 0 || completed ? "is-done" : "is-active"}>01 crawl</span>
          <span className={job.actions_taken > 0 || completed ? "is-done" : live ? "is-active" : ""}>02 interact</span>
          <span className={findings.length > 0 || completed ? "is-done" : live ? "is-active" : ""}>03 inspect</span>
          <span className={completed ? "is-done" : ""}>04 report</span>
        </div>
      </section>

      <section className="agent-console" aria-label="Live agent trace">
        <div className="console-topline"><span><span className="console-signal" />agent trace</span><span className="faint">{live ? "polling every 3s" : "run archived"}</span></div>
        <div className="console-lines">
          {traceLines.map((line, index) => (
            <div className="console-line" key={line} style={{ animationDelay: `${index * 120}ms` }}>
              <span className="console-arrow">{index === traceLines.length - 1 && live ? "▸" : "✓"}</span><span>{line}</span>
            </div>
          ))}
        </div>
        <div className="console-note">read-only mode · the agent can inspect, click, scroll, and submit safely without changing the target</div>
      </section>

      {job.status === "completed" && (
        <div className="scan-actions">
          <a href={`/reports/${job.id}`} className="btn btn-primary">Open shareable report ↗</a>
          <a href={`/connect-github?jobId=${job.id}`} className="btn">Connect GitHub to raise issues</a>
        </div>
      )}
      {job.status === "failed" && (
        <p style={{ color: "var(--danger)", marginTop: "0.9rem" }}>
          This run failed. Partial findings below (if any) are still real.
        </p>
      )}

      <hr className="divider" />

      <div className="findings-heading">
        <div>
          <div className="eyebrow">Evidence log</div>
          <h2 style={{ fontSize: "1.35rem" }}>Findings ({findings.length})</h2>
        </div>
        <span className="muted findings-help">Each card includes the check that surfaced it.</span>
      </div>
      <FindingsList findings={findings} />

      {!live && (
        <section className="next-step-panel">
          <div>
            <div className="eyebrow">What happens next</div>
            <h2>From evidence to action.</h2>
            <p className="muted">Share the report with your team, or connect a GitHub repository you own. BugHound will turn selected findings into clear issues with context and reproduction steps.</p>
          </div>
          <a href={`/connect-github?jobId=${job.id}`} className="ghost-btn">Review GitHub handoff ↗</a>
        </section>
      )}
    </main>
  );
}
