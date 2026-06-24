"""
Frontend: make 'Analyse draft' sector-aware and fix the PCF/KSS-only tooltip.
Run from repo root:

    python patch_ai_ui.py

Edits frontend/app/dashboard/page.js:
  1. analyseDraft sends the selected template's vertical to /ai/analyse.
  2. The 'Analyse draft' helper text no longer hard-codes PCF/KSS (it adapts
     per sector now).

Idempotent; atomic.
"""
import io, os, sys

PATH = os.path.join("frontend", "app", "dashboard", "page.js")

edits = [
    # 1) send vertical on pre-publish analyse
    (
        "    try { const r = await api('/ai/analyse', { method: 'POST', body: { content, assignment_context: meta.assignment_context } }); setDraftScore(r); setAiMsg(''); }",
        "    try { const r = await api('/ai/analyse', { method: 'POST', body: { content, assignment_context: meta.assignment_context, vertical: tpl?.vertical } }); setDraftScore(r); setAiMsg(''); }",
    ),
    # 2) sector-neutral tooltip
    (
        'professional frameworks (PCF/KSS), so you can sense-check it before publishing." />',
        'the professional framework for the selected template\u2019s sector, so you can sense-check it before publishing." />',
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

print("Done. Analyse draft is now sector-aware.")
