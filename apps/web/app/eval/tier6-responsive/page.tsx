export const metadata = { robots: { index: false, follow: false } };

export default function Tier6ResponsiveFixture() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1>Tier 6 — Responsive fixture</h1>
      <p>The button below is a 20&times;20px touch target, well under the 44px minimum.</p>
      <button style={{ width: 20, height: 20, padding: 0, fontSize: "0.6rem" }}>+</button>
      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
