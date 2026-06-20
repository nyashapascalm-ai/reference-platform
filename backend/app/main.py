"""Reference Custody Platform — backend API (Step 2).

Endpoints that make the ledger live end to end:
  POST /workers/verify          register + verify a worker (SWE stubbed)
  POST /references              issuing org drafts a reference
  POST /references/{id}/publish issuing org publishes -> server-side content hash
  POST /grants                  worker mints the £5 consent link (raw token shown once)
  GET  /share/{token}           grantee redeems -> audited read of the source record

DEV AUTH: the acting identity is taken from X-Org-Id / X-Worker-Id headers as a
stand-in. In production these are derived from the verified Supabase JWT, not trusted
from the client. Marked clearly so it is replaced, not forgotten.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from . import db
from .hashing import content_hash, identity_hash, new_share_token, token_hash
from .swe import check_registration


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    yield
    await db.disconnect()


app = FastAPI(title="Reference Custody Platform API", version="0.2.0", lifespan=lifespan)


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
class WorkerVerifyIn(BaseModel):
    full_name: str
    vertical: str
    registration_body: str
    registration_number: str
    dbs_certificate_number: str | None = None
    profile_id: UUID | None = None


class RefereeIn(BaseModel):
    full_name: str
    job_title: str
    work_email: str


class ReferenceCreateIn(BaseModel):
    worker_id: UUID
    template_id: UUID
    assignment_context: str | None = None
    content: dict = Field(default_factory=dict)
    referee: RefereeIn | None = None


class GrantMintIn(BaseModel):
    reference_id: UUID
    granted_to_email: str | None = None
    granted_to_org_id: UUID | None = None
    expires_in_days: int = 14


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _now():
    return datetime.now(timezone.utc)


def _client_ip(request: Request):
    import ipaddress
    host = request.client.host if request.client else None
    try:
        ipaddress.ip_address(host)
        return host
    except (ValueError, TypeError):
        return None


def _require_org(x_org_id: str | None) -> UUID:
    if not x_org_id:
        raise HTTPException(401, "X-Org-Id required (stand-in for verified org identity)")
    try:
        return UUID(x_org_id)
    except ValueError:
        raise HTTPException(400, "X-Org-Id is not a valid uuid")


def _require_worker(x_worker_id: str | None) -> UUID:
    if not x_worker_id:
        raise HTTPException(401, "X-Worker-Id required (stand-in for verified worker identity)")
    try:
        return UUID(x_worker_id)
    except ValueError:
        raise HTTPException(400, "X-Worker-Id is not a valid uuid")


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.get("/health")
async def health():
    async with db.pool().acquire() as c:
        await c.fetchval("select 1")
    return {"ok": True}


@app.post("/workers/verify", status_code=201)
async def workers_verify(body: WorkerVerifyIn):
    check = await check_registration(body.registration_body, body.registration_number)
    idhash = identity_hash(body.registration_body, body.registration_number, body.dbs_certificate_number)
    async with db.pool().acquire() as c:
        try:
            row = await c.fetchrow(
                """
                insert into workers
                  (profile_id, full_name, vertical, registration_body, registration_number,
                   registration_status, registration_checked_at, dbs_certificate_number, identity_hash)
                values ($1, $2, $3::vertical_t, $4::registration_body_t, $5,
                        $6::verification_status_t, $7, $8, $9)
                returning id, registration_status
                """,
                body.profile_id, body.full_name, body.vertical, body.registration_body,
                body.registration_number, check["status"], _now(),
                body.dbs_certificate_number, idhash,
            )
        except Exception as e:
            if "workers_registration_body_registration_number_key" in str(e):
                raise HTTPException(409, "worker with this registration already exists")
            raise
    return {"worker_id": str(row["id"]), "registration_status": row["registration_status"]}


@app.post("/references", status_code=201)
async def references_create(body: ReferenceCreateIn, x_org_id: str | None = Header(default=None)):
    org_id = _require_org(x_org_id)
    async with db.pool().acquire() as c:
        org = await c.fetchrow("select email_domain from orgs where id = $1", org_id)
        if org is None:
            raise HTTPException(404, "issuing org not found")
        async with c.transaction():
            ref = await c.fetchrow(
                """
                insert into "references" (worker_id, issuing_org_id, template_id, assignment_context, content)
                values ($1, $2, $3, $4, $5::jsonb)
                returning id, status
                """,
                body.worker_id, org_id, body.template_id, body.assignment_context,
                body.content,
            )
            referee_out = None
            if body.referee is not None:
                domain = body.referee.work_email.split("@")[-1].lower()
                verified = bool(org["email_domain"]) and domain == str(org["email_domain"]).lower()
                await c.execute(
                    """
                    insert into referees
                      (reference_id, full_name, job_title, work_email, email_domain, domain_verified, auth_method)
                    values ($1, $2, $3, $4, $5, $6, 'email_link')
                    """,
                    ref["id"], body.referee.full_name, body.referee.job_title,
                    body.referee.work_email, domain, verified,
                )
                referee_out = {"email_domain": domain, "domain_verified": verified}
    return {"reference_id": str(ref["id"]), "status": ref["status"], "referee": referee_out}


@app.post("/references/{reference_id}/publish")
async def references_publish(reference_id: UUID, x_org_id: str | None = Header(default=None)):
    org_id = _require_org(x_org_id)
    async with db.pool().acquire() as c:
        ref = await c.fetchrow(
            'select worker_id, issuing_org_id, template_id, content, status from "references" where id = $1',
            reference_id,
        )
        if ref is None:
            raise HTTPException(404, "reference not found")
        if ref["issuing_org_id"] != org_id:
            raise HTTPException(403, "only the issuing org may publish this reference")
        if ref["status"] == "published":
            raise HTTPException(409, "reference already published")

        tmpl = await c.fetchrow("select field_schema from reference_templates where id = $1", ref["template_id"])
        required = (tmpl["field_schema"] or {}).get("required", []) if tmpl else []
        content = ref["content"] or {}
        if isinstance(content, str):
            content = __import__("json").loads(content)
        missing = [f for f in required if not content.get(f)]
        if missing:
            raise HTTPException(422, {"error": "content missing required fields", "missing": missing})

        chash = content_hash(str(ref["worker_id"]), str(org_id), content)
        await c.execute(
            "update \"references\" set status='published', content_hash=$2, published_at=$3 where id=$1",
            reference_id, chash, _now(),
        )
    return {"reference_id": str(reference_id), "status": "published", "content_hash": chash}


@app.post("/grants", status_code=201)
async def grants_mint(body: GrantMintIn, x_worker_id: str | None = Header(default=None)):
    worker_id = _require_worker(x_worker_id)
    async with db.pool().acquire() as c:
        ref = await c.fetchrow(
            'select worker_id, status from "references" where id = $1', body.reference_id
        )
        if ref is None:
            raise HTTPException(404, "reference not found")
        if ref["worker_id"] != worker_id:
            raise HTTPException(403, "a worker may only share references about themselves")
        if ref["status"] != "published":
            raise HTTPException(409, "only a published reference can be shared")

        raw, thash = new_share_token()
        expires = _now() + timedelta(days=max(1, body.expires_in_days))
        grant = await c.fetchrow(
            """
            insert into access_grants
              (worker_id, reference_id, token_hash, granted_to_email, granted_to_org_id, expires_at)
            values ($1, $2, $3, $4, $5, $6)
            returning id, expires_at
            """,
            worker_id, body.reference_id, thash, body.granted_to_email,
            body.granted_to_org_id, expires,
        )
    # raw token returned ONCE; only the hash is stored
    return {"grant_id": str(grant["id"]), "share_token": raw, "expires_at": grant["expires_at"].isoformat()}


@app.get("/share/{share_token}")
async def share_redeem(
    share_token: str,
    request: Request,
    x_org_id: str | None = Header(default=None),
    x_email: str | None = Header(default=None),
):
    thash = token_hash(share_token)
    async with db.pool().acquire() as c:
        grant = await c.fetchrow(
            "select id, reference_id, status, expires_at from access_grants where token_hash = $1",
            thash,
        )
        if grant is None:
            raise HTTPException(404, "invalid share link")
        if grant["status"] == "revoked":
            raise HTTPException(403, "this share link has been revoked")
        if grant["expires_at"] <= _now():
            raise HTTPException(403, "this share link has expired")

        ref = await c.fetchrow(
            """
            select r.id, r.content, r.content_hash, r.assignment_context, r.published_at,
                   r.competency_map, r.risk_score, r.ai_summary,
                   w.full_name as worker_name, w.registration_body, w.registration_number,
                   o.name as issuing_org
            from "references" r
            join workers w on w.id = r.worker_id
            join orgs o on o.id = r.issuing_org_id
            where r.id = $1
            """,
            grant["reference_id"],
        )
        referee = await c.fetchrow(
            "select full_name, job_title, email_domain, domain_verified from referees where reference_id = $1",
            grant["reference_id"],
        )
        org_uuid = UUID(x_org_id) if x_org_id else None
        await c.execute(
            """
            insert into access_log (grant_id, reference_id, accessed_by_org_id, accessed_by_email, action, ip_address)
            values ($1, $2, $3, $4, 'view', $5)
            """,
            grant["id"], grant["reference_id"], org_uuid, x_email,
            _client_ip(request),
        )
    content = ref["content"]
    if isinstance(content, str):
        content = __import__("json").loads(content)
    return {
        "reference_id": str(ref["id"]),
        "worker": {
            "name": ref["worker_name"],
            "registration": f'{ref["registration_body"]}:{ref["registration_number"]}',
        },
        "issuing_org": ref["issuing_org"],
        "assignment_context": ref["assignment_context"],
        "published_at": ref["published_at"].isoformat() if ref["published_at"] else None,
        "content": content,
        "content_hash": ref["content_hash"],
        "referee": dict(referee) if referee else None,
        "ai": {
            "competency_map": ref["competency_map"],
            "risk_score": float(ref["risk_score"]) if ref["risk_score"] is not None else None,
            "summary": ref["ai_summary"],
        },
    }
