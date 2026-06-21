-- =====================================================================
-- 0010_oversight.sql
-- Admin oversight: attribute references to their author, allow admins to
-- lock a member's account, and freeze a disputed reference.
-- =====================================================================
alter table "references" add column if not exists created_by uuid;
alter table "references" add column if not exists frozen_at  timestamptz;
alter table profiles     add column if not exists is_locked  boolean not null default false;

create index if not exists references_created_by_idx on "references" (created_by);
