-- ============================================================
-- 0017  Org setup + branding
--   * setup_complete flag (prompt orgs to choose their type once)
--   * branding columns (logo, colours, email signature) for the
--     per-company email branding build that follows
--   * cqc_provider_id + contact fields used in request emails
--
-- org_type_t and vertical_t already contain all needed values
-- (care_provider, school, mat, nhs_trust, local_authority, agency /
--  care, healthcare, teaching, social_work) so NO enum changes needed.
--
-- Run the whole block once in the Supabase SQL editor. Safe to re-run.
-- ============================================================

alter table orgs add column if not exists setup_complete   boolean not null default false;

-- Branding (used to populate request emails + the public form footer)
alter table orgs add column if not exists logo_url         text;
alter table orgs add column if not exists brand_color      text;            -- hex, e.g. #6C5CE7
alter table orgs add column if not exists email_signature  text;            -- free text / html-safe
alter table orgs add column if not exists cqc_provider_id  text;            -- their own CQC registration
alter table orgs add column if not exists contact_name     text;            -- sender name for emails
alter table orgs add column if not exists contact_phone    text;
alter table orgs add column if not exists contact_email    text;

-- Mark existing orgs that already have a sensible type as set up, so they
-- are not nagged. (They were created with a real org_type already.)
update orgs set setup_complete = true where setup_complete = false and org_type is not null;
