import type { Finding } from "@/lib/api";

const TIER_LABELS: Record<number, string> = {
  1: "Functional",
  2: "Accessibility",
  3: "Performance",
  4: "SEO",
  5: "Security",
  6: "Responsive",
  7: "Visual/UX",
  8: "Flow",
};

export default function FindingsList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return <p className="muted">No findings yet.</p>;
  }

  return (
    <div>
      {findings.map((finding) => (
        <div className="card" key={finding.id}>
          <span className="badge">{TIER_LABELS[finding.tier] ?? `Tier ${finding.tier}`}</span>
          <span className="badge">{finding.severity}</span>
          {finding.filed_as_issue && finding.issue_url && (
            <a className="badge" href={finding.issue_url} target="_blank" rel="noreferrer">
              issue filed
            </a>
          )}
          <h3 style={{ margin: "0.5rem 0" }}>{finding.title}</h3>
          <p className="muted" style={{ margin: 0 }}>
            {finding.page_url}
          </p>
          {finding.description && <p>{finding.description}</p>}
          {finding.repro_steps && (
            <p className="muted" style={{ fontSize: "0.85rem" }}>
              {finding.repro_steps}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
