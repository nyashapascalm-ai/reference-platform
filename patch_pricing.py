"""
Update marketing /pricing feature bullets to match what the portal enforces.
Replaces only the four ASCII `features: [...]` arrays (prices/names/layout
untouched, so the GBP sign is never matched). Run from repo root:

    python patch_pricing.py

Backup .bak. Idempotent.
"""
import io, os, sys

PATH = os.path.join("frontend", "app", "pricing", "page.js")

edits = [
    # Free
    (
        "features: ['2 seats', 'Issue & verify references', 'Tamper-evident records', 'Worker sharing by consent'], cta: 'Start free'",
        "features: ['2 seats', 'Issue & verify references', 'Tamper-evident records', 'Consent-based worker sharing', 'AI fairness & sector analysis'], cta: 'Start free'",
    ),
    # Starter
    (
        "features: ['3 seats', 'Everything in Free', 'Team management', 'Reference records archive', 'Email support'], cta: 'Choose Starter'",
        "features: ['3 seats', 'Everything in Free', 'Team management & invites', 'Admin oversight & records', 'Email support'], cta: 'Choose Starter'",
    ),
    # Growth
    (
        "features: ['10 seats', 'Everything in Starter', 'Admin oversight & usage', 'Pay-as-you-go credits', 'Priority support'], cta: 'Choose Growth'",
        "features: ['10 seats', 'Everything in Starter', 'API access', 'White-label references', 'Pay-as-you-go credits', 'Priority support'], cta: 'Choose Growth'",
    ),
    # Business
    (
        "features: ['25 seats', 'Everything in Growth', 'API access', 'Advanced reporting', 'Onboarding help'], cta: 'Choose Business'",
        "features: ['25 seats', 'Everything in Growth', 'Onboarding support', 'Priority support'], cta: 'Choose Business'",
    ),
]

with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()
_orig = src

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

with io.open(PATH + ".bak", "w", encoding="utf-8") as f:
    f.write(_orig)
with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("Done. Pricing bullets now match the portal. Backup at " + PATH + ".bak")
