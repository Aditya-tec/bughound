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

      {/* No label, no aria-label, and deliberately no placeholder either -- placeholder
          text counts as a fallback accessible name per the accname spec, so axe-core
          correctly does NOT flag a placeholder-only input. Confirmed with a real
          axe-core run before removing it: this exact input passed axe's "label" rule
          with a placeholder present, and failed it once removed. */}
      <input name="unlabeled" />

      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
