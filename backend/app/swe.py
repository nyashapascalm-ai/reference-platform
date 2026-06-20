"""Registration checks against a local copy of the Social Work England register.

SWE blocks server-side scraping of its website, so we no longer fetch it live.
Instead we keep a local copy of the register (table swe_register), populated from
SWE's official employer CSV export via the token-gated import endpoint, and check
against that. Mapping onto verification_status_t:
  - status starts with "Registered"            -> verified
  - "no longer registered"/removed/suspended   -> failed
  - number not in our copy:
        SWE_REGISTER_COMPLETE truthy            -> failed (genuinely not on register)
        otherwise                                -> pending (our copy may be partial)

Other registers (NMC/GMC/HCPC/TRN) are not yet automated and return 'pending'.
"""
import csv
import io
import os
from datetime import datetime, timezone

from . import db

_VALID_BODIES = {"swe", "nmc", "gmc", "hcpc", "trn"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(number: str) -> str:
    n = (number or "").strip().upper()
    return n if n.startswith("SW") else f"SW{n}"


async def check_registration(registration_body: str, registration_number: str) -> dict:
    body = (registration_body or "").lower()
    number = (registration_number or "").strip().upper()
    if body not in _VALID_BODIES or not number:
        return {"status": "failed", "checked_at": _now(), "detail": "missing or unknown registration details"}
    if body == "swe":
        return await _check_swe(number)
    return {"status": "pending", "checked_at": _now(),
            "detail": f"{body.upper()} register check is not yet automated"}


async def _check_swe(number: str) -> dict:
    norm = _norm(number)
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "select registered_name, status, registered_until from swe_register where registration_number = $1",
            norm,
        )
    if row:
        st = (row["status"] or "").lower()
        if st.startswith("registered"):
            mapped = "verified"
        elif any(w in st for w in ("no longer", "removed", "not registered", "suspended")):
            mapped = "failed"
        else:
            mapped = "pending"
        return {"status": mapped, "checked_at": _now(), "register_status": row["status"],
                "registered_name": row["registered_name"], "registered_until": row["registered_until"],
                "number": norm, "source": "Social Work England register (local copy)"}
    complete = os.environ.get("SWE_REGISTER_COMPLETE", "").lower() in ("1", "true", "yes")
    if complete:
        return {"status": "failed", "checked_at": _now(),
                "detail": "not found on the Social Work England register", "number": norm}
    return {"status": "pending", "checked_at": _now(),
            "detail": "awaiting verification against the Social Work England register", "number": norm}


def parse_csv(text: str) -> list:
    """Tolerantly parse SWE's employer CSV export into register rows."""
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    lower = {(h or "").strip().lower(): h for h in headers}

    def find(*keys):
        for k, orig in lower.items():
            if any(key in k for key in keys):
                return orig
        return None

    c_num = find("registration number", "reg no", "number")
    c_name = find("name")
    c_status = find("status")
    c_until = find("until", "expiry", "expires", "valid to", "registered to")
    c_town = find("town", "employer")

    rows = []
    for r in reader:
        raw = (r.get(c_num) or "").strip() if c_num else ""
        if not raw:
            continue
        rows.append({
            "number": _norm(raw),
            "name": (r.get(c_name) or "").strip() if c_name else None,
            "status": (r.get(c_status) or "").strip() if c_status else None,
            "until": (r.get(c_until) or "").strip() if c_until else None,
            "town": (r.get(c_town) or "").strip() if c_town else None,
        })
    return rows
