-- ============================================================
-- 0014  Public API keys (per-organisation).
--   Only a SHA-256 hash of the key is stored. The raw key
--   (rk_live_...) is shown to the admin exactly once.
--   A short non-secret prefix is kept for display ("rk_live_a1b2...").
-- Run the whole block once in the Supabase SQL editor.
-- ============================================================

create table if not exists api_keys (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references orgs(id) on delete cascade,
  name          text not null default 'API key',
  key_hash      text not null unique,
  prefix        text not null,                 -- e.g. 'rk_live_a1b2c3d4' (display only)
  created_by    uuid,                          -- profiles.id of the admin who made it
  last_used_at  timestamptz,
  revoked_at    timestamptz,
  created_at    timestamptz not null default now()
);

create index if not exists api_keys_org_idx on api_keys(org_id);
create index if not exists api_keys_hash_idx on api_keys(key_hash);

-- API-created references and workers have no Supabase user behind them, so
-- these columns must allow NULL. (No-op if already nullable.)
alter table "references" alter column created_by drop not null;
alter table workers      alter column profile_id  drop not null;
