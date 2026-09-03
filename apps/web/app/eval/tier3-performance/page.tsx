export const metadata = { robots: { index: false, follow: false } };
// Force dynamic rendering -- otherwise Next.js statically pre-renders this at
// build time and the delay below only ever happens once, not on real requests.
export const dynamic = "force-dynamic";

// Deliberate server-side delay before the response is sent at all, so the
// largest content element can't paint before ~2.2s -- a real, reproducible
// LCP regression rather than a synthetic "big image" that depends on cache
// behavior to be reliably slow.
async function artificialDelay() {
  await new Promise((resolve) => setTimeout(resolve, 2200));
}

export default async function Tier3PerformanceFixture() {
  await artificialDelay();

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1>Tier 3 — Performance fixture</h1>
      <p>
        This page&apos;s response is deliberately delayed ~2.2s server-side before any content
        is sent, pushing LCP well past the ~1500ms threshold.
      </p>
      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
