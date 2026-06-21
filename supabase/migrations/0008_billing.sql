-- =====================================================================
-- 0008_billing.sql
-- Stripe billing: one billing record per organisation, plus a PAYG
-- credit ledger for pay-as-you-go verifications.
-- =====================================================================
create table if not exists billing_customers (
  org_id                  uuid primary key references orgs(id) on delete cascade,
  stripe_customer_id      text unique,
  stripe_subscription_id  text,
  plan                    text not null default 'free',     -- free | starter | growth | enterprise
  status                  text not null default 'inactive', -- inactive | active | trialing | past_due | canceled
  seats                   int  not null default 2,
  current_period_end      timestamptz,
  updated_at              timestamptz not null default now()
);

create table if not exists billing_credits (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid references orgs(id) on delete cascade,
  delta       int  not null,            -- +N purchased, -1 consumed
  reason      text,
  created_at  timestamptz not null default now()
);
create index if not exists idx_billing_credits_org on billing_credits(org_id);
