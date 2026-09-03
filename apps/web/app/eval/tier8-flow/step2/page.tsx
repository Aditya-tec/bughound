export const metadata = { robots: { index: false, follow: false } };

// Real destination the step-1 "Continue" link should have pointed to, but doesn't --
// exists so the fixture is a genuine broken flow, not a missing route.
export default function Tier8FlowFixtureStep2() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1>Tier 8 — Flow fixture (step 2 of 2)</h1>
      <p>You reached step 2 directly — the step-1 Continue link never actually brings you here.</p>
    </main>
  );
}
