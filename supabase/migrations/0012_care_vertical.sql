-- ============================================================
-- 0012  Care sector: new vertical, no-register verification,
--       and the CQC care & support reference template.
--
-- IMPORTANT: run this in TWO STEPS in the Supabase SQL editor.
-- Postgres will not let you USE a new enum value in the same
-- transaction that ADDED it, so Step 1 must commit before Step 2.
-- (Just run the two blocks one after the other.)
-- ============================================================


-- ===== STEP 1 — run this block first, on its own =====
alter type vertical_t            add value if not exists 'care';
alter type registration_body_t   add value if not exists 'none';
alter type verification_status_t add value if not exists 'not_applicable';


-- ===== STEP 2 — run this block after Step 1 has committed =====
insert into reference_templates (vertical, name, version, field_schema, is_active)
select
  'care',
  'CQC care & support reference',
  '1',
  '{
     "fields": [
       {"key":"role","label":"Role / job title held","type":"text"},
       {"key":"employment_from","label":"Employment start (month & year)","type":"text"},
       {"key":"employment_to","label":"Employment end (month & year, or \"current\")","type":"text"},
       {"key":"reason_for_leaving","label":"Reason for leaving","type":"text"},
       {"key":"employment_gaps","label":"Known gaps in employment & explanation","type":"textarea"},
       {"key":"conduct","label":"Conduct, reliability & attendance","type":"textarea"},
       {"key":"disciplinary_concerns","label":"Any disciplinary, capability or performance concerns","type":"textarea"},
       {"key":"safeguarding_concerns","label":"Any safeguarding concerns or allegations relating to adults or children","type":"textarea"},
       {"key":"suitable_vulnerable_adults","label":"In your professional view, is this person suitable to work with vulnerable adults? Please explain.","type":"textarea"},
       {"key":"would_reemploy","label":"Would you re-employ this person?","type":"text"},
       {"key":"additional_comments","label":"Any additional comments","type":"textarea"}
     ],
     "required": ["role","employment_from","employment_to","reason_for_leaving","conduct","safeguarding_concerns","suitable_vulnerable_adults"]
   }'::jsonb,
  true
where not exists (
  select 1 from reference_templates
  where vertical = 'care' and name = 'CQC care & support reference'
);
