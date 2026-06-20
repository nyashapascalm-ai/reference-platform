-- =====================================================================
-- 0007_swe_register.sql
-- Local copy of the Social Work England register, populated from SWE's
-- official employer export (CSV). The live registration check reads THIS
-- table instead of scraping the website (which blocks server requests).
-- =====================================================================
create table if not exists swe_register (
  registration_number text primary key,
  registered_name     text,
  status              text,
  registered_until    text,
  town                text,
  updated_at          timestamptz not null default now()
);
