"use client";

import { use, useEffect, useState } from "react";
import { getJobReport, type JobWithFindings } from "@/lib/api";
import FindingsList from "@/components/FindingsList";
import { TIERS, SEVERITIES } from "@/lib/tiers";

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
        <p style={{ color: "var(--danger)" }}>{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main>
        <div className="skeleton" style={{ height: 200 }} />
      </main>
    );
  }

  const { job, findings } = data;

  const bySeverity = { critical: 0, high: 0, medium: 0, low: 0 };
  const byTier: Record<number, number> = {};
  for (const f of findings) {
    bySeverity[f.severity]++;
    byTier[f.tier] = (byTier[f.tier] ?? 0) + 1;
  }
  const maxTierCount = Math.max(1, ...Object.values(byTier));

  return (
    <main>
      <div className="eyebrow">Scan report</div>
      <h1 style={{ fontSize: "1.9rem" }}>BugHound report</h1>
      <p className="mono muted" style={{ marginTop: "0.4rem", wordBreak: "break-all" }}>{job.target_url}</p>

      <div className="stat-grid">
        {SEVERITIES.map((sev) => (
          <div className="stat-card" key={sev}>
            <div className="stat-value" style={{ color: `var(--severity-${sev})` }}>{bySeverity[sev]}</div>
            <div className="stat-label">{sev}</div>
          </div>
        ))}
      </div>

      {findings.length > 0 && (
        <div className="tier-bars">
          {Object.entries(TIERS)
            .filter(([id]) => byTier[Number(id)])
            .map(([id, tier]) => {
              const count = byTier[Number(id)] ?? 0;
              return (
                <div className="tier-bar-row" key={id}>
                  <span className="muted" style={{ fontWeight: 600 }}>{tier.label}</span>
                  <div className="tier-bar-track">
                    <div
                      className="tier-bar-fill"
                      style={{ "--tier-color": tier.color, width: `${(count / maxTierCount) * 100}%` } as React.CSSProperties}
                    />
                  </div>
                  <span className="faint">{count}</span>
                </div>
              );
            })}
        </div>
      )}

      {job.mode === "scan" && (
        <div className="panel" style={{ marginBottom: "2rem" }}>
          <p className="muted" style={{ margin: "0 0 0.8rem", fontSize: "0.9rem" }}>
            This was a read-only scan — nothing was written to any repository.
          </p>
          <a href={`/connect-github?jobId=${job.id}`}>
            <button className="btn-primary" type="button">Connect GitHub</button>
          </a>
        </div>
      )}

      {job.mode === "owner" && (
        <div className="panel owner-github-panel" style={{ marginBottom: "2rem" }}>
          <div>
            <div className="eyebrow"><span className="status-dot" /> GitHub connected · Owner mode</div>
            <h2 style={{ fontSize: "1.25rem", marginTop: "0.35rem" }}>Issues are filed automatically.</h2>
            <p className="muted" style={{ margin: "0.55rem 0 0", fontSize: "0.88rem" }}>
              This run uses the configured owner repository. Findings are sent to GitHub as the agent verifies them, with duplicate filing protection.
            </p>
          </div>
          <a href={`/connect-github?jobId=${job.id}`} className="btn">View GitHub connection ↗</a>
        </div>
      )}

      <hr className="divider" />

      <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Findings ({findings.length})</h2>
      <FindingsList findings={findings} />
    </main>
  );
}
