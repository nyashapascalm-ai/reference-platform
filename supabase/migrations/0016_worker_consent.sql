-- ============================================================
-- 0016  Worker consent (hold-release) for References Received
--   * worker_email + consent token on reference_requests
--   * consent_token_hash on reference_sends (the worker's consent link)
--   * a couple of helpful indexes
--
-- Run the whole block once in the Supabase SQL editor. Safe to re-run.
-- ============================================================

alter table reference_requests add column if not exists worker_email text;

-- The consent link the worker receives (hash only; raw token emailed once).
alter table reference_sends add column if not exists consent_token_hash text;
alter table reference_sends add column if not exists consent_decided_at  timestamptz;

create index if not exists ref_sends_consent_token_idx
  on reference_sends(consent_token_hash) where consent_token_hash is not null;

-- consent_status already exists on reference_sends with values pending|granted|declined.
