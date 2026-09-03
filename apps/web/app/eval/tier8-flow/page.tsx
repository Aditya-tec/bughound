export const metadata = { robots: { index: false, follow: false } };

export default function Tier8FlowFixtureStep1() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1>Tier 8 — Flow fixture (step 1 of 2)</h1>
      <p>Clicking Continue should advance to step 2, but the link is dead (href=&quot;#&quot;) and never navigates.</p>
      {/* Deliberately broken: looks like real flow navigation, does nothing */}
      <a href="#" style={{ display: "inline-block", padding: "0.8rem 1.6rem", background: "#222", color: "#fff" }}>
        Continue →
      </a>
      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
