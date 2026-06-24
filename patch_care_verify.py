"""
Patch backend/app/main.py to support workers who are NOT on a professional
register (most care workers). Run from the repo root:

    python patch_care_verify.py

It makes three surgical edits to backend/app/main.py:
  1. WorkerVerifyIn.registration_number becomes optional.
  2. workers_verify branches: if no register, skip the lookup and store an
     identity-based verification (status 'not_applicable') keyed on user_id.
  3. The insert uses the resolved reg_body / reg_number.

The SWE / registered flow is unchanged. Safe to run once.
"""
import io, sys, os

PATH = os.path.join("backend", "app", "main.py")

edits = [
    # 1) make registration_number optional on the input model
    (
        "    registration_number: str\n    dbs_certificate_number: str | None = None",
        "    registration_number: str | None = None\n    dbs_certificate_number: str | None = None",
    ),
    # 2) branch the verify logic for the no-register case
    (
        'async def workers_verify(body: WorkerVerifyIn, user=Depends(current_user)):\n'
        '    check = await check_registration(body.registration_body, body.registration_number)\n'
        '    idhash = identity_hash(body.registration_body, body.registration_number, body.dbs_certificate_number)',

        'async def workers_verify(body: WorkerVerifyIn, user=Depends(current_user)):\n'
        '    no_register = (body.registration_body or "").strip().lower() in ("none", "self", "")\n'
        '    if no_register:\n'
        '        reg_body = "none"\n'
        '        # NOT NULL + unique(registration_body, registration_number):\n'
        '        # user_id is unique per worker, so it is a safe synthetic key here.\n'
        '        reg_number = str(user["user_id"])\n'
        '        check = {\n'
        '            "status": "not_applicable",\n'
        '            "checked_at": _now(),\n'
        '            "detail": "Role is not on a professional register; identity-based verification.",\n'
        '        }\n'
        '    else:\n'
        '        reg_body = body.registration_body\n'
        '        if not body.registration_number:\n'
        '            raise HTTPException(422, "registration_number is required for this registration body")\n'
        '        reg_number = body.registration_number\n'
        '        check = await check_registration(reg_body, reg_number)\n'
        '    idhash = identity_hash(reg_body, reg_number, body.dbs_certificate_number)',
    ),
    # 3) use the resolved values in the insert params
    (
        '                    user["user_id"], body.full_name, body.vertical, body.registration_body,\n'
        '                    body.registration_number, check["status"], _now(),',

        '                    user["user_id"], body.full_name, body.vertical, reg_body,\n'
        '                    reg_number, check["status"], _now(),',
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
        print(f"ERROR edit {i}: expected to find the target block exactly once, found {n}.")
        print("No changes written. Paste this output back and we'll adjust the match.")
        sys.exit(1)
    src = src.replace(old, new)
    print(f"  edit {i}: applied")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("Done. backend/app/main.py patched for no-register verification.")
