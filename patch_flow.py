"""
Replace the OrgPanel component with a guided 3-step flow (Compose -> Review ->
Publish). Run from repo root:

    python patch_flow.py

It splices out everything between the ASCII boundaries
  'function OrgPanel({ me }) {'  ...  'function ReferenceBoard({ refs, onPublish }) {'
and inserts the rewritten component (read from new_orgpanel.jsx, which must sit
next to this script). The old body's special characters are never matched, so
encoding can't break the patch. ReferenceBoard and everything else are untouched.

Makes a .bak backup first. Idempotent-ish: refuses to run if the new marker
('const [step, setStep]') is already present.
"""
import io, os, sys

PATH = os.path.join("frontend", "app", "dashboard", "page.js")
NEW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "new_orgpanel.jsx")

START = "function OrgPanel({ me }) {"
END = "function ReferenceBoard({ refs, onPublish }) {"

with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if "const [step, setStep]" in src:
    print("Looks like the guided flow is already applied (found 'step' state). Aborting to avoid double-apply.")
    sys.exit(0)

i = src.find(START)
j = src.find(END)
if i == -1 or j == -1 or j <= i:
    print(f"ERROR: could not locate boundaries (start={i}, end={j}). No changes written.")
    sys.exit(1)

with io.open(NEW, "r", encoding="utf-8") as f:
    new_component = f.read().rstrip() + "\n\n"

# backup
with io.open(PATH + ".bak", "w", encoding="utf-8") as f:
    f.write(src)

patched = src[:i] + new_component + src[j:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(patched)

print(f"OK: replaced OrgPanel ({j - i} chars) with the guided-flow version.")
print(f"Backup written to {PATH}.bak")
