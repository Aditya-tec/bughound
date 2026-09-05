"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fileIssues, getGithubInstallState, getJobReport, type Finding } from "@/lib/api";
import FindingsList from "@/components/FindingsList";
import { tierMeta } from "@/lib/tiers";

const GITHUB_APP_SLUG = process.env.NEXT_PUBLIC_GITHUB_APP_SLUG ?? "";

export default function ConnectGithubPage() {
  return (
    <Suspense fallback={null}>
      <ConnectGithubInner />
    </Suspense>
  );
}

function ConnectGithubInner() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId") ?? "";
  const connected = searchParams.get("connected") === "true";

  const [findings, setFindings] = useState<Finding[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [filing, setFiling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [installState, setInstallState] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    getJobReport(jobId)
      .then((data) => setFindings(data.findings))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load findings"));
  }, [jobId]);

  useEffect(() => {
    // The install link's `state` param has to be a signed token from the API, not the
    // raw job id -- GitHub echoes it back untouched on the callback, so an unsigned
    // job id would let anyone link their own installation to someone else's job by
    // hand-crafting that callback URL.
    if (!jobId || connected) return;
    getGithubInstallState(jobId)
      .then((data) => setInstallState(data.state))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to prepare the install link"));
  }, [jobId, connected]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleFile() {
    setFiling(true);
    setError(null);
    try {
      await fileIssues(jobId, [...selected]);
      const data = await getJobReport(jobId);
      setFindings(data.findings);
      setSelected(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to file issues");
    } finally {
      setFiling(false);
    }
  }

  if (!jobId) {
    return (
      <main className="narrow">
        <div className="eyebrow">Mode B+</div>
        <h1>Connect GitHub</h1>
        <p className="muted">Missing job id — open this page from a scan report.</p>
      </main>
    );
  }

  if (!connected) {
    const installUrl = installState
      ? `https://github.com/apps/${GITHUB_APP_SLUG}/installations/new?state=${encodeURIComponent(installState)}`
      : null;
    return (
      <main className="narrow">
        <div className="eyebrow">Mode B+ · consent-based filing</div>
        <h1>Connect GitHub</h1>
        <div className="panel" style={{ marginTop: "1.5rem" }}>
          <p style={{ marginTop: 0 }}>
            Install the BugHound GitHub App on the repository you want issues filed to. You pick
            exactly which repo via GitHub&apos;s own install screen — BugHound only ever gets{" "}
            <code>issues:write</code> on that one repo.
          </p>
          {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
          <a href={installUrl ?? undefined} aria-disabled={!installUrl}>
            <button className="btn-primary" style={{ marginTop: "0.5rem" }} disabled={!installUrl}>
              {installUrl ? "Connect GitHub →" : "Preparing…"}
            </button>
          </a>
        </div>
      </main>
    );
  }

  return (
    <main>
      <div className="eyebrow">Step 2 of 2</div>
      <h1>Select findings to file</h1>
      <p className="muted" style={{ marginTop: "0.4rem" }}>
        Nothing is filed until you press &quot;File selected as issues&quot; below.
      </p>

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

      <div className="panel" style={{ marginTop: "1.25rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
          <span className="muted" style={{ fontSize: "0.85rem" }}>{selected.size} selected</span>
          <button className="btn-primary" onClick={handleFile} disabled={filing || selected.size === 0}>
            {filing ? "Filing…" : `File ${selected.size} selected as issues`}
          </button>
        </div>
        <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {findings.map((f) => {
            const tier = tierMeta(f.tier);
            return (
              <label
                key={f.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.6rem",
                  padding: "0.5rem 0.6rem",
                  borderRadius: "var(--radius-control)",
                  border: "1px solid var(--border)",
                  opacity: f.filed_as_issue ? 0.55 : 1,
                }}
              >
                <input
                  type="checkbox"
                  disabled={f.filed_as_issue}
                  checked={selected.has(f.id)}
                  onChange={() => toggle(f.id)}
                />
                <span className="badge" data-tier={f.tier} style={{ "--tier-color": tier.color } as React.CSSProperties}>
                  {tier.short}
                </span>
                <span style={{ fontSize: "0.88rem" }}>{f.title}</span>
                {f.filed_as_issue && <span className="faint" style={{ fontSize: "0.78rem" }}>already filed</span>}
              </label>
            );
          })}
        </div>
      </div>

      <FindingsList findings={findings} />
    </main>
  );
}
