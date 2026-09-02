"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fileIssues, getJobReport, type Finding } from "@/lib/api";
import FindingsList from "@/components/FindingsList";

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

  useEffect(() => {
    if (!jobId) return;
    getJobReport(jobId)
      .then((data) => setFindings(data.findings))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load findings"));
  }, [jobId]);

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
      <main>
        <h1>Connect GitHub</h1>
        <p className="muted">Missing job id — open this page from a scan report.</p>
      </main>
    );
  }

  const installUrl = `https://github.com/apps/${GITHUB_APP_SLUG}/installations/new?state=${jobId}`;

  if (!connected) {
    return (
      <main>
        <h1>Connect GitHub</h1>
        <p>
          Install the BugHound GitHub App on the repository you want issues filed to. You pick
          exactly which repo via GitHub&apos;s own install screen — BugHound only ever gets
          <code> issues:write</code> on that one repo.
        </p>
        <a href={installUrl}>
          <button>Connect GitHub</button>
        </a>
      </main>
    );
  }

  return (
    <main>
      <h1>Select findings to file</h1>
      <p className="muted">
        Nothing is filed until you press &quot;File selected as issues&quot; below.
      </p>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <button onClick={handleFile} disabled={filing || selected.size === 0}>
        {filing ? "Filing…" : `File ${selected.size} selected as issues`}
      </button>
      <div style={{ marginTop: "1rem" }}>
        {findings.map((f) => (
          <label key={f.id} style={{ display: "block", marginBottom: "0.25rem" }}>
            <input
              type="checkbox"
              disabled={f.filed_as_issue}
              checked={selected.has(f.id)}
              onChange={() => toggle(f.id)}
            />{" "}
            {f.title} {f.filed_as_issue && <span className="muted">(already filed)</span>}
          </label>
        ))}
      </div>
      <FindingsList findings={findings} />
    </main>
  );
}
