"""
Make the two AI 'analyse' paths vertical-aware too (pairs with ai.py + the
publish/draft patch). Run from repo root:

    python patch_ai_analyse.py

Edits backend/app/main.py:
  1. AiAnalyseIn gains an optional `vertical` field.
  2. /ai/analyse passes body.vertical into ai.synthesise.
  3. references_analyse fetches the template vertical (join) ...
  4. ... and passes it into ai.synthesise.

Idempotent; atomic (writes only if all edits match).
"""
import io, os, sys

PATH = os.path.join("backend", "app", "main.py")

edits = [
    # 1) add vertical to the analyse input model
    (
        "class AiAnalyseIn(BaseModel):\n"
        "    content: dict\n"
        "    assignment_context: str | None = None",

        "class AiAnalyseIn(BaseModel):\n"
        "    content: dict\n"
        "    assignment_context: str | None = None\n"
        "    vertical: str | None = None",
    ),
    # 2) pre-publish analyse: pass the vertical through
    (
        "        return await ai.synthesise(body.content, body.assignment_context)",
        "        return await ai.synthesise(body.content, body.assignment_context, body.vertical)",
    ),
    # 3) analyse-by-id: also fetch the template vertical
    (
        "        ref = await c.fetchrow(\n"
        "            'select issuing_org_id, content, assignment_context from \"references\" where id = $1',\n"
        "            reference_id,\n"
        "        )",

        "        ref = await c.fetchrow(\n"
        "            'select r.issuing_org_id, r.content, r.assignment_context, t.vertical '\n"
        "            'from \"references\" r left join reference_templates t on t.id = r.template_id '\n"
        "            'where r.id = $1',\n"
        "            reference_id,\n"
        "        )",
    ),
    # 4) analyse-by-id: pass the vertical into synthesise
    (
        '            result = await ai.synthesise(ref["content"] or {}, ref["assignment_context"])',
        '            result = await ai.synthesise(ref["content"] or {}, ref["assignment_context"], ref["vertical"])',
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

print("Done. Both analyse paths are now vertical-aware.")
