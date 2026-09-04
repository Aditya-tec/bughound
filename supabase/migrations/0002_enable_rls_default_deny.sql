-- Run this once against the live project (SQL Editor in the Supabase dashboard).
--
-- Real finding: NEXT_PUBLIC_SUPABASE_ANON_KEY is baked into the frontend's client-side
-- JS bundle (anyone can read it from page source), and with RLS off, that key could
-- read/insert/update every row directly via PostgREST -- bypassing api/security.py's
-- SSRF guard, api/owner_mode.py's allowlist, and api/rate_limit.py's cap entirely,
-- since those only run inside the FastAPI layer. Verified live: inserted a test job
-- and updated a findings row using nothing but the public anon key (both cleaned up
-- immediately after).
--
-- The frontend never talks to Supabase directly (confirmed: zero supabase-js usage
-- in apps/web -- every read/write goes through bughound-api, which uses the
-- service_role key and always bypasses RLS by design). So the correct fix is
-- default-deny for anon/authenticated on every table: no policies needed or wanted.
--
-- Idempotent: safe to run more than once.

alter table jobs enable row level security;
alter table findings enable row level security;
alter table runs_meta enable row level security;
alter table installations enable row level security;
