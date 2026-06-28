-- 0022_partners.sql
-- Partner foundation: attribute references to partners for billing/rev-share.

create table if not exists partners (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  contact_email text,
  -- Commercial terms (per-deal flexible):
  price_per_ref numeric(10,2),          -- agreed price per generated reference (GBP)
  rev_share_pct numeric(5,2),           -- partner's share % (e.g. 30.00). Reffolio keeps the rest.
  active        boolean not null default true,
  notes         text,
  created_at    timestamptz not null default now()
);

-- Attribution columns. API key first, org as fallback.
alter table api_keys      add column if not exists partner_id uuid references partners(id) on delete set null;
alter table orgs          add column if not exists partner_id uuid references partners(id) on delete set null;
alter table billing_credits add column if not exists partner_id uuid references partners(id) on delete set null;

create index if not exists api_keys_partner_idx       on api_keys(partner_id)       where partner_id is not null;
create index if not exists orgs_partner_idx           on orgs(partner_id)           where partner_id is not null;
create index if not exists billing_credits_partner_idx on billing_credits(partner_id) where partner_id is not null;
