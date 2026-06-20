-- =====================================================================
-- 0002_risk_score_precision.sql
-- numeric(4,2) maxes out at 99.99, but risk_score is defined 0-100.
-- Widen to numeric(5,2) so a full 100.00 can be stored.
-- =====================================================================
alter table "references" alter column risk_score type numeric(5,2);
