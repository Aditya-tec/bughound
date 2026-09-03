export const metadata = { robots: { index: false, follow: false } };

export default function Tier7VisualUxFixture() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1>Lorem Ipsum Dolor Sit Amet</h1>
      <p>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt
        ut labore et dolore magna aliqua. This is placeholder copy left on a live page by mistake.
      </p>
      <button style={{ padding: "0.8rem 1.6rem", fontWeight: 700 }}>Buy Now</button>
      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
