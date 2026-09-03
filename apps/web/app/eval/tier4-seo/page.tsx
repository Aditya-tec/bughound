export const metadata = { robots: { index: false, follow: false } };

export default function Tier4SeoFixture() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      {/* Deliberately no <h1> anywhere on the page -- styled div instead */}
      <div style={{ fontSize: "2rem", fontWeight: 700 }}>Tier 4 — SEO fixture</div>
      <p>This page has no real heading element and relies on the site&apos;s missing sitemap.xml/robots.txt.</p>
      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
