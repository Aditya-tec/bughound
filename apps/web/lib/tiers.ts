export interface TierMeta {
  label: string;
  short: string;
  color: string;
  description: string;
}

export const TIERS: Record<number, TierMeta> = {
  1: { label: "Functional", short: "FN", color: "var(--tier-1)", description: "Console errors, broken links, failed requests" },
  2: { label: "Accessibility", short: "A11Y", color: "var(--tier-2)", description: "axe-core violations" },
  3: { label: "Performance", short: "PERF", color: "var(--tier-3)", description: "Core Web Vitals, slow responses" },
  4: { label: "SEO", short: "SEO", color: "var(--tier-4)", description: "Meta hygiene" },
  5: { label: "Security", short: "SEC", color: "var(--tier-5)", description: "Header + cookie hygiene" },
  6: { label: "Responsive", short: "RESP", color: "var(--tier-6)", description: "Viewport + touch targets" },
  7: { label: "Visual/UX", short: "UX", color: "var(--tier-7)", description: "Gemini vision judgment" },
  8: { label: "Flow", short: "FLOW", color: "var(--tier-8)", description: "Multi-step consistency" },
};

export function tierMeta(tier: number): TierMeta {
  return TIERS[tier] ?? { label: `Tier ${tier}`, short: `T${tier}`, color: "var(--accent)", description: "" };
}

export const SEVERITIES = ["critical", "high", "medium", "low"] as const;
