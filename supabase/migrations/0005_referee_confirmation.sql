-- =====================================================================
-- 0005_referee_confirmation.sql
-- The named referee attests authorship: they receive an email link, click
-- to confirm, and the reference records who confirmed and when. This turns
-- a domain-matched referee into an actively-attested one.
-- =====================================================================
alter table referees add column if not exists confirm_token_hash text;
alter table referees add column if not exists confirm_sent_at    timestamptz;
alter table referees add column if not exists confirmed_at       timestamptz;
alter table referees add column if not exists confirmed_name     text;
