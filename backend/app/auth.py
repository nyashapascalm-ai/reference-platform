"""Authentication: verify the Supabase login token and resolve identity."""
import os
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException

from . import db


def decode_token(token: str) -> dict:
    secret = os.environ["SUPABASE_JWT_SECRET"]
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
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
            "select id, org_id, role from profiles where id = $1::uuid", user["user_id"]
        )
    if row is None or row["org_id"] is None or row["role"] == "worker":
        raise HTTPException(403, "not a member of any organisation")
    return {"profile_id": row["id"], "org_id": row["org_id"], "role": row["role"], **user}


async def require_worker(user: dict = Depends(current_user)) -> dict:
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            """
            select w.id from workers w
            join profiles p on p.id = w.profile_id
            where p.id = $1::uuid
            """,
            user["user_id"],
        )
    if row is None:
        raise HTTPException(403, "no worker identity for this user")
    return {"worker_id": row["id"], **user}
