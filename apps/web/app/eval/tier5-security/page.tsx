export const metadata = { robots: { index: false, follow: false } };

// No page-specific setup needed: this deployment doesn't set CSP, X-Frame-Options,
// HSTS, or X-Content-Type-Options anywhere, so tier 5's header checks fire
// identically on every page including this one. That's the real, current gap --
// see the security hardening notes for whether to fix it site-wide via next.config.
export default function Tier5SecurityFixture() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1>Tier 5 — Security fixture</h1>
      <p>This page relies on the site-wide missing security headers (CSP, X-Frame-Options, HSTS, X-Content-Type-Options).</p>
      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
