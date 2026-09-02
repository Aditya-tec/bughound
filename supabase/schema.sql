create extension if not exists "pgcrypto";

create table jobs (
  id uuid primary key default gen_random_uuid(),
  target_url text not null,
  mode text not null check (mode in ('scan','owner')),
  status text not null default 'queued' check (status in ('queued','running','completed','failed')),
  pages_crawled int default 0,
  actions_taken int default 0,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz default now()
);

create table findings (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs(id) on delete cascade,
  tier int not null,               -- 1 through 8
  category text not null,          -- 'console_error','broken_link','a11y','performance','seo','security','responsive','visual_ux','flow'
  severity text not null check (severity in ('low','medium','high','critical')),
  page_url text not null,
  title text not null,
  description text,
  repro_steps text,
  screenshot_url text,
  filed_as_issue boolean default false,
  issue_url text,
  created_at timestamptz default now()
);

create table runs_meta (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs(id) on delete cascade,
  gemini_calls int default 0,
  tokens_used int default 0,
  estimated_cost_usd numeric default 0,
  duration_seconds int,
  created_at timestamptz default now()
);

create table installations (
  id uuid primary key default gen_random_uuid(),
  installation_id bigint not null,
  repo_full_name text not null,
  linked_job_id uuid references jobs(id),
  connected_at timestamptz default now()
);
