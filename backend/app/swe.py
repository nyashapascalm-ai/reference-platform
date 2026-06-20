"""Registration checks against professional registers.

STUB: this returns 'verified' for any well-formed registration number so the rest
of the flow can be built and tested. Replace check_registration() with the real
Social Work England (and later NMC / GMC / HCPC / TRN) register lookups without
changing any caller.
"""
from datetime import datetime, timezone

_VALID_BODIES = {"swe", "nmc", "gmc", "hcpc", "trn"}


async def check_registration(registration_body: str, registration_number: str) -> dict:
    body = registration_body.lower()
    number = (registration_number or "").strip()

    if body not in _VALID_BODIES or not number:
        return {"status": "failed", "checked_at": _now()}

    # --- STUB boundary -------------------------------------------------
    # Real implementation will query the SWE public register here and map the
    # response (active / lapsed / removed) onto our status values.
    return {"status": "verified", "checked_at": _now()}
    # -------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
