-- =====================================================================
-- 0004_share_codes.sql
-- Verified-recipient flow: when a share link is pinned to an email, the
-- viewer must enter a one-time code sent to that inbox before the
-- reference is revealed. Each code is single-use and short-lived.
-- =====================================================================
create table if not exists share_codes (
  id          uuid primary key default gen_random_uuid(),
  grant_id    uuid not null references access_grants(id) on delete cascade,
  email       citext not null,
  code_hash   text not null,
  expires_at  timestamptz not null,
  used_at     timestamptz,
  created_at  timestamptz not null default now()
);
create index if not exists share_codes_grant_idx on share_codes(grant_id);

-- mark which access-log entries were identity-verified (vs self-declared)
alter table access_log add column if not exists verified boolean not null default false;
