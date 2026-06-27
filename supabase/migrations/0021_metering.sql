-- 0021_metering.sql
-- Per-reference metering: each verified (consent-granted) reference consumes one credit.
-- ref_id ties the charge to the reference; the unique index makes double-charging impossible.

alter table billing_credits add column if not exists ref_id uuid;

-- One consumption row per (org, reference). Only applies to consumption rows
-- (reason='reference'); purchases (ref_id null) are unaffected.
create unique index if not exists billing_credits_ref_uniq
  on billing_credits (org_id, ref_id)
  where reason = 'reference' and ref_id is not null;
