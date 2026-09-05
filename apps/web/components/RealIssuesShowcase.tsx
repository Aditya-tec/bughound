import { tierMeta } from "@/lib/tiers";

// Real GitHub issues, auto-filed by an actual owner-mode run against
// adityakalambe.xyz on 2026-09-04 -- not staged, not mocked. Verified live at
// github.com/Aditya-tec/bughound/issues before writing this list.
const REAL_ISSUES = [
  { number: 1, tier: 1, title: "Broken link: linkedin.com/posts/... returned 404" },
  { number: 2, tier: 4, title: "Missing canonical tag" },
  { number: 5, tier: 5, title: "Missing Content-Security-Policy header" },
  { number: 8, tier: 6, title: "26 touch target(s) under 44px at mobile width" },
];

export default function RealIssuesShowcase() {
  return (
    <div className="fan">
      {REAL_ISSUES.map((issue) => {
        const tier = tierMeta(issue.tier);
        return (
          <a
            key={issue.number}
            className="fan-card"
            href={`https://github.com/Aditya-tec/bughound/issues/${issue.number}`}
            target="_blank"
            rel="noreferrer"
            style={{ "--tier-color": tier.color, textDecoration: "none" } as React.CSSProperties}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="fan-dot" />
              <span className="mono-label">{tier.label}</span>
            </div>
            <p className="fan-quote">&ldquo;{issue.title}&rdquo;</p>
            <span className="faint mono" style={{ fontSize: "0.75rem" }}>
              Issue #{issue.number} · filed automatically ↗
            </span>
          </a>
        );
      })}
    </div>
  );
}
