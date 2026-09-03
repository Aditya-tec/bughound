"use client";

import { use, useEffect, useState } from "react";
import { getJob, type JobWithFindings } from "@/lib/api";
import FindingsList from "@/components/FindingsList";

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

  return (
    <main>
      <div className="eyebrow">{live ? "Scan in progress" : "Scan finished"}</div>
      <h1 className="mono" style={{ fontSize: "1.6rem", wordBreak: "break-all" }}>{job.target_url}</h1>

      <div style={{ marginTop: "0.9rem" }}>
        <span className="badge badge-status" data-status={job.status}>
          {live && <span className="pulse" />}
          {job.status}
        </span>
        <span className="badge">{job.pages_crawled} pages crawled</span>
        <span className="badge">{job.actions_taken} actions taken</span>
      </div>

      {job.status === "completed" && (
        <p className="muted" style={{ marginTop: "0.9rem" }}>
          Done — <a href={`/reports/${job.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>view the shareable report ↗</a>
        </p>
      )}
      {job.status === "failed" && (
        <p style={{ color: "var(--danger)", marginTop: "0.9rem" }}>
          This run failed. Partial findings below (if any) are still real.
        </p>
      )}

      <hr className="divider" />

      <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Findings ({findings.length})</h2>
      <FindingsList findings={findings} />
    </main>
  );
}
