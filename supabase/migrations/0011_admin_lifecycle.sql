-- =====================================================================
-- 0011_admin_lifecycle.sql
-- Operator controls: suspend / archive an org, and a billing-events log
-- so churn and status trends can be measured from now on.
-- =====================================================================
alter table orgs add column if not exists is_suspended boolean not null default false;
alter table orgs add column if not exists archived_at  timestamptz;

create table if not exists billing_events (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid,
  status      text,
  plan        text,
  created_at  timestamptz not null default now()
);
create index if not exists billing_events_org_idx     on billing_events (org_id);
create index if not exists billing_events_created_idx  on billing_events (created_at);
