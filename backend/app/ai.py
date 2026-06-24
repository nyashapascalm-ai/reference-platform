"""AI core — the differentiators, powered by the Anthropic API.

  draft_reference  rough manager notes      -> structured, template-compliant content
  check_reference  a drafted reference      -> fairness / defamation flags + safe rewrite
  synthesise       a published reference     -> competency map, risk score, summary

All assessment is VERTICAL-AWARE: the framework used to assess a reference is
chosen from the worker's sector (social_work -> PCF/KSS, care -> CQC fit-person
& safeguarding of adults, healthcare -> NMC/HCPC, teaching -> Teachers' Standards
& KCSIE), with a sensible generic fallback. A care reference is never assessed
against children's social-work standards.

The model is overridable with ANTHROPIC_MODEL; the API key comes from
ANTHROPIC_API_KEY. `_complete` is module-level so it can be patched in tests
without network access.
"""
import json
import os

from anthropic import AsyncAnthropic

_client: AsyncAnthropic | None = None
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


# --- per-vertical assessment profiles -------------------------------------
# Each entry: the sector label, the drafting register, the assessment
# framework, and the JSON keys the competency map should use.
_PROFILES = {
    "social_work": {
        "sector": "UK children's and adults' social work",
        "draft_role": "UK social-work employment references",
        "framework": (
            "the Professional Capabilities Framework (PCF) and the "
            "Knowledge & Skills Statements (KSS)"
        ),
        "map_keys": '{ "PCF": [..], "KSS": [..] }',
    },
    "care": {
        "sector": "UK adult social care (CQC-regulated care & support work)",
        "draft_role": "UK adult social care employment references",
        "framework": (
            "CQC fit-and-proper-person expectations: suitability to work with "
            "vulnerable adults, safeguarding, reliability and conduct, and the "
            "Care Certificate standards where relevant. Do NOT use children's "
            "social-work frameworks (PCF/KSS) for care-worker references"
        ),
        "map_keys": '{ "Suitability": [..], "Safeguarding": [..], "Conduct": [..] }',
    },
    "healthcare": {
        "sector": "UK healthcare (nursing / allied health professions)",
        "draft_role": "UK healthcare employment references",
        "framework": (
            "the relevant professional regulator's standards (NMC Code for "
            "nursing, HCPC standards for allied health professions), patient "
            "safety, safeguarding, and fitness to practise"
        ),
        "map_keys": '{ "Standards": [..], "Safeguarding": [..], "Conduct": [..] }',
    },
    "teaching": {
        "sector": "UK education (teaching and school staff)",
        "draft_role": "UK education employment references",
        "framework": (
            "the Teachers' Standards and Keeping Children Safe in Education "
            "(KCSIE): suitability to work with children, safeguarding, and "
            "professional conduct"
        ),
        "map_keys": '{ "Standards": [..], "Safeguarding": [..], "Conduct": [..] }',
    },
}

_GENERIC = {
    "sector": "UK regulated employment",
    "draft_role": "UK employment references",
    "framework": (
        "general suitability for the role, safeguarding where relevant, "
        "reliability and professional conduct"
    ),
    "map_keys": '{ "Suitability": [..], "Conduct": [..] }',
}


def _profile(vertical: str | None) -> dict:
    return _PROFILES.get((vertical or "").strip().lower(), _GENERIC)


def _client_or_init() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


async def _complete(system: str, user: str, max_tokens: int = 1200) -> str:
    msg = await _client_or_init().messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")


def _extract_json(text: str):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    t = t.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i != -1 and j != -1:
            return json.loads(t[i:j + 1])
        raise


async def draft_reference(notes: str, required_fields: list[str], vertical: str | None = None) -> dict:
    p = _profile(vertical)
    system = (
        f"You write {p['draft_role']}. Produce only factual, "
        "evidence-based, fair language. Avoid opinion presented as fact, avoid any "
        "discriminatory content, and never invent specifics not supported by the notes. "
        "Return STRICT JSON only — an object whose keys are exactly the requested fields, "
        "each a concise string. No prose, no markdown."
    )
    user = (
        f"Required fields: {required_fields}\n\n"
        f"Manager's rough notes:\n{notes}\n\n"
        "Return a JSON object with exactly those keys."
    )
    data = await _complete(system, user)
    obj = _extract_json(data)
    return {k: str(obj.get(k, "")) for k in required_fields}


async def check_reference(content: dict, vertical: str | None = None) -> dict:
    system = (
        "You are a compliance reviewer for UK employment references. Check the reference "
        "for: discriminatory language, unevidenced opinion stated as fact, and defamation / "
        "data-protection risk. Return STRICT JSON only: "
        '{"ok": bool, "flags": [{"field": str, "issue": str, "severity": "low|medium|high"}], '
        '"rewritten": { field: safer_text }}. '
        "If nothing is wrong, ok=true, flags=[], rewritten={}. No markdown."
    )
    user = f"Reference content (JSON):\n{json.dumps(content)}"
    data = await _complete(system, user)
    obj = _extract_json(data)
    return {
        "ok": bool(obj.get("ok", True)),
        "flags": obj.get("flags", []) or [],
        "rewritten": obj.get("rewritten", {}) or {},
    }


async def synthesise(content: dict, assignment_context: str | None = None, vertical: str | None = None) -> dict:
    p = _profile(vertical)
    system = (
        f"You assess references for {p['sector']}. Assess the evidence against "
        f"{p['framework']}. Judge the reference ONLY against the standards for its own "
        "sector and role — never contrast it against a different profession's framework. "
        "Return STRICT JSON only: "
        '{"competency_map": ' + p["map_keys"] + ", "
        '"risk_score": number 0-100 (0 = no concern, 100 = serious concern), '
        '"summary": one plain-English paragraph }. No markdown.'
    )
    user = (
        f"Sector: {p['sector']}\n"
        f"Assignment context: {assignment_context or 'n/a'}\n"
        f"Reference content (JSON):\n{json.dumps(content)}"
    )
    data = await _complete(system, user)
    obj = _extract_json(data)
    score = obj.get("risk_score")
    try:
        score = max(0.0, min(100.0, float(score)))
    except (TypeError, ValueError):
        score = None
    return {
        "competency_map": obj.get("competency_map", {}),
        "risk_score": score,
        "summary": str(obj.get("summary", "")),
    }


async def share_message(worker_name: str, issuing_org: str) -> dict:
    """A short, professional covering note the worker can email with their reference link."""
    system = (
        "Write a brief, professional covering email from a job candidate sharing a verified "
        "employment reference with a prospective employer. Courteous, 3-4 sentences. Do NOT "
        "include the link (it is appended separately) and do not invent details. "
        'Return STRICT JSON only: {"subject": str, "body": str}. No markdown.'
    )
    user = f"Candidate: {worker_name}. Reference issued by: {issuing_org}."
    data = await _complete(system, user, max_tokens=400)
    obj = _extract_json(data)
    return {
        "subject": str(obj.get("subject") or "Verified employment reference"),
        "body": str(obj.get("body") or ""),
    }
