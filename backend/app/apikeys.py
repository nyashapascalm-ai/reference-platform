"""Public API keys for organisations.

A key looks like  rfl_live_<43 url-safe chars>.  We store only its SHA-256
hash; the raw value is shown to the admin once. `require_api_org` authenticates
a request by its `Authorization: Bearer rfl_live_...` header, resolves the org,
enforces the `api` plan flag (Growth+), records last_used_at, and returns the
SAME actor shape as auth.require_org_actor so the /v1 handlers can reuse the
existing per-org logic unchanged.
"""
import hashlib
import secrets

from fastapi import Depends, Header, HTTPException

from . import db, billing

KEY_PREFIX = "rfl_live_"


def generate_key() -> tuple[str, str, str]:
    """Return (raw_key, key_hash, display_prefix). Raw is shown once."""
    raw = KEY_PREFIX + secrets.token_urlsafe(32)
    return raw, hash_key(raw), raw[:16]


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def require_api_org(authorization: str | None = Header(default=None)) -> dict:
    """Authenticate an API request by its bearer API key and return an actor
    dict: {api_key_id, org_id, role, via_api: True}. Raises 401/403/402 as
    appropriate. The `role` is reported as 'api' (full org-write scope)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing API key (Authorization: Bearer rfl_live_...)")
    raw = authorization.split(" ", 1)[1].strip()
    if not raw.startswith(KEY_PREFIX):
        raise HTTPException(401, "invalid API key")
    kh = hash_key(raw)
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "select k.id, k.org_id, k.revoked_at, "
            "       coalesce(b.plan, 'free') as plan, "
            "       o.is_suspended, o.archived_at "
            "from api_keys k "
            "join orgs o on o.id = k.org_id "
            "left join billing_customers b on b.org_id = k.org_id "
            "where k.key_hash = $1",
            kh,
        )
        if row is None:
            raise HTTPException(401, "invalid API key")
        if row["revoked_at"] is not None:
            raise HTTPException(401, "this API key has been revoked")
        if row["is_suspended"]:
            raise HTTPException(403, "your organisation's access has been suspended")
        if row["archived_at"] is not None:
            raise HTTPException(403, "your organisation is no longer active")
        if not billing.features(row["plan"]).get("api"):
            raise HTTPException(
                402,
                "The API is available on the Growth and Business plans. "
                "Upgrade your plan to use the API.",
            )
        # best-effort last-used stamp
        await c.execute("update api_keys set last_used_at = now() where id = $1", row["id"])
    return {
        "api_key_id": str(row["id"]),
        "org_id": row["org_id"],
        "role": "api",
        "via_api": True,
        "user_id": None,
        "email": None,
    }
