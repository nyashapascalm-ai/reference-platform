"""
Turn the dashboard into a sidebar + home-tiles shell. Run from repo root:

    python patch_shell.py

Two changes to frontend/app/dashboard/page.js:
  1. Prepend the shell helper components (Icon, Tile, Shell) from shell.jsx,
     right before 'export default function Dashboard() {'.
  2. Replace the Dashboard component (between 'export default function
     Dashboard() {' and the following 'function Onboarding(') with the
     tile/sidebar version from new_dashboard.jsx.

All existing panels (OrgPanel, AdminOversightPanel, TeamPanel, BillingPanel,
WorkerPanel, Onboarding, etc.) are untouched and simply mounted by the shell.
Matches only ASCII boundaries, so encoding can't break it. Makes a .bak.
Refuses to double-apply.
"""
import io, os, sys

PATH = os.path.join("frontend", "app", "dashboard", "page.js")
HERE = os.path.dirname(os.path.abspath(__file__))
SHELL = os.path.join(HERE, "shell.jsx")
NEWDASH = os.path.join(HERE, "new_dashboard.jsx")

START = "export default function Dashboard() {"
END = "function Onboarding({ onDone, role, setRole }) {"

with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if "function Shell(" in src or "function Tile(" in src:
    print("Shell appears already applied (found Shell/Tile). Aborting to avoid double-apply.")
    sys.exit(0)

i = src.find(START)
j = src.find(END)
if i == -1 or j == -1 or j <= i:
    print(f"ERROR: boundaries not found (start={i}, end={j}). No changes written.")
    sys.exit(1)

with io.open(SHELL, "r", encoding="utf-8") as f:
    shell = f.read().rstrip() + "\n\n"
with io.open(NEWDASH, "r", encoding="utf-8") as f:
    newdash = f.read().rstrip() + "\n\n"

# backup
with io.open(PATH + ".bak2", "w", encoding="utf-8") as f:
    f.write(src)

# prepend shell helpers before Dashboard, then replace Dashboard body up to Onboarding
patched = src[:i] + shell + newdash + src[j:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(patched)

print(f"OK: shell prepended + Dashboard replaced ({j - i} chars swapped).")
print(f"Backup at {PATH}.bak2")
