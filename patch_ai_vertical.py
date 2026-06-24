"""
Thread the reference template's vertical into the AI calls so assessments use
the right sector framework (care vs social work etc). Run from repo root:

    python patch_ai_vertical.py

Edits backend/app/main.py:
  1. publish: fetch the template's vertical alongside field_schema
  2. publish: pass that vertical into ai.synthesise
  3. draft:  fetch the template's vertical alongside field_schema
  4. draft:  pass that vertical into ai.draft_reference

Backward compatible (the new ai.py params default to a generic profile).
Idempotent. Pair with the new ai.py.
"""
import io, os, sys

PATH = os.path.join("backend", "app", "main.py")

edits = [
    # 1) publish: add vertical to the template fetch
    (
        '        tmpl = await c.fetchrow("select field_schema from reference_templates where id = $1", ref["template_id"])',
        '        tmpl = await c.fetchrow("select field_schema, vertical from reference_templates where id = $1", ref["template_id"])',
    ),
    # 2) publish: pass vertical into synthesise
    (
        "            result = await ai.synthesise(content, None)",
        '            result = await ai.synthesise(content, None, tmpl["vertical"] if tmpl else None)',
    ),
    # 3) draft: add vertical to the template fetch
    (
        '        tmpl = await c.fetchrow("select field_schema from reference_templates where id = $1", body.template_id)',
        '        tmpl = await c.fetchrow("select field_schema, vertical from reference_templates where id = $1", body.template_id)',
    ),
    # 4) draft: pass vertical into draft_reference
    (
        "        content = await ai.draft_reference(body.notes, required)",
        '        content = await ai.draft_reference(body.notes, required, tmpl["vertical"] if tmpl else None)',
    ),
]

with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

for i, (old, new) in enumerate(edits, 1):
    if new in src and old not in src:
        print(f"  edit {i}: already applied, skipping")
        continue
    n = src.count(old)
    if n != 1:
        print(f"ERROR edit {i}: expected target exactly once, found {n}. No changes written.")
        sys.exit(1)
    src = src.replace(old, new)
    print(f"  edit {i}: applied")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("Done. AI calls are now vertical-aware.")
