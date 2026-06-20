-- =====================================================================
-- 0003_viewer_identity.sql
-- The share page now asks the viewer to identify themselves before the
-- reference is revealed. Store their declared name and organisation
-- alongside the email we already capture.
-- =====================================================================
alter table access_log add column if not exists accessed_by_name text;
alter table access_log add column if not exists viewer_org text;
