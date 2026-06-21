"""Reffolio — backend API (Step 3: real auth).

Identity now comes from the verified Supabase login token, not from headers.

  POST /onboarding/org          create an org; the caller becomes its admin
  POST /workers/verify          the logged-in user registers as a verified worker
  POST /references              org member drafts a reference (org from token)
  POST /references/{id}/publish org member publishes -> server-side content hash
  POST /grants                  worker mints the £5 consent link (raw token once)
  GET  /share/{token}           public, token-gated read of the source record (audited)
"""
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import ai, billing, db, email, swe
from .auth import current_user, require_org_actor, require_worker
from .hashing import content_hash, identity_hash, new_share_token, token_hash
from .swe import check_registration


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    yield
    await db.disconnect()


app = FastAPI(title="Reffolio API", version="0.3.0", lifespan=lifespan)


async def require_org_admin(actor=Depends(require_org_actor)) -> dict:
    if actor["role"] != "org_admin":
        raise HTTPException(403, "this action requires an organisation admin")
    return actor


async def require_super_admin(user=Depends(current_user)) -> dict:
    admins = [e.strip().lower() for e in os.environ.get("SUPER_ADMIN_EMAILS", "").split(",") if e.strip()]
    if not admins or (user.get("email") or "").lower() not in admins:
        raise HTTPException(403, "super admin only")
    return user



_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
_wildcard = _origins == ["*"] or not _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=not _wildcard,
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


class InviteIn(BaseModel):
    email: str
    title: str | None = None
    grant_admin: bool = False


class SweImportIn(BaseModel):
    csv: str


class CheckoutIn(BaseModel):
    plan: str


class CreditsIn(BaseModel):
    quantity: int = 100


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


@app.post("/admin/swe-register/import")
async def swe_register_import(body: SweImportIn, x_import_token: str | None = Header(default=None)):
    """Upsert SWE register rows from an official employer CSV export.
    Gated by the SWE_IMPORT_TOKEN secret (sent as X-Import-Token)."""
    secret = os.environ.get("SWE_IMPORT_TOKEN")
    if not secret:
        raise HTTPException(503, "import is not configured")
    if x_import_token != secret:
        raise HTTPException(403, "invalid import token")
    rows = swe.parse_csv(body.csv)
    if not rows:
        raise HTTPException(422, "no rows parsed — check the CSV has a header row with a registration number column")
    async with db.pool().acquire() as c:
        async with c.transaction():
            for r in rows:
                await c.execute(
                    "insert into swe_register (registration_number, registered_name, status, registered_until, town, updated_at) "
                    "values ($1, $2, $3, $4, $5, now()) "
                    "on conflict (registration_number) do update set "
                    "registered_name = excluded.registered_name, status = excluded.status, "
                    "registered_until = excluded.registered_until, town = excluded.town, updated_at = now()",
                    r["number"], r["name"], r["status"], r["until"], r["town"],
                )
    return {"imported": len(rows)}


# ---- Billing ----
_APP_URL = os.environ.get("PUBLIC_APP_URL", "https://reference-platform.vercel.app").rstrip("/")


@app.get("/billing/me")
async def billing_me(actor=Depends(require_org_actor)):
    async with db.pool().acquire() as c:
        row = await billing.get_billing(c, actor["org_id"])
        bal = await billing.credits_balance(c, actor["org_id"])
        used = await billing.seats_used(c, actor["org_id"])
    return {
        "plan": row["plan"],
        "status": row["status"],
        "seats": row["seats"],
        "seats_used": used,
        "credits": bal,
        "features": billing.features(row["plan"]),
        "current_period_end": row["current_period_end"].isoformat() if row["current_period_end"] else None,
        "configured": billing.configured(),
        "enforced": billing.enforce(),
    }


@app.post("/billing/checkout")
async def billing_checkout(body: CheckoutIn, actor=Depends(require_org_admin)):
    if not billing.configured():
        raise HTTPException(503, "billing is not configured")
    price = billing.plan_price(body.plan)
    if not price:
        raise HTTPException(400, "unknown or unpriced plan")
    async with db.pool().acquire() as c:
        org = await c.fetchrow("select name from orgs where id = $1", actor["org_id"])
        customer = await billing.get_or_create_customer(c, actor["org_id"], org["name"], actor["email"])
    url = billing.checkout_subscription(
        customer, price,
        f"{_APP_URL}/dashboard?billing=success",
        f"{_APP_URL}/dashboard?billing=cancelled",
        actor["org_id"],
    )
    return {"url": url}


@app.post("/billing/credits/checkout")
async def billing_credits_checkout(body: CreditsIn, actor=Depends(require_org_admin)):
    if not billing.configured():
        raise HTTPException(503, "billing is not configured")
    price = os.environ.get("STRIPE_PRICE_CREDITS")
    if not price:
        raise HTTPException(400, "credit pricing is not configured")
    qty = max(1, int(body.quantity))
    async with db.pool().acquire() as c:
        org = await c.fetchrow("select name from orgs where id = $1", actor["org_id"])
        customer = await billing.get_or_create_customer(c, actor["org_id"], org["name"], actor["email"])
    url = billing.checkout_credits(
        customer, price, qty,
        f"{_APP_URL}/dashboard?billing=credits",
        f"{_APP_URL}/dashboard?billing=cancelled",
        actor["org_id"],
    )
    return {"url": url}


@app.post("/billing/portal")
async def billing_portal(actor=Depends(require_org_admin)):
    if not billing.configured():
        raise HTTPException(503, "billing is not configured")
    async with db.pool().acquire() as c:
        row = await billing.get_billing(c, actor["org_id"])
        if not row["stripe_customer_id"]:
            org = await c.fetchrow("select name from orgs where id = $1", actor["org_id"])
            cust = await billing.get_or_create_customer(c, actor["org_id"], org["name"], actor["email"])
        else:
            cust = row["stripe_customer_id"]
    url = billing.billing_portal(cust, f"{_APP_URL}/dashboard")
    return {"url": url}


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(503, "webhook is not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        import stripe
        stripe.Webhook.construct_event(payload, sig, secret)  # verifies signature (raises if invalid)
    except Exception:
        raise HTTPException(400, "invalid signature")
    try:
        event = json.loads(payload.decode("utf-8"))  # plain dict, version-agnostic
    except Exception:
        raise HTTPException(400, "invalid payload")
    try:
        async with db.pool().acquire() as c:
            await billing.handle_event(event, c)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        app.state.last_webhook_error = {"type": event.get("type"), "error": f"{e.__class__.__name__}: {e}", "trace": tb[-1500:]}
        print("WEBHOOK_ERROR", event.get("type"), tb, flush=True)
        # return 200 so Stripe stops retrying a poison event; we've logged it
        return {"received": True, "handled": False}
    return {"received": True, "handled": True}


@app.get("/billing/_debug")
async def billing_debug(actor=Depends(require_org_admin)):
    return getattr(app.state, "last_webhook_error", {"error": None})


# ---- Super admin (Reffolio staff; gated by SUPER_ADMIN_EMAILS) ----
@app.get("/admin/overview")
async def admin_overview(user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        orgs = await c.fetchval("select count(*) from orgs")
        workers = await c.fetchval("select count(*) from workers")
        refs_total = await c.fetchval('select count(*) from "references"')
        refs_published = await c.fetchval("select count(*) from \"references\" where status = 'published'")
        members = await c.fetchval("select count(*) from profiles where org_id is not null")
        roles = await c.fetch("select role::text as role, count(*) as n from profiles group by role")
        active_plans = await c.fetch(
            "select plan, count(*) as n from billing_customers where status = 'active' group by plan"
        )
        all_plans = await c.fetch("select plan, status, count(*) as n from billing_customers group by plan, status")
        credits = await c.fetchval("select coalesce(sum(delta),0) from billing_credits")
        swe_rows = await c.fetchval("select count(*) from swe_register")
        recent_orgs = await c.fetch("select count(*) from orgs where created_at > now() - interval '7 days'")
    mrr = sum(billing.PLAN_PRICE_GBP.get(r["plan"], 0) * r["n"] for r in active_plans)
    return {
        "totals": {
            "orgs": orgs, "workers": workers, "org_members": members,
            "references": refs_total, "references_published": refs_published,
            "swe_register_rows": swe_rows, "credits_outstanding": int(credits or 0),
            "new_orgs_7d": recent_orgs[0]["count"] if recent_orgs else 0,
        },
        "roles": {r["role"]: r["n"] for r in roles},
        "active_subscriptions": {r["plan"]: r["n"] for r in active_plans},
        "plan_status": [dict(r) for r in all_plans],
        "estimated_mrr_gbp": mrr,
        "estimated_arr_gbp": mrr * 12,
    }


@app.get("/admin/orgs")
async def admin_orgs(include_archived: bool = False, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            """
            select o.id, o.name, o.org_type::text as org_type, o.vertical::text as vertical,
                   o.is_active, o.is_suspended, o.archived_at, o.created_at,
                   coalesce(b.plan, 'free') as plan,
                   coalesce(b.status, 'inactive') as status,
                   coalesce(b.seats, 2) as seats,
                   b.current_period_end,
                   (select count(*) from profiles p where p.org_id = o.id) as members,
                   (select count(*) from "references" r where r.issuing_org_id = o.id) as refs
            from orgs o
            left join billing_customers b on b.org_id = o.id
            where ($1 or o.archived_at is null)
            order by o.created_at desc
            """,
            include_archived,
        )
    return {"orgs": [dict(r) for r in rows]}


@app.get("/admin/analytics")
async def admin_analytics(user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        active = await c.fetchval("select count(*) from billing_customers where status = 'active'")
        canceled = await c.fetchval("select count(*) from billing_customers where status = 'canceled'")
        past_due = await c.fetchval("select count(*) from billing_customers where status = 'past_due'")
        suspended = await c.fetchval("select count(*) from orgs where is_suspended = true and archived_at is null")
        archived = await c.fetchval("select count(*) from orgs where archived_at is not null")
        growth = await c.fetchrow(
            """
            select count(*) filter (where created_at > now() - interval '7 days')  as d7,
                   count(*) filter (where created_at > now() - interval '30 days') as d30,
                   count(*) filter (where created_at > now() - interval '90 days') as d90
            from orgs where archived_at is null
            """
        )
        seats = await c.fetchrow(
            """
            select coalesce(sum(b.seats), 0) as subscribed,
                   coalesce(sum((select count(*) from profiles p where p.org_id = b.org_id)), 0) as used
            from billing_customers b where b.status = 'active'
            """
        )
        cancels_30 = await c.fetchval(
            "select count(distinct org_id) from billing_events "
            "where status = 'canceled' and created_at > now() - interval '30 days'"
        )
    base = (active or 0) + (canceled or 0)
    churn_rate = round((canceled or 0) / base, 4) if base else 0.0
    sub = seats["subscribed"] or 0
    used = seats["used"] or 0
    return {
        "subscriptions": {"active": active, "canceled": canceled, "past_due": past_due},
        "lifecycle": {"suspended": suspended, "archived": archived},
        "growth": {"new_7d": growth["d7"], "new_30d": growth["d30"], "new_90d": growth["d90"]},
        "seats": {"subscribed": sub, "used": used,
                  "utilisation": round(used / sub, 4) if sub else 0.0},
        "churn": {"rate": churn_rate, "cancels_30d": cancels_30 or 0,
                  "note": "Snapshot churn = cancelled \u00f7 (active + cancelled). Trended churn builds from now via billing events."},
    }


@app.get("/admin/report")
async def admin_report(user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            """
            select o.id, o.name, o.org_type::text as org_type, o.vertical::text as vertical,
                   o.created_at, o.is_suspended, o.archived_at,
                   coalesce(b.plan, 'free') as plan, coalesce(b.status, 'inactive') as status,
                   coalesce(b.seats, 0) as seats, b.current_period_end,
                   (select count(*) from profiles p where p.org_id = o.id) as members,
                   (select count(*) from "references" r where r.issuing_org_id = o.id) as refs,
                   (select count(*) from "references" r where r.issuing_org_id = o.id and r.status = 'published') as published,
                   (select max(created_at) from "references" r where r.issuing_org_id = o.id) as last_reference_at
            from orgs o
            left join billing_customers b on b.org_id = o.id
            order by o.created_at desc
            """
        )
    return {"rows": [dict(r) for r in rows], "generated_at": _now().isoformat()}


@app.post("/admin/orgs/{org_id}/suspend")
async def admin_suspend_org(org_id: UUID, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        r = await c.fetchrow("update orgs set is_suspended = true where id = $1 returning id", org_id)
    if not r:
        raise HTTPException(404, "organisation not found")
    return {"suspended": True}


@app.post("/admin/orgs/{org_id}/unsuspend")
async def admin_unsuspend_org(org_id: UUID, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        r = await c.fetchrow("update orgs set is_suspended = false where id = $1 returning id", org_id)
    if not r:
        raise HTTPException(404, "organisation not found")
    return {"suspended": False}


@app.post("/admin/orgs/{org_id}/archive")
async def admin_archive_org(org_id: UUID, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        r = await c.fetchrow("update orgs set archived_at = now() where id = $1 returning id", org_id)
    if not r:
        raise HTTPException(404, "organisation not found")
    return {"archived": True}


@app.post("/admin/orgs/{org_id}/unarchive")
async def admin_unarchive_org(org_id: UUID, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        r = await c.fetchrow("update orgs set archived_at = null where id = $1 returning id", org_id)
    if not r:
        raise HTTPException(404, "organisation not found")
    return {"archived": False}


@app.post("/admin/orgs/{org_id}/cancel-subscription")
async def admin_cancel_subscription(org_id: UUID, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        b = await c.fetchrow("select stripe_subscription_id from billing_customers where org_id = $1", org_id)
    stripe_done = False
    sub_id = b["stripe_subscription_id"] if b else None
    if sub_id and billing.configured():
        try:
            import stripe
            billing._init()
            stripe.Subscription.delete(sub_id)
            stripe_done = True
        except Exception as e:
            app.state.last_admin_error = f"stripe cancel: {e}"
    async with db.pool().acquire() as c:
        await c.execute(
            "update billing_customers set plan='free', status='canceled', updated_at=now() where org_id=$1",
            org_id,
        )
        await c.execute("insert into billing_events (org_id, status, plan) values ($1, 'canceled', 'free')", org_id)
    return {"canceled": True, "stripe_canceled": stripe_done}


class ConfirmDelete(BaseModel):
    confirm_name: str


@app.delete("/admin/orgs/{org_id}")
async def admin_delete_org(org_id: UUID, body: ConfirmDelete, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        org = await c.fetchrow("select name from orgs where id = $1", org_id)
        if not org:
            raise HTTPException(404, "organisation not found")
        if (body.confirm_name or "").strip() != org["name"]:
            raise HTTPException(400, "the name you typed does not match this organisation")
        async with c.transaction():
            await c.execute('delete from "references" where issuing_org_id = $1', org_id)
            await c.execute("delete from org_invites where org_id = $1", org_id)
            await c.execute("delete from billing_credits where org_id = $1", org_id)
            await c.execute("delete from billing_customers where org_id = $1", org_id)
            await c.execute("delete from billing_events where org_id = $1", org_id)
            await c.execute("update profiles set org_id = null where org_id = $1", org_id)
            await c.execute("delete from orgs where id = $1", org_id)
    return {"deleted": True}


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
    admins = [e.strip().lower() for e in os.environ.get("SUPER_ADMIN_EMAILS", "").split(",") if e.strip()]
    is_super = bool(admins) and (actor.get("email") or "").lower() in admins
    return {
        "user_id": actor["user_id"],
        "email": actor["email"],
        "org_id": str(prof["org_id"]) if prof and prof["org_id"] else None,
        "role": prof["role"] if prof else None,
        "worker_id": str(worker["id"]) if worker else None,
        "is_super_admin": is_super,
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


_INVITE_ROLES = {"hiring_manager", "compliance_lead", "org_admin"}


@app.post("/org/invites", status_code=201)
async def create_invite(body: InviteIn, actor=Depends(require_org_admin)):
    role = "org_admin" if body.grant_admin else "hiring_manager"
    title = (body.title or "").strip() or None
    email_in = body.email.strip()
    raw, thash = new_share_token()
    async with db.pool().acquire() as c:
        if billing.enforce():
            b = await billing.get_billing(c, actor["org_id"])
            used = await billing.seats_used(c, actor["org_id"])
            if used >= b["seats"]:
                raise HTTPException(402, f"Your {b['plan']} plan includes {b['seats']} seats and they're all in use. Upgrade to add more.")
        org = await c.fetchrow("select name from orgs where id = $1", actor["org_id"])
        await c.execute(
            "insert into org_invites (org_id, email, role, title, token_hash, invited_by, expires_at) "
            "values ($1, $2, $3::user_role_t, $4, $5, $6::uuid, $7)",
            actor["org_id"], email_in, role, title, thash, actor["user_id"], _now() + timedelta(days=14),
        )
    base = os.environ.get("PUBLIC_APP_URL", "https://reference-platform.vercel.app").rstrip("/")
    link = f"{base}/invite/{raw}"
    descriptor = title or ("an admin" if body.grant_admin else "a team member")
    sent = await email.send_email(
        email_in,
        f"You've been invited to {org['name']} on Reffolio",
        f"<p>You've been invited to join <b>{org['name']}</b> as {descriptor}"
        f"{' with admin access' if body.grant_admin else ''}.</p>"
        f"<p>Accept your invite:</p><p><a href='{link}'>{link}</a></p>"
        f"<p>Sign in (or create an account) with this email address to accept.</p>",
    )
    return {"sent": bool(sent), "invite_link": link}


@app.get("/org/members")
async def list_members(actor=Depends(require_org_actor)):
    async with db.pool().acquire() as c:
        members = await c.fetch(
            "select id, full_name, email, role, title from profiles where org_id = $1 order by role, full_name",
            actor["org_id"],
        )
        pending = await c.fetch(
            "select id, email, role, title, created_at from org_invites "
            "where org_id = $1 and accepted_at is null and expires_at > now() order by created_at desc",
            actor["org_id"],
        )
    return {
        "members": [dict(m) for m in members],
        "pending_invites": [dict(p) for p in pending],
        "is_admin": actor["role"] == "org_admin",
        "me": str(actor["user_id"]),
    }


@app.delete("/org/invites/{invite_id}")
async def cancel_invite(invite_id: UUID, actor=Depends(require_org_admin)):
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "delete from org_invites where id = $1 and org_id = $2 and accepted_at is null returning id",
            invite_id, actor["org_id"],
        )
    if not row:
        raise HTTPException(404, "invite not found or already accepted")
    return {"cancelled": True}


@app.delete("/org/members/{profile_id}")
async def remove_member(profile_id: UUID, actor=Depends(require_org_admin)):
    if str(profile_id) == str(actor["user_id"]):
        raise HTTPException(400, "you can't remove yourself")
    async with db.pool().acquire() as c:
        m = await c.fetchrow(
            "select id, role from profiles where id = $1 and org_id = $2", profile_id, actor["org_id"]
        )
        if not m:
            raise HTTPException(404, "member not found")
        if m["role"] == "org_admin":
            admins = await c.fetchval(
                "select count(*) from profiles where org_id = $1 and role = 'org_admin'", actor["org_id"]
            )
            if admins <= 1:
                raise HTTPException(400, "can't remove the last admin")
        await c.execute("delete from profiles where id = $1 and org_id = $2", profile_id, actor["org_id"])
    return {"removed": True}


@app.post("/org/members/{profile_id}/lock")
async def lock_member(profile_id: UUID, actor=Depends(require_org_admin)):
    if str(profile_id) == str(actor["user_id"]):
        raise HTTPException(400, "you can't lock yourself")
    async with db.pool().acquire() as c:
        r = await c.fetchrow(
            "update profiles set is_locked = true where id = $1 and org_id = $2 returning id",
            profile_id, actor["org_id"],
        )
    if not r:
        raise HTTPException(404, "member not found")
    return {"locked": True}


@app.post("/org/members/{profile_id}/unlock")
async def unlock_member(profile_id: UUID, actor=Depends(require_org_admin)):
    async with db.pool().acquire() as c:
        r = await c.fetchrow(
            "update profiles set is_locked = false where id = $1 and org_id = $2 returning id",
            profile_id, actor["org_id"],
        )
    if not r:
        raise HTTPException(404, "member not found")
    return {"locked": False}


@app.post("/org/references/{reference_id}/freeze")
async def freeze_reference(reference_id: UUID, actor=Depends(require_org_admin)):
    async with db.pool().acquire() as c:
        r = await c.fetchrow(
            'update "references" set frozen_at = now() where id = $1 and issuing_org_id = $2 returning id',
            reference_id, actor["org_id"],
        )
    if not r:
        raise HTTPException(404, "reference not found")
    return {"frozen": True}


@app.post("/org/references/{reference_id}/unfreeze")
async def unfreeze_reference(reference_id: UUID, actor=Depends(require_org_admin)):
    async with db.pool().acquire() as c:
        r = await c.fetchrow(
            'update "references" set frozen_at = null where id = $1 and issuing_org_id = $2 returning id',
            reference_id, actor["org_id"],
        )
    if not r:
        raise HTTPException(404, "reference not found")
    return {"frozen": False}


@app.get("/org/activity")
async def org_activity(actor=Depends(require_org_admin)):
    async with db.pool().acquire() as c:
        members = await c.fetch(
            """
            select p.id, p.full_name, p.email, p.title, p.role, p.is_locked,
                   count(r.id) filter (where r.id is not null) as total,
                   count(r.id) filter (where r.status = 'draft') as drafts,
                   count(r.id) filter (where r.status = 'published') as published,
                   max(r.created_at) as last_active
            from profiles p
            left join "references" r on r.created_by = p.id and r.issuing_org_id = p.org_id
            where p.org_id = $1
            group by p.id, p.full_name, p.email, p.title, p.role, p.is_locked
            order by published desc nulls last, p.full_name
            """,
            actor["org_id"],
        )
        totals = await c.fetchrow(
            """
            select count(*) as total,
                   count(*) filter (where status = 'published') as published,
                   count(*) filter (where status = 'draft') as drafts,
                   count(*) filter (where frozen_at is not null) as frozen
            from "references" where issuing_org_id = $1
            """,
            actor["org_id"],
        )
        opens = await c.fetchval(
            'select count(*) from access_log al join "references" r on r.id = al.reference_id '
            "where r.issuing_org_id = $1",
            actor["org_id"],
        )
    return {
        "members": [dict(m) for m in members],
        "totals": {**dict(totals), "total_opens": int(opens or 0)},
    }


@app.get("/org/records")
async def org_records(actor=Depends(require_org_admin)):
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            """
            select r.id, r.status, r.assignment_context, r.content_hash, r.risk_score,
                   r.ai_summary, r.published_at, r.created_at, r.frozen_at,
                   w.full_name as worker_name,
                   cre.full_name as author_name,
                   coalesce(a.opens, 0) as opens, a.last_opened,
                   exists(select 1 from referees rf where rf.reference_id = r.id and rf.confirmed_at is not null) as referee_confirmed
            from "references" r
            join workers w on w.id = r.worker_id
            left join profiles cre on cre.id = r.created_by
            left join (select reference_id, count(*) as opens, max(accessed_at) as last_opened
                       from access_log group by reference_id) a on a.reference_id = r.id
            where r.issuing_org_id = $1
            order by r.created_at desc
            """,
            actor["org_id"],
        )
    return {"records": [dict(r) for r in rows]}


@app.get("/invite/{token}")
async def invite_preview(token: str, user=Depends(current_user)):
    async with db.pool().acquire() as c:
        inv = await c.fetchrow(
            "select i.org_id, i.email, i.role, i.accepted_at, i.expires_at, o.name as org_name "
            "from org_invites i join orgs o on o.id = i.org_id where i.token_hash = $1",
            token_hash(token),
        )
        if inv is None:
            raise HTTPException(404, "invalid invite link")
    return {
        "org_name": inv["org_name"],
        "role": inv["role"],
        "invited_email": inv["email"],
        "email_matches": (user.get("email") or "").lower() == str(inv["email"]).lower(),
        "already_accepted": inv["accepted_at"] is not None,
        "expired": inv["expires_at"] <= _now(),
    }


@app.post("/invite/{token}/accept")
async def accept_invite(token: str, user=Depends(current_user)):
    async with db.pool().acquire() as c:
        inv = await c.fetchrow(
            "select id, org_id, email, role, title, accepted_at, expires_at from org_invites where token_hash = $1",
            token_hash(token),
        )
        if inv is None:
            raise HTTPException(404, "invalid invite link")
        if inv["expires_at"] <= _now():
            raise HTTPException(403, "this invite has expired")
        if (user.get("email") or "").lower() != str(inv["email"]).lower():
            raise HTTPException(403, "this invite was sent to a different email address")
        async with c.transaction():
            await c.execute(
                "insert into profiles (id, org_id, role, title, full_name, email) "
                "values ($1::uuid, $2, $3::user_role_t, $4, $5, $6) "
                "on conflict (id) do update set org_id = excluded.org_id, role = excluded.role, title = excluded.title",
                user["user_id"], inv["org_id"], inv["role"], inv["title"],
                user.get("email") or "member", user.get("email") or "unknown@local",
            )
            if inv["accepted_at"] is None:
                await c.execute("update org_invites set accepted_at = now() where id = $1", inv["id"])
    return {"org_id": str(inv["org_id"]), "role": inv["role"]}


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
    return {
        "worker_id": str(row["id"]),
        "registration_status": row["registration_status"],
        "register": {
            "register_status": check.get("register_status"),
            "registered_name": check.get("registered_name"),
            "registered_until": check.get("registered_until"),
            "detail": check.get("detail"),
        },
    }


@app.post("/references", status_code=201)
async def references_create(body: ReferenceCreateIn, actor=Depends(require_org_actor)):
    org_id = actor["org_id"]
    async with db.pool().acquire() as c:
        org = await c.fetchrow("select email_domain from orgs where id = $1", org_id)
        async with c.transaction():
            ref = await c.fetchrow(
                """
                insert into "references" (worker_id, issuing_org_id, template_id, assignment_context, content, created_by)
                values ($1, $2, $3, $4, $5, $6::uuid)
                returning id, status
                """,
                body.worker_id, org_id, body.template_id, body.assignment_context, body.content, actor["user_id"],
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
    frozen = await c.fetchval('select frozen_at from "references" where id = $1', grant["reference_id"])
    if frozen is not None:
        raise HTTPException(403, "this reference is under review and temporarily unavailable")
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
                   w.registration_status,
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
        "worker": {"name": ref["worker_name"], "registration": f'{ref["registration_body"]}:{ref["registration_number"]}', "registration_status": ref["registration_status"]},
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
                   w.registration_status,
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
        "worker": {"name": ref["worker_name"], "registration": f'{ref["registration_body"]}:{ref["registration_number"]}', "registration_status": ref["registration_status"]},
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
