-- =====================================================================
-- 0009_member_titles.sql
-- Job title is a free label, separate from permission (role). Permission
-- stays two-level: org_admin (billing/team control) vs member.
-- =====================================================================
alter table profiles    add column if not exists title text;
alter table org_invites add column if not exists title text;
