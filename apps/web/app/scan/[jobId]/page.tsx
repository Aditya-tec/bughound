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
        <p style={{ color: "crimson" }}>{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main>
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const { job, findings } = data;

  return (
    <main>
      <h1>Scanning {job.target_url}</h1>
      <p>
        <span className="badge">{job.status}</span>
        <span className="badge">{job.pages_crawled} pages crawled</span>
        <span className="badge">{job.actions_taken} actions taken</span>
      </p>
      {job.status === "completed" && (
        <p className="muted">
          Done. <a href={`/reports/${job.id}`}>View the shareable report</a>.
        </p>
      )}
      <h2>Findings ({findings.length})</h2>
      <FindingsList findings={findings} />
    </main>
  );
}
