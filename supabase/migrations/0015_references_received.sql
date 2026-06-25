-- ============================================================
-- 0015  References Received framework
--   * permanent human reference number on each reference
--   * versioning (original frozen; amendments add versions)
--   * reference_requests: employer-to-employer request lifecycle
--   * reference_sends: every time a reference is sent to an employer
--   * reference_events: append-only audit trail
--
-- Run the whole block once in the Supabase SQL editor. Safe to re-run.
-- ============================================================

-- ---- 1. Human reference number + version pointer on references ----
alter table "references" add column if not exists ref_number   text;
alter table "references" add column if not exists version       integer not null default 1;
alter table "references" add column if not exists supersedes_id  uuid references "references"(id);
alter table "references" add column if not exists amendment_reason text;
alter table "references" add column if not exists negative_change  boolean not null default false;
alter table "references" add column if not exists amended_by    uuid;
alter table "references" add column if not exists is_current    boolean not null default true;

create unique index if not exists references_ref_number_uidx on "references"(ref_number) where ref_number is not null;

-- Backfill a reference number for any existing references that lack one.
-- Format: REF-XXXX-XXXX (uppercase hex; the application generates new ones the same way).
update "references"
   set ref_number = 'REF-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 4))
                    || '-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 4))
 where ref_number is null;


-- ---- 2. reference_requests: the employer-to-employer request lifecycle ----
-- A hiring provider requests a reference about a candidate from a previous
-- employer (the referee). On completion this can produce a "references" row.
create table if not exists reference_requests (
  id                 uuid primary key default gen_random_uuid(),
  requester_org_id   uuid not null references orgs(id) on delete cascade,
  requested_by       uuid,                       -- profiles.id of the manager (nullable: survives them leaving)
  worker_name        text not null,              -- candidate as named by the requester
  worker_id          uuid references workers(id),-- linked once known/consented
  prev_employer_name text,                        -- previous employer (free text + optional CQC match)
  cqc_provider_id    text,                        -- CQC register id if matched
  cqc_verified       boolean not null default false,
  referee_name       text,
  referee_email      text not null,
  referee_email_domain text,
  domain_verified    boolean not null default false,
  template_id        uuid references reference_templates(id),
  link_token_hash    text not null unique,        -- the secure completion link (hash only)
  status             text not null default 'sent',-- sent|opened|completed|expired|cancelled
  message            text,
  sent_at            timestamptz not null default now(),
  opened_at          timestamptz,
  completed_at       timestamptz,
  produced_reference_id uuid references "references"(id),
  created_at         timestamptz not null default now()
);
create index if not exists ref_requests_requester_idx on reference_requests(requester_org_id);
create index if not exists ref_requests_token_idx on reference_requests(link_token_hash);
create index if not exists ref_requests_worker_idx on reference_requests(worker_id);


-- ---- 3. reference_attachments: documents both directions ----
create table if not exists reference_attachments (
  id            uuid primary key default gen_random_uuid(),
  request_id    uuid references reference_requests(id) on delete cascade,
  reference_id  uuid references "references"(id) on delete cascade,
  direction     text not null,            -- 'outgoing' (with request) | 'returned' (with completion)
  filename      text not null,
  content_type  text,
  byte_size     integer,
  storage_key   text not null,            -- key in object storage
  uploaded_by   uuid,
  created_at    timestamptz not null default now()
);
create index if not exists ref_attach_request_idx on reference_attachments(request_id);
create index if not exists ref_attach_reference_idx on reference_attachments(reference_id);


-- ---- 4. reference_sends: every delivery of a reference to an employer ----
-- This powers "send the same reference again and again" + the recipient's
-- "Received references" inbox.
create table if not exists reference_sends (
  id              uuid primary key default gen_random_uuid(),
  reference_id    uuid not null references "references"(id) on delete cascade,
  reference_version integer not null default 1,
  sender_org_id   uuid not null references orgs(id),
  sent_by         uuid,                          -- profiles.id (nullable: survives leaving)
  recipient_org_id uuid references orgs(id),     -- set if recipient is a Reffolio org
  recipient_email text not null,
  recipient_name  text,
  consent_status  text not null default 'pending',-- pending|granted|declined
  delivered_at    timestamptz,
  opened_at       timestamptz,
  created_at      timestamptz not null default now()
);
create index if not exists ref_sends_reference_idx on reference_sends(reference_id);
create index if not exists ref_sends_recipient_org_idx on reference_sends(recipient_org_id);
create index if not exists ref_sends_sender_idx on reference_sends(sender_org_id);


-- ---- 5. reference_events: append-only audit trail ----
create table if not exists reference_events (
  id            uuid primary key default gen_random_uuid(),
  reference_id  uuid references "references"(id) on delete cascade,
  request_id    uuid references reference_requests(id) on delete cascade,
  event_type    text not null,   -- requested|delivered|opened|completed|sent|consent_requested|
                                  -- consent_granted|consent_declined|amended|viewed|withdrawn
  actor_org_id  uuid references orgs(id),
  actor_id      uuid,            -- profiles.id where applicable
  actor_name    text,
  actor_email   text,
  detail        jsonb,           -- event-specific data (e.g. version, reason, negative_change)
  ip_address    inet,
  created_at    timestamptz not null default now()
);
create index if not exists ref_events_reference_idx on reference_events(reference_id);
create index if not exists ref_events_request_idx on reference_events(request_id);
create index if not exists ref_events_type_idx on reference_events(event_type);
