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
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import ai, db, email
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


class ShareMessageIn(BaseModel):
    worker_name: str | None = None
    issuing_org: str | None = None


class ViewerIn(BaseModel):
    name: str
    email: str
    organisation: str | None = None


class RequestCodeIn(BaseModel):
    email: str


class VerifyCodeIn(BaseModel):
    email: str
    code: str
    name: str | None = None
    organisation: str | None = None


class ConfirmIn(BaseModel):
    name: str | None = None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _now():
    return datetime.now(timezone.utc)


def _mask_email(addr: str) -> str:
    try:
        local, domain = addr.split("@", 1)
        shown = local[0] if local else ""
        return f"{shown}{'•' * max(1, len(local) - 1)}@{domain}"
    except Exception:
        return "•••"


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
                'o.name as issuing_org, r.published_at, '
                'coalesce(a.opens, 0) as opens, a.last_opened '
                'from "references" r join orgs o on o.id = r.issuing_org_id '
                'left join (select reference_id, count(*) as opens, max(accessed_at) as last_opened '
                '           from access_log group by reference_id) a on a.reference_id = r.id '
                'where r.worker_id = $1 order by r.created_at desc',
                worker["id"],
            )]
        if prof and prof["org_id"]:
            out["as_org"] = [dict(r) for r in await c.fetch(
                'select r.id, r.status, r.assignment_context, r.content_hash, '
                'w.full_name as worker_name, r.published_at, '
                'coalesce(a.opens, 0) as opens, a.last_opened '
                'from "references" r join workers w on w.id = r.worker_id '
                'left join (select reference_id, count(*) as opens, max(accessed_at) as last_opened '
                '           from access_log group by reference_id) a on a.reference_id = r.id '
                'where r.issuing_org_id = $1 order by r.created_at desc',
                prof["org_id"],
            )]
    return out


@app.get("/references/{reference_id}/activity")
async def reference_activity(reference_id: UUID, user=Depends(current_user)):
    async with db.pool().acquire() as c:
        ref = await c.fetchrow('select worker_id, issuing_org_id from "references" where id = $1', reference_id)
        if ref is None:
            raise HTTPException(404, "reference not found")
        prof = await c.fetchrow("select org_id from profiles where id = $1::uuid", user["user_id"])
        worker = await c.fetchrow("select id from workers where profile_id = $1::uuid", user["user_id"])
        allowed = (worker and worker["id"] == ref["worker_id"]) or (prof and prof["org_id"] == ref["issuing_org_id"])
        if not allowed:
            raise HTTPException(403, "not permitted to view this activity")
        rows = await c.fetch(
            "select accessed_by_name, accessed_by_email, viewer_org, verified, accessed_at, action "
            "from access_log where reference_id = $1 order by accessed_at desc",
            reference_id,
        )
    return [dict(r) for r in rows]


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
        # best-effort: ask the named referee to confirm authorship (needs email configured)
        try:
            await _send_referee_confirmation(c, reference_id)
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


@app.post("/ai/share-message")
async def ai_share_message(body: ShareMessageIn, user=Depends(current_user)):
    """A covering email the worker can send with their share link. Never fails —
    falls back to a clean template if the AI is unavailable."""
    try:
        return await ai.share_message(body.worker_name or "the candidate",
                                      body.issuing_org or "a previous employer")
    except Exception:
        return {
            "subject": "Verified employment reference",
            "body": ("Hello,\n\nI'd like to share a verified employment reference with you. "
                     "It was issued directly by my previous employer and can be viewed securely "
                     "via the link below.\n\nKind regards"),
        }


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


async def _validate_grant(c, share_token: str):
    grant = await c.fetchrow(
        "select id, reference_id, status, expires_at from access_grants where token_hash = $1",
        token_hash(share_token),
    )
    if grant is None:
        raise HTTPException(404, "invalid share link")
    if grant["status"] == "revoked":
        raise HTTPException(403, "this share link has been revoked")
    if grant["expires_at"] <= _now():
        raise HTTPException(403, "this share link has expired")
    return grant


async def _send_referee_confirmation(c, reference_id) -> bool:
    ref = await c.fetchrow(
        'select w.full_name as worker_name, o.name as issuing_org '
        'from "references" r join workers w on w.id = r.worker_id '
        'join orgs o on o.id = r.issuing_org_id where r.id = $1',
        reference_id,
    )
    referee = await c.fetchrow(
        "select id, full_name, work_email, confirmed_at from referees where reference_id = $1",
        reference_id,
    )
    if ref is None or referee is None or referee["confirmed_at"] is not None:
        return False
    raw, thash = new_share_token()
    await c.execute(
        "update referees set confirm_token_hash = $2, confirm_sent_at = now() where id = $1",
        referee["id"], thash,
    )
    base = os.environ.get("PUBLIC_APP_URL", "https://reference-platform.vercel.app").rstrip("/")
    link = f"{base}/confirm/{raw}"
    html = (
        f"<p>Hello {referee['full_name']},</p>"
        f"<p>{ref['issuing_org']} has recorded an employment reference for "
        f"<b>{ref['worker_name']}</b> and has named you as the referee.</p>"
        f"<p>Please confirm that you provided this reference:</p>"
        f"<p><a href='{link}'>Confirm this reference</a></p>"
        f"<p>If you did not provide this reference, you can ignore this email.</p>"
    )
    return await email.send_email(str(referee["work_email"]), "Please confirm an employment reference", html)


async def _notify_worker_opened(c, reference_id, viewer_name, viewer_email, viewer_org, verified: bool):
    """Email the worker the first time a given viewer opens their reference."""
    try:
        seen = await c.fetchval(
            "select count(*) from access_log where reference_id = $1 and accessed_by_email = $2",
            reference_id, viewer_email,
        )
        if seen and seen > 1:
            return  # this viewer has opened before — don't notify again
        row = await c.fetchrow(
            'select p.email as worker_email, w.full_name as worker_name '
            'from "references" r join workers w on w.id = r.worker_id '
            'join profiles p on p.id = w.profile_id where r.id = $1',
            reference_id,
        )
        if not row or not row["worker_email"]:
            return
        who = viewer_name or viewer_email or "someone"
        org = f" · {viewer_org}" if viewer_org else ""
        tick = " (identity verified)" if verified else ""
        html = (
            f"<p>Hello {row['worker_name']},</p>"
            f"<p>Your verified reference was just viewed by <b>{who}</b>{org}{tick}.</p>"
            f"<p>You can see every view in your portal.</p>"
        )
        await email.send_email(str(row["worker_email"]), "Your reference was viewed", html)
    except Exception:
        pass


@app.post("/references/{reference_id}/request-referee-confirmation")
async def request_referee_confirmation(reference_id: UUID, actor=Depends(require_org_actor)):
    async with db.pool().acquire() as c:
        ref = await c.fetchrow('select issuing_org_id from "references" where id = $1', reference_id)
        if ref is None:
            raise HTTPException(404, "reference not found")
        if ref["issuing_org_id"] != actor["org_id"]:
            raise HTTPException(403, "only the issuing org may request confirmation")
        sent = await _send_referee_confirmation(c, reference_id)
    return {"sent": bool(sent)}


@app.get("/confirm/{token}")
async def confirm_preview(token: str):
    async with db.pool().acquire() as c:
        referee = await c.fetchrow(
            "select full_name, reference_id, confirmed_at from referees where confirm_token_hash = $1",
            token_hash(token),
        )
        if referee is None:
            raise HTTPException(404, "invalid or expired confirmation link")
        ref = await c.fetchrow(
            'select w.full_name as worker_name, o.name as issuing_org, r.assignment_context '
            'from "references" r join workers w on w.id = r.worker_id '
            'join orgs o on o.id = r.issuing_org_id where r.id = $1',
            referee["reference_id"],
        )
    return {
        "referee_name": referee["full_name"],
        "worker_name": ref["worker_name"] if ref else None,
        "issuing_org": ref["issuing_org"] if ref else None,
        "assignment_context": ref["assignment_context"] if ref else None,
        "already_confirmed": referee["confirmed_at"] is not None,
    }


@app.post("/confirm/{token}")
async def confirm_submit(token: str, body: ConfirmIn, request: Request):
    async with db.pool().acquire() as c:
        referee = await c.fetchrow(
            "select id, confirmed_at from referees where confirm_token_hash = $1",
            token_hash(token),
        )
        if referee is None:
            raise HTTPException(404, "invalid or expired confirmation link")
        if referee["confirmed_at"] is None:
            await c.execute(
                "update referees set confirmed_at = now(), confirmed_name = $2, ip_address = $3 where id = $1",
                referee["id"], body.name, _client_ip(request),
            )
    return {"confirmed": True}


@app.get("/share/{share_token}")
async def share_preview(share_token: str):
    """Validate the link and name the worker — but reveal nothing and log nothing
    until the viewer identifies themselves (POST) or verifies a code."""
    async with db.pool().acquire() as c:
        grant = await _validate_grant(c, share_token)
        pinned = await c.fetchval("select granted_to_email from access_grants where id = $1", grant["id"])
        ref = await c.fetchrow(
            'select w.full_name as worker_name, o.name as issuing_org '
            'from "references" r join workers w on w.id = r.worker_id '
            'join orgs o on o.id = r.issuing_org_id where r.id = $1',
            grant["reference_id"],
        )
    return {
        "valid": True,
        "requires_identity": True,
        "pinned": bool(pinned),
        "recipient_hint": _mask_email(str(pinned)) if pinned else None,
        "worker_name": ref["worker_name"] if ref else None,
        "issuing_org": ref["issuing_org"] if ref else None,
    }


@app.post("/share/{share_token}/request-code")
async def share_request_code(share_token: str, body: RequestCodeIn):
    """Email a one-time code to the recipient inbox so the viewer can prove they control it."""
    email_in = body.email.strip()
    async with db.pool().acquire() as c:
        grant = await _validate_grant(c, share_token)
        pinned = await c.fetchval("select granted_to_email from access_grants where id = $1", grant["id"])
        if pinned and email_in.lower() != str(pinned).lower():
            raise HTTPException(403, "this link was sent to a different email address")
        code = f"{secrets.randbelow(1_000_000):06d}"
        await c.execute(
            "insert into share_codes (grant_id, email, code_hash, expires_at) values ($1, $2, $3, $4)",
            grant["id"], email_in, token_hash(code), _now() + timedelta(minutes=10),
        )
    sent = await email.send_email(
        email_in,
        "Your reference access code",
        f"<p>Your one-time code to view the verified reference is "
        f"<b style='font-size:20px;letter-spacing:2px'>{code}</b>.</p>"
        f"<p>It expires in 10 minutes. If you didn't request this, you can ignore this email.</p>",
    )
    return {"sent": bool(sent)}


@app.post("/share/{share_token}/verify")
async def share_verify_code(share_token: str, body: VerifyCodeIn, request: Request):
    """Check the one-time code, log a verified access, and reveal the reference."""
    email_in = body.email.strip()
    async with db.pool().acquire() as c:
        grant = await _validate_grant(c, share_token)
        rec = await c.fetchrow(
            "select id, code_hash, expires_at, used_at from share_codes "
            "where grant_id = $1 and email = $2 order by created_at desc limit 1",
            grant["id"], email_in,
        )
        if (rec is None or rec["used_at"] is not None or rec["expires_at"] <= _now()
                or rec["code_hash"] != token_hash(body.code.strip())):
            raise HTTPException(403, "invalid or expired code")
        await c.execute("update share_codes set used_at = now() where id = $1", rec["id"])
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
            "select full_name, job_title, email_domain, domain_verified, confirmed_at, confirmed_name from referees where reference_id = $1",
            grant["reference_id"],
        )
        await c.execute(
            """
            insert into access_log
              (grant_id, reference_id, accessed_by_name, accessed_by_email, viewer_org, verified, action, ip_address)
            values ($1, $2, $3, $4, $5, true, 'view', $6)
            """,
            grant["id"], grant["reference_id"], body.name or email_in, email_in,
            body.organisation, _client_ip(request),
        )
        await _notify_worker_opened(c, grant["reference_id"], body.name, email_in, body.organisation, True)
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


@app.post("/share/{share_token}")
async def share_redeem(share_token: str, viewer: ViewerIn, request: Request):
    """The viewer identifies themselves; we log who/when, then reveal the reference."""
    async with db.pool().acquire() as c:
        grant = await _validate_grant(c, share_token)
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
            "select full_name, job_title, email_domain, domain_verified, confirmed_at, confirmed_name from referees where reference_id = $1",
            grant["reference_id"],
        )
        await c.execute(
            """
            insert into access_log
              (grant_id, reference_id, accessed_by_name, accessed_by_email, viewer_org, action, ip_address)
            values ($1, $2, $3, $4, $5, 'view', $6)
            """,
            grant["id"], grant["reference_id"], viewer.name, viewer.email,
            viewer.organisation, _client_ip(request),
        )
        await _notify_worker_opened(c, grant["reference_id"], viewer.name, viewer.email, viewer.organisation, False)
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
