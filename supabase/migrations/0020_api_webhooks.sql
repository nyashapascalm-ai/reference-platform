-- 0020_api_webhooks.sql
-- Outbound webhooks for the /v1 API. One or more endpoints per org; Reffolio
-- POSTs signed event payloads (referee_submitted, consent_granted, reference_received).

create table if not exists api_webhooks (
  id               uuid primary key default gen_random_uuid(),
  org_id           uuid not null references orgs(id) on delete cascade,
  url              text not null,
  secret           text not null,
  events           text[] not null default array['referee_submitted','consent_granted','reference_received'],
  active           boolean not null default true,
  created_at       timestamptz not null default now(),
  last_delivery_at timestamptz,
  last_status      int
);

create index if not exists api_webhooks_org_idx on api_webhooks(org_id) where active;
