"""Authentication: verify the Supabase login token and resolve identity.

Supports both Supabase token styles:
  - HS256  : legacy shared JWT secret (SUPABASE_JWT_SECRET)
  - ES256/RS256 : new asymmetric signing keys, verified via the project's JWKS
                  (SUPABASE_URL -> /auth/v1/.well-known/jwks.json)
The token header's `alg` selects the path, so either works with no config change.
"""
import os
from uuid import UUID

import jwt
from jwt import PyJWKClient
from fastapi import Depends, Header, HTTPException

from . import db

_jwks_client = None


def _jwks() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        url = os.environ.get("SUPABASE_JWKS_URL")
        if not url:
            base = os.environ["SUPABASE_URL"].rstrip("/")
            url = f"{base}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(url)
    return _jwks_client


def decode_token(token: str) -> dict:
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
        if alg == "HS256":
            secret = os.environ["SUPABASE_JWT_SECRET"]
            return jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
        key = _jwks().get_signing_key_from_jwt(token).key
        return jwt.decode(token, key, algorithms=["ES256", "RS256"], audience="authenticated")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "login session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "invalid login token")


async def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    claims = decode_token(authorization.split(" ", 1)[1].strip())
    uid = claims.get("sub")
    if not uid:
        raise HTTPException(401, "token has no subject")
    return {"user_id": uid, "email": claims.get("email")}


async def require_org_actor(user: dict = Depends(current_user)) -> dict:
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "select id, org_id, role, is_locked from profiles where id = $1::uuid", user["user_id"]
        )
    if row is None or row["org_id"] is None or row["role"] == "worker":
        raise HTTPException(403, "not a member of any organisation")
    if row["is_locked"]:
        raise HTTPException(403, "your account has been locked by an administrator")
    return {"profile_id": row["id"], "org_id": row["org_id"], "role": row["role"], **user}


async def require_worker(user: dict = Depends(current_user)) -> dict:
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "select w.id from workers w join profiles p on p.id = w.profile_id "
            "where p.id = $1::uuid",
            user["user_id"],
        )
    if row is None:
        raise HTTPException(403, "no worker identity for this user")
    return {"worker_id": row["id"], **user}
