import type { Finding } from "@/lib/api";
import { tierMeta } from "@/lib/tiers";

export default function FindingsList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return (
      <div className="panel" style={{ textAlign: "center", padding: "2.5rem 1.5rem" }}>
        <p className="muted" style={{ margin: 0 }}>No findings yet.</p>
      </div>
    );
  }

  return (
    <div>
      {findings.map((finding, i) => {
        const tier = tierMeta(finding.tier);
        return (
          <div
            className="card"
            key={finding.id}
            style={{ "--tier-color": tier.color, animationDelay: `${Math.min(i, 12) * 30}ms` } as React.CSSProperties}
          >
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.3rem", marginBottom: "0.6rem" }}>
              <span className="badge" data-tier={finding.tier} style={{ "--tier-color": tier.color } as React.CSSProperties}>
                {tier.label}
              </span>
              <span className="badge" data-severity={finding.severity}>{finding.severity}</span>
              {finding.filed_as_issue && finding.issue_url && (
                <a className="badge" href={finding.issue_url} target="_blank" rel="noreferrer">
                  issue filed ↗
                </a>
              )}
            </div>
            <h3 style={{ fontSize: "1rem", marginBottom: "0.3rem" }}>{finding.title}</h3>
            <p className="mono faint" style={{ margin: "0 0 0.5rem", fontSize: "0.8rem", wordBreak: "break-all" }}>
              {finding.page_url}
            </p>
            {finding.description && (
              <p style={{ margin: "0 0 0.4rem", fontSize: "0.9rem" }}>{finding.description}</p>
            )}
            {finding.repro_steps && (
              <p className="muted" style={{ fontSize: "0.82rem", margin: 0 }}>
                {finding.repro_steps}
              </p>
            )}
            <details className="finding-details">
              <summary>How BugHound got here <span>+</span></summary>
              <div className="finding-method">
                <div><span className="mono-label">Agent check</span><strong>{tier.label}</strong><p>{tier.description}</p></div>
                <div><span className="mono-label">Evidence</span><strong>{finding.page_url}</strong><p>{finding.repro_steps ?? "The agent captured this result while exploring the page and comparing it with the check's expected behavior."}</p></div>
              </div>
            </details>
          </div>
        );
      })}
    </div>
  );
}
