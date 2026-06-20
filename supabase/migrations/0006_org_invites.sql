-- =====================================================================
-- 0006_org_invites.sql
-- Proper invite flow: an org admin invites a colleague by email; the
-- colleague accepts via a one-time link and joins THAT org with a role.
-- Replaces open self-onboarding into arbitrary orgs.
-- =====================================================================
create table if not exists org_invites (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references orgs(id) on delete cascade,
  email       citext not null,
  role        user_role_t not null default 'hiring_manager',
  token_hash  text not null,
  invited_by  uuid references profiles(id),
  accepted_at timestamptz,
  expires_at  timestamptz not null,
  created_at  timestamptz not null default now()
);
create index if not exists org_invites_token_idx on org_invites(token_hash);
create index if not exists org_invites_org_idx on org_invites(org_id);
