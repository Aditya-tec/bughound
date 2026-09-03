import { tierMeta } from "@/lib/tiers";

// Real findings BugHound has actually produced against example.com and its own
// deliberately-broken test fixture during development -- not fabricated copy.
const SHOWCASE = [
  { tier: 1, title: "Uncaught JS exception", source: "fixtures/broken-test-site" },
  { tier: 2, title: "color-contrast: elements must meet minimum contrast ratio", source: "example.com" },
  { tier: 4, title: "Missing or broken sitemap.xml", source: "example.com" },
  { tier: 6, title: "Touch targets under 44px at mobile width", source: "example.com" },
  { tier: 7, title: "Leftover placeholder content on a live page", source: "example.com — caught by vision review" },
];

export default function FindingsShowcase() {
  const n = SHOWCASE.length;
  return (
    <div className="fan">
      {SHOWCASE.map((item, i) => {
        const tier = tierMeta(item.tier);
        const centered = i - (n - 1) / 2;
        return (
          <div
            className="fan-card"
            key={item.tier}
            style={
              {
                "--tier-color": tier.color,
                "--rot": `${centered * 4.5}deg`,
                "--lift": `${Math.abs(centered) * 14}px`,
                zIndex: i,
              } as React.CSSProperties
            }
          >
            <span className="badge" data-tier={item.tier} style={{ "--tier-color": tier.color } as React.CSSProperties}>
              {tier.label}
            </span>
            <p className="fan-quote">&ldquo;{item.title}&rdquo;</p>
            <p className="faint" style={{ fontSize: "0.75rem", margin: 0 }}>&mdash; {item.source}</p>
          </div>
        );
      })}
    </div>
  );
}
