"""
Replace BillingPanel with a plan comparison table (honest to enforced features).
Run from repo root:

    python patch_billing.py

Finds 'function BillingPanel({ me }) {' and replaces the whole function (by
brace-matching) with the version in new_billing.jsx. Makes a .bak3 backup.
Refuses to double-apply.
"""
import io, os, sys

PATH = os.path.join("frontend", "app", "dashboard", "page.js")
NEW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "new_billing.jsx")
ANCHOR = "function BillingPanel({ me }) {"

with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if "const PLANS = [" in src and "Manager seats" in src:
    print("Billing table appears already applied. Aborting.")
    sys.exit(0)

i = src.find(ANCHOR)
if i == -1:
    print("ERROR: BillingPanel not found. No changes written.")
    sys.exit(1)

# brace-match from the function BODY opening brace, which is the final '{' of
# ANCHOR — NOT the '{' inside the ({ me }) parameter destructuring.
brace_start = i + len(ANCHOR) - 1
depth = 0
end = None
for k in range(brace_start, len(src)):
    c = src[k]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            end = k + 1
            break
if end is None:
    print("ERROR: could not brace-match the end of BillingPanel. No changes written.")
    sys.exit(1)

with io.open(NEW, "r", encoding="utf-8") as f:
    new_fn = f.read().rstrip()

with io.open(PATH + ".bak3", "w", encoding="utf-8") as f:
    f.write(src)

patched = src[:i] + new_fn + src[end:]
with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(patched)

print(f"OK: BillingPanel replaced ({end - i} chars). Backup at {PATH}.bak3")
