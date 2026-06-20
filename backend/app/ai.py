"""AI core — the differentiators, powered by the Anthropic API.

  draft_reference  rough manager notes      -> structured, template-compliant content
  check_reference  a drafted reference      -> fairness / defamation flags + safe rewrite
  synthesise       a published reference     -> PCF/KSS competency map, risk score, summary

Each function asks Claude for STRICT JSON and parses it defensively. The model is
overridable with ANTHROPIC_MODEL; the API key comes from ANTHROPIC_API_KEY.
`_complete` is module-level so it can be patched in tests without network access.
"""
import json
import os

from anthropic import AsyncAnthropic

_client: AsyncAnthropic | None = None
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


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


async def draft_reference(notes: str, required_fields: list[str]) -> dict:
    system = (
        "You write UK social-work employment references. Produce only factual, "
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


async def check_reference(content: dict) -> dict:
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


async def synthesise(content: dict, assignment_context: str | None = None) -> dict:
    system = (
        "You assess UK children's social-work references. Map the evidence to the "
        "Professional Capabilities Framework (PCF) and the Knowledge & Skills Statements (KSS). "
        "Return STRICT JSON only: "
        '{"competency_map": { "PCF": [..], "KSS": [..] }, '
        '"risk_score": number 0-100 (0 = no concern, 100 = serious concern), '
        '"summary": one plain-English paragraph }. No markdown.'
    )
    user = (
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
