"""Reference Custody Platform — backend API (Step 3: real auth).

Identity now comes from the verified Supabase login token, not from headers.

  POST /onboarding/org          create an org; the caller becomes its admin
  POST /workers/verify          the logged-in user registers as a verified worker
  POST /references              org member drafts a reference (org from token)
  POST /references/{id}/publish org member publishes -> server-side content hash
  POST /grants                  worker mints the £5 consent link (raw token once)
  GET  /share/{token}           public, token-gated read of the source record (audited)
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import ai, db
from .auth import current_user, require_org_actor, require_worker
from .hashing import content_hash, identity_hash, new_share_token, token_hash
from .swe import check_registration


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    yield
    await db.disconnect()


app = FastAPI(title="Reference Custody Platform API", version="0.3.0", lifespan=lifespan)

_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
class OrgCreateIn(BaseModel):
    name: str
    org_type: str
    vertical: str
    email_domain: str | None = None
    full_name: str  # the admin's display name


class WorkerVerifyIn(BaseModel):
    full_name: str
    vertical: str
    registration_body: str
    registration_number: str
    dbs_certificate_number: str | None = None


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


class AiDraftIn(BaseModel):
    notes: str
    template_id: UUID


class AiCheckIn(BaseModel):
    content: dict


class AiAnalyseIn(BaseModel):
    content: dict
    assignment_context: str | None = None


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


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.get("/health")
async def health():
    async with db.pool().acquire() as c:
        await c.fetchval("select 1")
    return {"ok": True}


@app.get("/me")
async def me(actor=Depends(current_user)):
    """Who am I, per my token — and what identities are attached."""
    async with db.pool().acquire() as c:
        prof = await c.fetchrow(
            "select org_id, role, full_name from profiles where id = $1::uuid", actor["user_id"]
        )
        worker = await c.fetchrow(
            "select id from workers where profile_id = $1::uuid", actor["user_id"]
        )
    return {
        "user_id": actor["user_id"],
        "email": actor["email"],
        "org_id": str(prof["org_id"]) if prof and prof["org_id"] else None,
        "role": prof["role"] if prof else None,
        "worker_id": str(worker["id"]) if worker else None,
    }


@app.get("/templates")
async def list_templates(vertical: str | None = None):
    async with db.pool().acquire() as c:
        if vertical:
            rows = await c.fetch(
                "select id, vertical, name, version, field_schema from reference_templates "
                "where is_active and vertical = $1::vertical_t order by name",
                vertical,
            )
        else:
            rows = await c.fetch(
                "select id, vertical, name, version, field_schema from reference_templates "
                "where is_active order by name"
            )
    return [dict(r) for r in rows]


@app.get("/me/references")
async def my_references(user=Depends(current_user)):
    async with db.pool().acquire() as c:
        prof = await c.fetchrow("select org_id from profiles where id = $1::uuid", user["user_id"])
        worker = await c.fetchrow("select id from workers where profile_id = $1::uuid", user["user_id"])
        out = {"as_worker": [], "as_org": []}
        if worker:
            out["as_worker"] = [dict(r) for r in await c.fetch(
                'select r.id, r.status, r.assignment_context, r.content_hash, '
                'o.name as issuing_org, r.published_at '
                'from "references" r join orgs o on o.id = r.issuing_org_id '
                'where r.worker_id = $1 order by r.created_at desc',
                worker["id"],
            )]
        if prof and prof["org_id"]:
            out["as_org"] = [dict(r) for r in await c.fetch(
                'select r.id, r.status, r.assignment_context, r.content_hash, '
                'w.full_name as worker_name, r.published_at '
                'from "references" r join workers w on w.id = r.worker_id '
                'where r.issuing_org_id = $1 order by r.created_at desc',
                prof["org_id"],
            )]
    return out


@app.post("/onboarding/org", status_code=201)
async def onboarding_org(body: OrgCreateIn, user=Depends(current_user)):
    async with db.pool().acquire() as c:
        async with c.transaction():
            org = await c.fetchrow(
                """
                insert into orgs (name, org_type, vertical, email_domain)
                values ($1, $2::org_type_t, $3::vertical_t, $4)
                returning id
                """,
                body.name, body.org_type, body.vertical, body.email_domain,
            )
            await c.execute(
                """
                insert into profiles (id, org_id, role, full_name, email)
                values ($1::uuid, $2, 'org_admin', $3, $4)
                on conflict (id) do update
                  set org_id = excluded.org_id, role = 'org_admin', full_name = excluded.full_name
                """,
                user["user_id"], org["id"], body.full_name, user["email"] or "unknown@local",
            )
    return {"org_id": str(org["id"]), "role": "org_admin"}


@app.post("/workers/verify", status_code=201)
async def workers_verify(body: WorkerVerifyIn, user=Depends(current_user)):
    check = await check_registration(body.registration_body, body.registration_number)
    idhash = identity_hash(body.registration_body, body.registration_number, body.dbs_certificate_number)
    async with db.pool().acquire() as c:
        try:
            async with c.transaction():
                await c.execute(
                    """
                    insert into profiles (id, org_id, role, full_name, email)
                    values ($1::uuid, null, 'worker', $2, $3)
                    on conflict (id) do nothing
                    """,
                    user["user_id"], body.full_name, user["email"] or "unknown@local",
                )
                row = await c.fetchrow(
                    """
                    insert into workers
                      (profile_id, full_name, vertical, registration_body, registration_number,
                       registration_status, registration_checked_at, dbs_certificate_number, identity_hash)
                    values ($1::uuid, $2, $3::vertical_t, $4::registration_body_t, $5,
                            $6::verification_status_t, $7, $8, $9)
                    returning id, registration_status
                    """,
                    user["user_id"], body.full_name, body.vertical, body.registration_body,
                    body.registration_number, check["status"], _now(),
                    body.dbs_certificate_number, idhash,
                )
        except Exception as e:
            if "workers_registration_body_registration_number_key" in str(e):
                raise HTTPException(409, "worker with this registration already exists")
            if "workers_profile_id_key" in str(e):
                raise HTTPException(409, "this user already has a worker identity")
            raise
    return {"worker_id": str(row["id"]), "registration_status": row["registration_status"]}


@app.post("/references", status_code=201)
async def references_create(body: ReferenceCreateIn, actor=Depends(require_org_actor)):
    org_id = actor["org_id"]
    async with db.pool().acquire() as c:
        org = await c.fetchrow("select email_domain from orgs where id = $1", org_id)
        async with c.transaction():
            ref = await c.fetchrow(
                """
                insert into "references" (worker_id, issuing_org_id, template_id, assignment_context, content)
                values ($1, $2, $3, $4, $5)
                returning id, status
                """,
                body.worker_id, org_id, body.template_id, body.assignment_context, body.content,
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
async def references_publish(reference_id: UUID, actor=Depends(require_org_actor)):
    org_id = actor["org_id"]
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
        missing = [f for f in required if not content.get(f)]
        if missing:
            raise HTTPException(422, {"error": "content missing required fields", "missing": missing})

        chash = content_hash(str(ref["worker_id"]), str(org_id), content)
        await c.execute(
            "update \"references\" set status='published', content_hash=$2, published_at=$3 where id=$1",
            reference_id, chash, _now(),
        )
        # best-effort: attach an AI assessment so the share page can show it.
        # Never block publishing if the AI is unavailable (no key / no credit / error).
        try:
            result = await ai.synthesise(content, None)
            await c.execute(
                'update "references" set competency_map=$2, risk_score=$3, ai_summary=$4 where id=$1',
                reference_id, result["competency_map"], result["risk_score"], result["summary"],
            )
        except Exception:
            pass
    return {"reference_id": str(reference_id), "status": "published", "content_hash": chash}


@app.post("/grants", status_code=201)
async def grants_mint(body: GrantMintIn, worker=Depends(require_worker)):
    worker_id = worker["worker_id"]
    async with db.pool().acquire() as c:
        ref = await c.fetchrow('select worker_id, status from "references" where id = $1', body.reference_id)
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
            worker_id, body.reference_id, thash, body.granted_to_email, body.granted_to_org_id, expires,
        )
    return {"grant_id": str(grant["id"]), "share_token": raw, "expires_at": grant["expires_at"].isoformat()}


@app.post("/ai/draft")
async def ai_draft(body: AiDraftIn, actor=Depends(require_org_actor)):
    async with db.pool().acquire() as c:
        tmpl = await c.fetchrow("select field_schema from reference_templates where id = $1", body.template_id)
    if tmpl is None:
        raise HTTPException(404, "template not found")
    required = (tmpl["field_schema"] or {}).get("required", [])
    try:
        content = await ai.draft_reference(body.notes, required)
    except Exception as e:
        raise HTTPException(502, f"AI drafting failed: {e}")
    return {"content": content}


@app.post("/ai/check")
async def ai_check(body: AiCheckIn, actor=Depends(require_org_actor)):
    try:
        return await ai.check_reference(body.content)
    except Exception as e:
        raise HTTPException(502, f"AI check failed: {e}")


@app.post("/ai/analyse")
async def ai_analyse(body: AiAnalyseIn, actor=Depends(require_org_actor)):
    """Analyse live draft content without saving — lets the issuer iterate pre-publish."""
    try:
        return await ai.synthesise(body.content, body.assignment_context)
    except Exception as e:
        raise HTTPException(502, f"AI analysis failed: {e}")


@app.post("/references/{reference_id}/analyse")
async def references_analyse(reference_id: UUID, actor=Depends(require_org_actor)):
    async with db.pool().acquire() as c:
        ref = await c.fetchrow(
            'select issuing_org_id, content, assignment_context from "references" where id = $1',
            reference_id,
        )
        if ref is None:
            raise HTTPException(404, "reference not found")
        if ref["issuing_org_id"] != actor["org_id"]:
            raise HTTPException(403, "only the issuing org may analyse this reference")
        try:
            result = await ai.synthesise(ref["content"] or {}, ref["assignment_context"])
        except Exception as e:
            raise HTTPException(502, f"AI analysis failed: {e}")
        await c.execute(
            'update "references" set competency_map = $2, risk_score = $3, ai_summary = $4 where id = $1',
            reference_id, result["competency_map"], result["risk_score"], result["summary"],
        )
    return result


@app.get("/share/{share_token}")
async def share_redeem(
    share_token: str,
    request: Request,
    x_email: str | None = Header(default=None),
):
    thash = token_hash(share_token)
    async with db.pool().acquire() as c:
        grant = await c.fetchrow(
            "select id, reference_id, status, expires_at from access_grants where token_hash = $1", thash
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
        await c.execute(
            """
            insert into access_log (grant_id, reference_id, accessed_by_email, action, ip_address)
            values ($1, $2, $3, 'view', $4)
            """,
            grant["id"], grant["reference_id"], x_email, _client_ip(request),
        )
    return {
        "reference_id": str(ref["id"]),
        "worker": {"name": ref["worker_name"], "registration": f'{ref["registration_body"]}:{ref["registration_number"]}'},
        "issuing_org": ref["issuing_org"],
        "assignment_context": ref["assignment_context"],
        "published_at": ref["published_at"].isoformat() if ref["published_at"] else None,
        "content": ref["content"],
        "content_hash": ref["content_hash"],
        "referee": dict(referee) if referee else None,
        "ai": {
            "competency_map": ref["competency_map"],
            "risk_score": float(ref["risk_score"]) if ref["risk_score"] is not None else None,
            "summary": ref["ai_summary"],
        },
    }
