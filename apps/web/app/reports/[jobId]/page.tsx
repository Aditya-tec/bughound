"use client";

import { use, useEffect, useState } from "react";
import { getJobReport, type JobWithFindings } from "@/lib/api";
import FindingsList from "@/components/FindingsList";

export default function ReportPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const [data, setData] = useState<JobWithFindings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJobReport(jobId)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load report"));
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
  const bySeverity = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const f of findings) bySeverity[f.severity]++;

  return (
    <main>
      <h1>BugHound report</h1>
      <p className="muted">{job.target_url}</p>
      <p>
        <span className="badge">{bySeverity.critical} critical</span>
        <span className="badge">{bySeverity.high} high</span>
        <span className="badge">{bySeverity.medium} medium</span>
        <span className="badge">{bySeverity.low} low</span>
      </p>

      {job.mode === "scan" && (
        <p className="muted" style={{ fontSize: "0.9rem" }}>
          This was a read-only scan — nothing was written to any repository. If you own this
          site, you can{" "}
          <a href={`/connect-github?jobId=${job.id}`}>connect GitHub to file selected findings</a>{" "}
          as issues.
        </p>
      )}

      <h2>Findings ({findings.length})</h2>
      <FindingsList findings={findings} />
    </main>
  );
}
