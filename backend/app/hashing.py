"""Deterministic hashing for the custody ledger.

The content hash is what makes a published reference tamper-evident: it binds the
exact payload to the worker and issuing org. It is computed server-side at publish
time and never trusted from the client.
"""
import hashlib
import json
import secrets


def canonical(content: dict) -> str:
    """Stable JSON encoding: sorted keys, no incidental whitespace."""
    return json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(worker_id: str, issuing_org_id: str, content: dict) -> str:
    """Tamper-evident hash bound to worker + issuer + payload."""
    basis = f"{worker_id}|{issuing_org_id}|{canonical(content)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def identity_hash(registration_body: str, registration_number: str, dbs: str | None) -> str:
    """Tamper-evident binding of a worker's verified anchors."""
    basis = f"{registration_body}|{registration_number}|{dbs or ''}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def new_share_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). The raw token is shown to the worker ONCE;
    only the hash is ever stored."""
    raw = secrets.token_urlsafe(24)
    return raw, token_hash(raw)


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
