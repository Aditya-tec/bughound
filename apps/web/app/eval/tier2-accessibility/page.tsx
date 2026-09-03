export const metadata = { robots: { index: false, follow: false } };

export default function Tier2AccessibilityFixture() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1>Tier 2 — Accessibility fixture</h1>

      {/* Missing alt text */}
      <img src="/logo-128.png" width={64} height={64} />

      {/* Insufficient contrast: light gray on white */}
      <p style={{ color: "#e0e0e0", background: "#ffffff" }}>
        This paragraph fails WCAG contrast requirements against its background.
      </p>

      {/* Input with no associated label and no aria-label */}
      <input name="unlabeled" placeholder="No label, no aria-label" />

      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
