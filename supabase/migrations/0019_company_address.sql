-- 0019  Company address (shown on reference requests)
alter table orgs add column if not exists company_address text;

-- Make the date fields render as calendar pickers across all active templates.
-- (jsonb update: set type='date' on fields keyed known_from / known_to)
update reference_templates t
set field_schema = jsonb_set(
  field_schema,
  '{fields}',
  (
    select jsonb_agg(
      case when (f->>'key') in ('known_from','known_to')
           then jsonb_set(f, '{type}', '"date"')
           else f end
    )
    from jsonb_array_elements(field_schema->'fields') f
  )
)
where is_active = true
  and field_schema ? 'fields';
