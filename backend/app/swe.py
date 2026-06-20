"""Registration checks against professional registers.

Social Work England (SWE) publishes a public page per registrant at
  /umbraco/surface/searchregister/socialworker/{number}
We fetch it and read the visible "Status:" / "Registered name:" / "Registered until:"
fields. Mapping onto our verification_status_t:
  - "Registered" (incl. "subject to conditions")  -> verified
  - "no longer registered" / removed / not found   -> failed
  - any network or parse failure                    -> pending  (never falsely verify,
                                                                 never hard-block)

Other registers (NMC/GMC/HCPC/TRN) are not yet automated and return 'pending' honestly.
"""
import html as _html
import re
from datetime import datetime, timezone

import httpx

_VALID_BODIES = {"swe", "nmc", "gmc", "hcpc", "trn"}
_SWE_URL = "https://www.socialworkengland.org.uk/umbraco/surface/searchregister/socialworker/{number}"
_UA = "ReferenceCustodyPlatform/1.0 (registration verification)"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", _html.unescape(raw)).strip()


def _field(text: str, label: str, stop_words: list) -> str:
    stop = "|".join(re.escape(s) for s in stop_words)
    m = re.search(rf"{re.escape(label)}\s*(.+?)\s*(?:{stop})", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def parse_swe(raw_html: str, norm: str) -> dict:
    """Pure parser (no network) so it can be unit-tested."""
    text = _to_text(raw_html)
    if "Registration Number" not in text or norm not in text or "Status:" not in text:
        return {"status": "failed", "detail": "not found on the Social Work England register", "number": norm}
    status_text = _field(text, "Status:", ["Read more", "Town of employment", "Registered from"])
    name = _field(text, "Registered name:", ["This is the name", "Registration Number"])
    until = _field(text, "Registered until:", ["This date", "Annotations", "Guide to the register"])
    s = (status_text or "").lower()
    if s.startswith("registered"):
        mapped = "verified"
    elif any(w in s for w in ("no longer", "removed", "not registered", "suspended")):
        mapped = "failed"
    else:
        mapped = "pending"
    return {"status": mapped, "register_status": status_text, "registered_name": name,
            "registered_until": until, "number": norm}


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
    norm = number if number.startswith("SW") else f"SW{number}"
    url = _SWE_URL.format(number=norm)
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers={"User-Agent": _UA}) as cx:
            r = await cx.get(url)
        if r.status_code != 200:
            return {"status": "pending", "checked_at": _now(),
                    "detail": f"register returned HTTP {r.status_code}", "number": norm}
        out = parse_swe(r.text, norm)
        out["checked_at"] = _now()
        out["source"] = url
        return out
    except Exception as e:
        return {"status": "pending", "checked_at": _now(),
                "detail": f"register unreachable ({e.__class__.__name__})", "number": norm}
