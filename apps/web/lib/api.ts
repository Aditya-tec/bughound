const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export type Mode = "scan" | "owner";

export interface Finding {
  id: string;
  job_id: string;
  tier: number;
  category: string;
  severity: "low" | "medium" | "high" | "critical";
  page_url: string;
  title: string;
  description: string | null;
  repro_steps: string | null;
  screenshot_url: string | null;
  filed_as_issue: boolean;
  issue_url: string | null;
  created_at: string;
}

export interface Job {
  id: string;
  target_url: string;
  mode: Mode;
  status: "queued" | "running" | "completed" | "failed";
  pages_crawled: number;
  actions_taken: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface JobWithFindings {
  job: Job;
  findings: Finding[];
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function createJob(targetUrl: string, mode: Mode): Promise<{ job_id: string }> {
  return apiFetch("/api/jobs", {
    method: "POST",
    body: JSON.stringify({ target_url: targetUrl, mode }),
  });
}

export function getJob(jobId: string): Promise<JobWithFindings> {
  return apiFetch(`/api/jobs/${jobId}`);
}

export function getJobReport(jobId: string): Promise<JobWithFindings> {
  return apiFetch(`/api/jobs/${jobId}/report`);
}

export function fileIssues(jobId: string, findingIds: string[]): Promise<unknown> {
  return apiFetch(`/api/jobs/${jobId}/file-issues`, {
    method: "POST",
    body: JSON.stringify({ finding_ids: findingIds }),
  });
}
