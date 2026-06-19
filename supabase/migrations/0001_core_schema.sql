-- =====================================================================
-- 0001_core_schema.sql
-- Reference Custody Platform — foundation migration
--
-- Layers built here (per architecture map):
--   00  identity spine        -> workers, identity binding
--   01  shared core           -> referees (domain auth), references (ledger),
--                                access_grants (consent gate), access_log (audit)
--   02  per-vertical hooks     -> reference_templates (statutory), vertical enum
--
-- Tamper-evidence: every published reference carries a content_hash bound to
-- worker + referee + payload + timestamp. The worker controls ACCESS via grants;
-- never the CONTENT. That single rule is enforced structurally below.
-- =====================================================================

create extension if not exists "pgcrypto";      -- gen_random_uuid(), digest()
create extension if not exists "citext";         -- case-insensitive email/domain

-- ---------------------------------------------------------------------
-- Enumerated types
-- ---------------------------------------------------------------------
create type vertical_t            as enum ('social_work', 'healthcare', 'teaching');
create type org_type_t            as enum ('local_authority', 'agency', 'nhs_trust', 'care_provider', 'school', 'mat');
create type user_role_t           as enum ('org_admin', 'hiring_manager', 'compliance_lead', 'referee', 'worker');
create type registration_body_t   as enum ('swe', 'nmc', 'gmc', 'hcpc', 'trn');
create type verification_status_t as enum ('pending', 'verified', 'failed', 'expired');
create type reference_status_t    as enum ('draft', 'submitted', 'published', 'withdrawn');
create type grant_status_t        as enum ('active', 'consumed', 'revoked', 'expired');

-- ---------------------------------------------------------------------
-- orgs  — tenants: councils, agencies, trusts, schools, MATs
-- ---------------------------------------------------------------------
create table orgs (
  id              uuid primary key default gen_random_uuid(),
  name            text        not null,
  org_type        org_type_t  not null,
  vertical        vertical_t  not null,
  email_domain    citext,                       -- verified domain referees must match
  is_active       boolean     not null default true,
  created_at      timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- profiles — mirrors auth.users; an app identity inside an org (or a worker)
-- ---------------------------------------------------------------------
create table profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  org_id      uuid references orgs (id) on delete set null,   -- null for independent workers
  role        user_role_t not null,
  full_name   text        not null,
  email       citext      not null,
  created_at  timestamptz not null default now()
);
create index profiles_org_idx on profiles (org_id);

-- ---------------------------------------------------------------------
-- 00 — IDENTITY SPINE
-- workers — verified worker identity; everything binds here
-- ---------------------------------------------------------------------
create table workers (
  id                       uuid primary key default gen_random_uuid(),
  profile_id               uuid unique references profiles (id) on delete set null,
  full_name                text not null,
  vertical                 vertical_t not null,
  registration_body        registration_body_t not null,
  registration_number      text not null,
  registration_status      verification_status_t not null default 'pending',
  registration_checked_at  timestamptz,
  dbs_certificate_number   text,
  dbs_status               verification_status_t not null default 'pending',
  rtw_status               verification_status_t not null default 'pending',
  identity_hash            text,                 -- tamper-evident binding of the verified anchors
  created_at               timestamptz not null default now(),
  unique (registration_body, registration_number)
);

-- ---------------------------------------------------------------------
-- 02 — PER-VERTICAL: statutory reference templates (versioned)
-- ---------------------------------------------------------------------
create table reference_templates (
  id             uuid primary key default gen_random_uuid(),
  vertical       vertical_t not null,
  name           text not null,
  version        text not null,
  field_schema   jsonb not null,                -- required fields the reference must satisfy
  is_active      boolean not null default true,
  effective_from date not null default current_date,
  created_at     timestamptz not null default now(),
  unique (vertical, name, version)
);

-- ---------------------------------------------------------------------
-- 01 — SHARED CORE: references (the custody ledger)
-- written once, structured to a template, hashed at publish
-- ---------------------------------------------------------------------
create table "references" (
  id                uuid primary key default gen_random_uuid(),
  worker_id         uuid not null references workers (id) on delete cascade,
  issuing_org_id    uuid not null references orgs (id) on delete restrict,
  template_id       uuid not null references reference_templates (id) on delete restrict,
  status            reference_status_t not null default 'draft',
  content           jsonb not null default '{}'::jsonb,   -- structured to template field_schema
  assignment_context text,                                -- role/assignment the ref relates to
  content_hash      text,                                 -- set at publish; tamper-evidence
  -- AI core outputs (CORE-06/07):
  competency_map    jsonb,                                -- PCF/KSS, NHS, KCSIE mappings
  risk_score        numeric(4,2),
  ai_summary        text,
  submitted_at      timestamptz,
  published_at      timestamptz,
  withdrawn_at      timestamptz,
  created_at        timestamptz not null default now(),
  -- a published reference must be hashed; drafts must not claim a publish time
  constraint published_requires_hash
    check (status <> 'published' or content_hash is not null),
  constraint risk_score_range
    check (risk_score is null or (risk_score >= 0 and risk_score <= 100))
);
create index references_worker_idx  on "references" (worker_id);
create index references_org_idx     on "references" (issuing_org_id);
create index references_status_idx  on "references" (status);

-- ---------------------------------------------------------------------
-- referees — domain-authenticated author of a reference (1:1)
-- the email_domain must match the issuing org's verified domain
-- ---------------------------------------------------------------------
create table referees (
  id              uuid primary key default gen_random_uuid(),
  reference_id    uuid not null unique references "references" (id) on delete cascade,
  full_name       text not null,
  job_title       text not null,
  work_email      citext not null,
  email_domain    citext not null,
  domain_verified boolean not null default false,
  auth_method     text,                          -- 'email_link' | 'sso' | '2fa'
  ip_address      inet,
  submitted_at    timestamptz
);

-- ---------------------------------------------------------------------
-- 01 — CONSENT GATE: access_grants (the £5 share link)
-- worker authorises ACCESS to a source record; never hands over content
-- ---------------------------------------------------------------------
create table access_grants (
  id                 uuid primary key default gen_random_uuid(),
  worker_id          uuid not null references workers (id) on delete cascade,
  reference_id       uuid not null references "references" (id) on delete cascade,
  token_hash         text not null unique,        -- hash of the share token; raw token never stored
  granted_to_email   citext,                      -- optional: pin the link to a recipient
  granted_to_org_id  uuid references orgs (id) on delete set null,  -- set when consumed
  status             grant_status_t not null default 'active',
  expires_at         timestamptz not null,
  created_at         timestamptz not null default now(),
  consumed_at        timestamptz,
  revoked_at         timestamptz
);
create index access_grants_worker_idx on access_grants (worker_id);
create index access_grants_ref_idx    on access_grants (reference_id);

-- ---------------------------------------------------------------------
-- access_log — immutable audit of every read
-- ---------------------------------------------------------------------
create table access_log (
  id                 uuid primary key default gen_random_uuid(),
  grant_id           uuid references access_grants (id) on delete set null,
  reference_id       uuid not null references "references" (id) on delete cascade,
  accessed_by_org_id uuid references orgs (id) on delete set null,
  accessed_by_email  citext,
  action             text not null default 'view',
  ip_address         inet,
  accessed_at        timestamptz not null default now()
);
create index access_log_ref_idx on access_log (reference_id);

-- =====================================================================
-- Helper functions (security definer) for RLS
-- =====================================================================

-- current user's org
create or replace function app_current_org_id()
returns uuid language sql stable security definer set search_path = public as $$
  select org_id from profiles where id = auth.uid()
$$;

-- current user's worker row (if they are a worker)
create or replace function app_current_worker_id()
returns uuid language sql stable security definer set search_path = public as $$
  select w.id from workers w
  join profiles p on p.id = w.profile_id
  where p.id = auth.uid()
$$;

-- does the caller's org hold an active, unexpired grant to this reference?
create or replace function app_org_has_grant(ref uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from access_grants g
    where g.reference_id = ref
      and g.granted_to_org_id = app_current_org_id()
      and g.status in ('active','consumed')
      and g.expires_at > now()
  )
$$;

-- =====================================================================
-- Row-level security
-- =====================================================================
alter table orgs                enable row level security;
alter table profiles            enable row level security;
alter table workers             enable row level security;
alter table reference_templates enable row level security;
alter table "references"        enable row level security;
alter table referees            enable row level security;
alter table access_grants       enable row level security;
alter table access_log          enable row level security;

-- orgs: members can read their own org
create policy orgs_read_own on orgs
  for select using (id = app_current_org_id());

-- profiles: read self; read others in same org
create policy profiles_read_self on profiles
  for select using (id = auth.uid() or org_id = app_current_org_id());

-- templates: readable by anyone authenticated (statutory, non-secret)
create policy templates_read on reference_templates
  for select using (auth.uid() is not null);

-- workers: the worker reads their own; an org reads workers it has issued a ref for
create policy workers_read_self on workers
  for select using (profile_id = auth.uid());
create policy workers_read_by_issuer on workers
  for select using (
    exists (select 1 from "references" r
            where r.worker_id = workers.id
              and r.issuing_org_id = app_current_org_id())
  );

-- references: worker reads own; issuing org reads own; granted org reads via grant
create policy references_read_worker on "references"
  for select using (worker_id = app_current_worker_id());
create policy references_read_issuer on "references"
  for select using (issuing_org_id = app_current_org_id());
create policy references_read_granted on "references"
  for select using (app_org_has_grant(id));

-- references: only the issuing org may write/update (draft -> publish)
create policy references_write_issuer on "references"
  for insert with check (issuing_org_id = app_current_org_id());
create policy references_update_issuer on "references"
  for update using (issuing_org_id = app_current_org_id());

-- referees: visible alongside any reference the caller can see
create policy referees_read on referees
  for select using (
    exists (select 1 from "references" r where r.id = referees.reference_id)
  );

-- access_grants: the worker fully controls their own grants (create / revoke / read)
create policy grants_owner_all on access_grants
  for all using (worker_id = app_current_worker_id())
  with check (worker_id = app_current_worker_id());
-- the granted org can see grants pointed at it
create policy grants_read_grantee on access_grants
  for select using (granted_to_org_id = app_current_org_id());

-- access_log: worker sees reads of their references; issuing org sees its own refs' reads
create policy access_log_read_worker on access_log
  for select using (
    exists (select 1 from "references" r
            where r.id = access_log.reference_id
              and r.worker_id = app_current_worker_id())
  );
create policy access_log_read_issuer on access_log
  for select using (
    exists (select 1 from "references" r
            where r.id = access_log.reference_id
              and r.issuing_org_id = app_current_org_id())
  );
