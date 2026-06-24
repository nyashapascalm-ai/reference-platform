-- ============================================================
-- 0013  Seed healthcare (NMC/HCPC) and teaching (KCSIE / Teachers'
--       Standards) reference templates.
--
-- The 'healthcare' and 'teaching' verticals already exist in vertical_t,
-- so this is a single step (no ALTER TYPE). Run the whole block once in
-- the Supabase SQL editor. Safe to re-run (guarded with NOT EXISTS).
-- ============================================================

-- ---------- Healthcare (NMC / HCPC) ----------
insert into reference_templates (vertical, name, version, field_schema, is_active)
select
  'healthcare',
  'NHS / healthcare reference (NMC & HCPC)',
  '1',
  '{
     "fields": [
       {"key":"role","label":"Role / post held (e.g. Registered Nurse, Band 5)","type":"text"},
       {"key":"employment_from","label":"Employment start (month & year)","type":"text"},
       {"key":"employment_to","label":"Employment end (month & year, or \"current\")","type":"text"},
       {"key":"reason_for_leaving","label":"Reason for leaving","type":"text"},
       {"key":"employment_gaps","label":"Known gaps in employment & explanation","type":"textarea"},
       {"key":"registration_standing","label":"Professional registration standing (NMC/HCPC) and any restrictions","type":"textarea"},
       {"key":"clinical_competence","label":"Clinical competence and standard of practice","type":"textarea"},
       {"key":"conduct","label":"Conduct, reliability and attendance","type":"textarea"},
       {"key":"fitness_to_practise","label":"Any fitness-to-practise, disciplinary or capability proceedings (current or concluded)","type":"textarea"},
       {"key":"safeguarding_concerns","label":"Any safeguarding concerns or allegations relating to patients, adults or children","type":"textarea"},
       {"key":"suitable_patient_care","label":"In your professional view, is this person suitable for a role involving patient care? Please explain.","type":"textarea"},
       {"key":"would_reemploy","label":"Would you re-employ this person?","type":"text"},
       {"key":"additional_comments","label":"Any additional comments","type":"textarea"}
     ],
     "required": ["role","employment_from","employment_to","reason_for_leaving","registration_standing","clinical_competence","fitness_to_practise","safeguarding_concerns","suitable_patient_care"]
   }'::jsonb,
  true
where not exists (
  select 1 from reference_templates
  where vertical = 'healthcare' and name = 'NHS / healthcare reference (NMC & HCPC)'
);


-- ---------- Teaching (KCSIE / Teachers' Standards) ----------
insert into reference_templates (vertical, name, version, field_schema, is_active)
select
  'teaching',
  'Education reference (KCSIE safer recruitment)',
  '1',
  '{
     "fields": [
       {"key":"role","label":"Role / post held (e.g. Class Teacher, TA)","type":"text"},
       {"key":"employment_from","label":"Employment start (month & year)","type":"text"},
       {"key":"employment_to","label":"Employment end (month & year, or \"current\")","type":"text"},
       {"key":"reason_for_leaving","label":"Reason for leaving","type":"text"},
       {"key":"employment_gaps","label":"Known gaps in employment & explanation","type":"textarea"},
       {"key":"professional_performance","label":"Professional performance against the Teachers'' Standards (or role equivalent)","type":"textarea"},
       {"key":"conduct","label":"Conduct, reliability and attendance","type":"textarea"},
       {"key":"disciplinary_allegations","label":"All disciplinary action, capability proceedings and any allegations relating to the safety and welfare of children (including time-expired, where they relate to safeguarding)","type":"textarea"},
       {"key":"safeguarding_concerns","label":"Any safeguarding concerns, referrals or substantiated allegations relating to children","type":"textarea"},
       {"key":"suitable_children","label":"In your professional view, is this person suitable to work with children? Please explain.","type":"textarea"},
       {"key":"would_reemploy","label":"Would you re-employ this person?","type":"text"},
       {"key":"additional_comments","label":"Any additional comments","type":"textarea"}
     ],
     "required": ["role","employment_from","employment_to","reason_for_leaving","conduct","disciplinary_allegations","safeguarding_concerns","suitable_children"]
   }'::jsonb,
  true
where not exists (
  select 1 from reference_templates
  where vertical = 'teaching' and name = 'Education reference (KCSIE safer recruitment)'
);
