-- Run this once against the live project (SQL Editor in the Supabase dashboard).
-- Adds the column api/rate_limit.py needs to cap job creation per IP.
-- Idempotent: safe to run more than once.

alter table jobs add column if not exists client_ip text;
create index if not exists jobs_client_ip_created_at_idx on jobs (client_ip, created_at);
