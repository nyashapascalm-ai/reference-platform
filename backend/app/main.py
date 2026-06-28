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

from . import ai, apikeys, billing, db, email, swe
from . import webhooks
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
    registration_number: str | None = None
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
    vertical: str | None = None
    vertical: str | None = None


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
        await billing.assert_active(c, actor["org_id"])
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
    no_register = (body.registration_body or "").strip().lower() in ("none", "self", "")
    if no_register:
        reg_body = "none"
        # NOT NULL + unique(registration_body, registration_number):
        # user_id is unique per worker, so it is a safe synthetic key here.
        reg_number = str(user["user_id"])
        check = {
            "status": "not_applicable",
            "checked_at": _now(),
            "detail": "Role is not on a professional register; identity-based verification.",
        }
    else:
        reg_body = body.registration_body
        if not body.registration_number:
            raise HTTPException(422, "registration_number is required for this registration body")
        reg_number = body.registration_number
        check = await check_registration(reg_body, reg_number)
    idhash = identity_hash(reg_body, reg_number, body.dbs_certificate_number)
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
                    user["user_id"], body.full_name, body.vertical, reg_body,
                    reg_number, check["status"], _now(),
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

        tmpl = await c.fetchrow("select field_schema, vertical from reference_templates where id = $1", ref["template_id"])
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
            result = await ai.synthesise(content, None, tmpl["vertical"] if tmpl else None)
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
        tmpl = await c.fetchrow("select field_schema, vertical from reference_templates where id = $1", body.template_id)
    if tmpl is None:
        raise HTTPException(404, "template not found")
    required = (tmpl["field_schema"] or {}).get("required", [])
    try:
        content = await ai.draft_reference(body.notes, required, tmpl["vertical"] if tmpl else None)
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
        return await ai.synthesise(body.content, body.assignment_context, body.vertical)
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
            'select r.issuing_org_id, r.content, r.assignment_context, t.vertical '
            'from "references" r left join reference_templates t on t.id = r.template_id '
            'where r.id = $1',
            reference_id,
        )
        if ref is None:
            raise HTTPException(404, "reference not found")
        if ref["issuing_org_id"] != actor["org_id"]:
            raise HTTPException(403, "only the issuing org may analyse this reference")
        try:
            result = await ai.synthesise(ref["content"] or {}, ref["assignment_context"], ref["vertical"])
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


# ============================================================
# Public API (v1) + API key management
# ============================================================

class ApiKeyCreateIn(BaseModel):
    name: str | None = None


@app.get("/org/api-keys")
async def list_api_keys(actor=Depends(require_org_actor)):
    if actor["role"] != "org_admin":
        raise HTTPException(403, "only an organisation admin can manage API keys")
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            "select id, name, prefix, last_used_at, revoked_at, created_at "
            "from api_keys where org_id = $1 order by created_at desc",
            actor["org_id"],
        )
    plan = "free"
    async with db.pool().acquire() as c:
        b = await c.fetchrow("select coalesce(plan,'free') as plan from billing_customers where org_id = $1", actor["org_id"])
        if b:
            plan = b["plan"]
    return {"api_enabled": bool(billing.features(plan).get("api")), "keys": [dict(r) for r in rows]}


@app.post("/org/api-keys", status_code=201)
async def create_api_key(body: ApiKeyCreateIn, actor=Depends(require_org_actor)):
    if actor["role"] != "org_admin":
        raise HTTPException(403, "only an organisation admin can create API keys")
    async with db.pool().acquire() as c:
        b = await c.fetchrow("select coalesce(plan,'free') as plan from billing_customers where org_id = $1", actor["org_id"])
        plan = b["plan"] if b else "free"
        if not billing.features(plan).get("api"):
            raise HTTPException(402, "The API is available on the Growth and Business plans. Upgrade to create API keys.")
        raw, kh, prefix = apikeys.generate_key()
        row = await c.fetchrow(
            "insert into api_keys (org_id, name, key_hash, prefix, created_by) "
            "values ($1, $2, $3, $4, $5::uuid) returning id, created_at",
            actor["org_id"], (body.name or "API key").strip()[:80], kh, prefix, actor["profile_id"],
        )
    # raw key returned exactly once
    return {"id": str(row["id"]), "name": (body.name or "API key"), "prefix": prefix, "key": raw,
            "created_at": row["created_at"].isoformat()}


@app.delete("/org/api-keys/{key_id}")
async def revoke_api_key(key_id: UUID, actor=Depends(require_org_actor)):
    if actor["role"] != "org_admin":
        raise HTTPException(403, "only an organisation admin can revoke API keys")
    async with db.pool().acquire() as c:
        r = await c.execute(
            "update api_keys set revoked_at = now() where id = $1 and org_id = $2 and revoked_at is null",
            key_id, actor["org_id"],
        )
    return {"revoked": True}


# ---- /v1 public API (authenticated by API key) -------------------------------

@app.get("/v1/ping")
async def v1_ping(actor=Depends(apikeys.require_api_org)):
    return {"ok": True, "org_id": str(actor["org_id"]), "scope": "org"}


@app.get("/v1/templates")
async def v1_templates(vertical: str | None = None, actor=Depends(apikeys.require_api_org)):
    async with db.pool().acquire() as c:
        if vertical:
            rows = await c.fetch(
                "select id, vertical, name, version, field_schema from reference_templates "
                "where is_active and vertical = $1::vertical_t order by name", vertical)
        else:
            rows = await c.fetch(
                "select id, vertical, name, version, field_schema from reference_templates "
                "where is_active order by name")
    return [dict(r) for r in rows]


# ============================================================================
# NEW /v1 API — request / consent / receive model (employer-to-employer)
# Replaces the old worker-held endpoints (workers/verify, references create/publish).
# Mirrors the UI's create_request behaviour exactly.
# ============================================================================

class V1RequestCreateIn(BaseModel):
    worker_name: str
    worker_email: str
    referee_email: str
    referee_name: str | None = None
    prev_employer_name: str | None = None
    template_id: str | None = None
    vertical: str | None = None
    message: str | None = None


def _v1_request_status(req_status: str, consent_status: str | None) -> str:
    """Map internal columns to a single public lifecycle status."""
    if req_status == "sent":
        return "pending"
    if req_status == "opened":
        return "opened"
    if req_status == "completed":
        if consent_status == "granted":
            return "received"        # reference is readable by the requester
        return "awaiting_consent"    # completed but candidate hasn't consented yet
    return req_status or "pending"


@app.post("/v1/requests", status_code=201)
async def v1_request_create(body: V1RequestCreateIn, request: Request,
                            actor=Depends(apikeys.require_api_org)):
    """Create a reference request. Reffolio emails the referee a secure link and,
    on completion, asks the candidate to consent — exactly as in the dashboard."""
    org_id = actor["org_id"]
    async with db.pool().acquire() as _bc:
        await billing.assert_active(_bc, org_id)
        await billing.assert_credits(_bc, org_id)
    referee_email = body.referee_email.strip().lower()
    worker_email = body.worker_email.strip().lower()
    if "@" not in referee_email:
        raise HTTPException(422, "a valid referee email is required")
    if "@" not in worker_email:
        raise HTTPException(422, "a valid candidate email is required")
    domain = referee_email.split("@")[-1]
    free_mail = domain in {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
                           "icloud.com", "live.com", "aol.com", "me.com"}
    raw, thash = new_share_token()
    link = f"{SITE_URL}/complete-reference/{raw}"

    async with db.pool().acquire() as c:
        org = await c.fetchrow("select name, brand_color, logo_url, email_signature from orgs where id = $1", org_id)
        req = await c.fetchrow(
            """
            insert into reference_requests
              (requester_org_id, requested_by, worker_name, worker_email, prev_employer_name,
               referee_name, referee_email, referee_email_domain, domain_verified,
               template_id, link_token_hash, message)
            values ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            returning id
            """,
            org_id, actor.get("user_id"), body.worker_name.strip(), worker_email, body.prev_employer_name,
            body.referee_name, referee_email, domain, (not free_mail),
            (body.template_id
             or await resolve_template_for_vertical(c, body.vertical)
             or await resolve_default_template(c, org_id)), thash, body.message,
        )
        await add_event(c, event_type="requested", request_id=req["id"],
                       actor_org_id=org_id, actor_id=actor.get("user_id"),
                       actor_email=actor.get("email"),
                       detail={"referee_email": referee_email, "free_mail": free_mail, "via_api": True},
                       ip_address=request.client.host if request.client else None)

    sent = await email.send_email(
        referee_email,
        f"Reference request for {body.worker_name.strip()}",
        request_email_html(candidate=body.worker_name.strip(),
                          requester_org=org["name"], referee_name=body.referee_name,
                          link=link, message=body.message,
                          brand_color=org["brand_color"], logo_url=org["logo_url"],
                          signature=org["email_signature"]),
    )
    return {"request_id": str(req["id"]), "status": "pending",
            "email_sent": sent, "domain_verified": (not free_mail)}


@app.get("/v1/requests/{request_id}")
async def v1_request_get(request_id: UUID, actor=Depends(apikeys.require_api_org)):
    """Poll one request: lifecycle status, and the produced reference + consent once available.
    Scoped to the caller's organisation."""
    org_id = actor["org_id"]
    async with db.pool().acquire() as c:
        req = await c.fetchrow(
            """select id, worker_name, worker_email, referee_email, referee_name,
                      prev_employer_name, status, created_at, sent_at, opened_at, completed_at,
                      produced_reference_id, domain_verified
               from reference_requests
               where id = $1 and requester_org_id = $2""",
            request_id, org_id,
        )
        if not req:
            raise HTTPException(404, "request not found")
        consent_status = None
        ref_meta = None
        if req["produced_reference_id"]:
            srow = await c.fetchrow(
                """select s.consent_status, r.ref_number, r.content_hash
                   from reference_sends s join "references" r on r.id = s.reference_id
                   where s.reference_id = $1 and s.recipient_org_id = $2
                   order by s.created_at desc limit 1""",
                req["produced_reference_id"], org_id,
            )
            if srow:
                consent_status = srow["consent_status"]
                ref_meta = {"reference_id": str(req["produced_reference_id"]),
                            "ref_number": srow["ref_number"],
                            "content_hash": srow["content_hash"],
                            "readable": srow["consent_status"] == "granted"}
        return {
            "request_id": str(req["id"]),
            "status": _v1_request_status(req["status"], consent_status),
            "candidate_name": req["worker_name"],
            "candidate_email": req["worker_email"],
            "referee_email": req["referee_email"],
            "referee_name": req["referee_name"],
            "previous_employer": req["prev_employer_name"],
            "domain_verified": req["domain_verified"],
            "created_at": req["created_at"].isoformat() if req["created_at"] else None,
            "completed_at": req["completed_at"].isoformat() if req["completed_at"] else None,
            "consent_status": consent_status,
            "reference": ref_meta,
        }


@app.get("/v1/requests")
async def v1_request_list(actor=Depends(apikeys.require_api_org)):
    """List the organisation's reference requests with their lifecycle status (polling fallback)."""
    org_id = actor["org_id"]
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            """select req.id, req.worker_name, req.referee_email, req.status, req.created_at,
                      req.produced_reference_id, s.consent_status
               from reference_requests req
               left join reference_sends s on s.reference_id = req.produced_reference_id
                    and s.recipient_org_id = req.requester_org_id
               where req.requester_org_id = $1
               order by req.created_at desc""",
            org_id,
        )
    return [{"request_id": str(r["id"]),
             "status": _v1_request_status(r["status"], r["consent_status"]),
             "candidate_name": r["worker_name"],
             "referee_email": r["referee_email"],
             "consent_status": r["consent_status"],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None}
            for r in rows]


@app.get("/v1/references/{reference_id}")
async def v1_reference_get(reference_id: UUID, actor=Depends(apikeys.require_api_org)):
    """Fetch a received reference's content. Scoped: only references SENT TO the caller's
    organisation with consent GRANTED are readable (never gated by billing status)."""
    org_id = actor["org_id"]
    async with db.pool().acquire() as c:
        srow = await c.fetchrow(
            """select s.consent_status, s.recipient_name, s.created_at as received_at,
                      r.id, r.content, r.content_hash, r.risk_score, r.ai_summary,
                      r.ref_number, r.published_at, t.vertical, t.name as template_name
               from reference_sends s
               join "references" r on r.id = s.reference_id
               left join reference_templates t on t.id = r.template_id
               where s.reference_id = $1 and s.recipient_org_id = $2
               order by s.created_at desc limit 1""",
            reference_id, org_id,
        )
        if srow is None:
            raise HTTPException(404, "reference not found for your organisation")
        if srow["consent_status"] != "granted":
            raise HTTPException(403, "the candidate has not consented to release this reference yet")
    return {
        "reference_id": str(srow["id"]),
        "ref_number": srow["ref_number"],
        "candidate_name": srow["recipient_name"],
        "sector": srow["vertical"],
        "template_name": srow["template_name"],
        "content": srow["content"],
        "content_hash": srow["content_hash"],
        "risk_score": srow["risk_score"],
        "ai_summary": srow["ai_summary"],
        "consent_status": srow["consent_status"],
        "published_at": srow["published_at"].isoformat() if srow["published_at"] else None,
        "received_at": srow["received_at"].isoformat() if srow["received_at"] else None,
    }
# ============================================================
# References Received — request flow endpoints (Layer 2)
# Appended to main.py. Uses: require_org_actor, current_user, db,
# new_share_token, token_hash, content_hash, _now, email.send_email,
# and the requests_mod helpers.
# ============================================================
from .requests_mod import (
    new_ref_number, add_event,
    request_email_html, received_email_html, worker_notice_html,
)

SITE_URL = os.environ.get("SITE_URL", "https://reffolio.co.uk")


class RequestCreateIn(BaseModel):
    worker_name: str
    worker_email: str
    referee_email: str
    referee_name: str | None = None
    prev_employer_name: str | None = None
    template_id: str | None = None
    vertical: str | None = None
    message: str | None = None


class RequestCompleteIn(BaseModel):
    content: dict
    referee_name: str | None = None
    referee_job_title: str | None = None
    worker_registration_body: str | None = None
    worker_registration_number: str | None = None
    worker_vertical: str | None = None


# Accepted vertical hints from API partners -> mapped to the org's template pool.
_VERTICAL_ALIASES = {
    "care": "care", "social_care": "care", "cqc": "care",
    "health": "healthcare", "healthcare": "healthcare", "nhs": "healthcare",
    "nmc": "healthcare", "hcpc": "healthcare",
    "education": "teaching", "teaching": "teaching", "school": "teaching",
    "kcsie": "teaching",
    "social_work": "social_work", "socialwork": "social_work", "swe": "social_work",
}


async def resolve_template_for_vertical(conn, vertical_hint):
    """Map a partner-supplied vertical hint (e.g. 'care', 'nhs') to an active
    template id. Returns None if the hint is unknown or no template matches,
    so the caller can fall back to the org default."""
    if not vertical_hint:
        return None
    key = _VERTICAL_ALIASES.get(str(vertical_hint).strip().lower())
    if not key:
        return None
    row = await conn.fetchrow(
        "select id from reference_templates where vertical = $1::vertical_t "
        "and is_active order by name limit 1",
        key,
    )
    return row["id"] if row else None


async def resolve_default_template(conn, org_id):
    """Return an appropriate template_id for an org that didn't specify one.
    Picks the active template matching the org's vertical; falls back to any
    active template. Returns None only if no templates exist at all."""
    row = await conn.fetchrow(
        """select t.id
           from reference_templates t
           join orgs o on o.vertical = t.vertical
           where o.id = $1 and t.is_active
           order by t.name
           limit 1""",
        org_id,
    )
    if row:
        return row["id"]
    # Fallback: any active template (keeps the flow working even if vertical
    # doesn't match a template for some reason).
    row = await conn.fetchrow(
        "select id from reference_templates where is_active order by name limit 1"
    )
    return row["id"] if row else None


@app.post("/requests")
async def create_request(body: RequestCreateIn, request: Request, actor=Depends(require_org_actor)):
    """A hiring provider requests a reference about a candidate from a previous employer."""
    org_id = actor["org_id"]
    async with db.pool().acquire() as _bc:
        await billing.assert_active(_bc, org_id)
        await billing.assert_credits(_bc, org_id)
    referee_email = body.referee_email.strip().lower()
    worker_email = body.worker_email.strip().lower()
    if "@" not in referee_email:
        raise HTTPException(422, "a valid referee email is required")
    if "@" not in worker_email:
        raise HTTPException(422, "a valid candidate email is required")
    domain = referee_email.split("@")[-1]
    free_mail = domain in {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
                           "icloud.com", "live.com", "aol.com", "me.com"}
    raw, thash = new_share_token()
    link = f"{SITE_URL}/complete-reference/{raw}"

    async with db.pool().acquire() as c:
        org = await c.fetchrow("select name, brand_color, logo_url, email_signature from orgs where id = $1", org_id)
        req = await c.fetchrow(
            """
            insert into reference_requests
              (requester_org_id, requested_by, worker_name, worker_email, prev_employer_name,
               referee_name, referee_email, referee_email_domain, domain_verified,
               template_id, link_token_hash, message)
            values ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            returning id
            """,
            org_id, actor["user_id"], body.worker_name.strip(), worker_email, body.prev_employer_name,
            body.referee_name, referee_email, domain, (not free_mail),
            (body.template_id
             or await resolve_template_for_vertical(c, body.vertical)
             or await resolve_default_template(c, org_id)), thash, body.message,
        )
        await add_event(c, event_type="requested", request_id=req["id"],
                       actor_org_id=org_id, actor_id=actor["user_id"],
                       actor_email=actor.get("email"),
                       detail={"referee_email": referee_email, "free_mail": free_mail},
                       ip_address=request.client.host if request.client else None)

    sent = await email.send_email(
        referee_email,
        f"Reference request for {body.worker_name.strip()}",
        request_email_html(candidate=body.worker_name.strip(),
                          requester_org=org["name"], referee_name=body.referee_name,
                          link=link, message=body.message,
                          brand_color=org["brand_color"], logo_url=org["logo_url"],
                          signature=org["email_signature"]),
    )
    return {"request_id": str(req["id"]), "email_sent": sent,
            "domain_verified": (not free_mail)}


@app.get("/requests/{token}")
async def open_request(token: str, request: Request):
    """Public: the referee opens the secure link. Returns the request + template form."""
    async with db.pool().acquire() as c:
        req = await c.fetchrow(
            """
            select r.id, r.worker_name, r.prev_employer_name, r.referee_name,
                   r.status, r.template_id, r.message, o.name as requester_org,
                   o.brand_color, o.logo_url
            from reference_requests r join orgs o on o.id = r.requester_org_id
            where r.link_token_hash = $1
            """,
            token_hash(token),
        )
        if not req:
            raise HTTPException(404, "this reference link is not valid")
        if req["status"] == "completed":
            raise HTTPException(409, "this reference has already been completed")
        tpl = None
        if req["template_id"]:
            tpl = await c.fetchrow(
                "select id, name, vertical, field_schema from reference_templates where id = $1",
                req["template_id"],
            )
        if req["status"] == "sent":
            await c.execute("update reference_requests set status='opened', opened_at=now() where id=$1", req["id"])
            await add_event(c, event_type="opened", request_id=req["id"],
                           ip_address=request.client.host if request.client else None)
            try:
                _adm = await c.fetchrow(
                    "select p.email, rr.referee_name, rr.worker_name from reference_requests rr "
                    "join profiles p on p.id = rr.requested_by where rr.id = $1", req["id"])
                if _adm and _adm["email"]:
                    from .requests_mod import referee_opened_html
                    await email.send_email(
                        _adm["email"], f"Your reference request for {_adm['worker_name']} was opened",
                        referee_opened_html(candidate=_adm["worker_name"], referee_name=_adm["referee_name"]))
            except Exception:
                pass
    return {
        "worker_name": req["worker_name"],
        "prev_employer_name": req["prev_employer_name"],
        "referee_name": req["referee_name"],
        "requester_org": req["requester_org"],
        "brand_color": req["brand_color"],
        "logo_url": req["logo_url"],
        "message": req["message"],
        "template": ({"id": str(tpl["id"]), "name": tpl["name"], "vertical": tpl["vertical"],
                      "field_schema": tpl["field_schema"]} if tpl else None),
    }


@app.post("/requests/{token}/complete")
async def complete_request(token: str, body: RequestCompleteIn, request: Request):
    """Public: the referee submits. Produces a frozen, hashed reference, sends it to
    the requester, and notifies the worker. No account required."""
    async with db.pool().acquire() as c:
        req = await c.fetchrow(
            "select * from reference_requests where link_token_hash = $1",
            token_hash(token),
        )
        if not req:
            raise HTTPException(404, "this reference link is not valid")
        if req["status"] == "completed":
            raise HTTPException(409, "this reference has already been completed")

        org_id = req["requester_org_id"]
        # Validate required fields if the template declares them.
        tpl = None
        if req["template_id"]:
            tpl = await c.fetchrow(
                "select vertical, field_schema from reference_templates where id = $1", req["template_id"])
            required = (tpl["field_schema"] or {}).get("required", []) if tpl else []
            missing = [f for f in required if not str(body.content.get(f, "")).strip()]
            if missing:
                raise HTTPException(422, f"missing required answers: {', '.join(missing)}")

        # Find or create the worker (org-owned; consent claimed later by the worker).
        vertical = body.worker_vertical or (tpl["vertical"] if tpl else "care")
        reg_body = body.worker_registration_body or "none"
        reg_no = body.worker_registration_number or "n/a"
        worker = await c.fetchrow(
            "select id from workers where lower(full_name)=lower($1) and vertical=$2::vertical_t limit 1",
            req["worker_name"], vertical,
        )
        if worker:
            worker_id = worker["id"]
        else:
            worker_id = (await c.fetchrow(
                """insert into workers (full_name, vertical, registration_body, registration_number,
                       registration_status, dbs_status, rtw_status)
                   values ($1, $2::vertical_t, $3::registration_body_t, $4,
                       'not_applicable','not_applicable','not_applicable')
                   returning id""",
                req["worker_name"], vertical, reg_body, reg_no,
            ))["id"]

        ref_number = new_ref_number()
        chash = content_hash(str(worker_id), str(org_id), body.content)
        now = _now()
        ref = await c.fetchrow(
            """
            insert into "references"
              (worker_id, issuing_org_id, template_id, content, content_hash,
               ref_number, status, submitted_at, published_at, frozen_at, created_by)
            values ($1, $2, $3, $4, $5, $6, 'published', $7, $7, $7, null)
            returning id
            """,
            worker_id, org_id,
            (req["template_id"] or await resolve_default_template(c, org_id)),
            body.content, chash, ref_number, now,
        )
        ref_id = ref["id"]

        # Record the referee.
        ref_name = body.referee_name or req["referee_name"] or "Referee"
        ref_email = req["referee_email"]
        await c.execute(
            """insert into referees (reference_id, full_name, job_title, work_email,
                   email_domain, domain_verified, auth_method, submitted_at, confirmed_at, confirmed_name)
               values ($1, $2, $3, $4, $5, $6, 'request_link', now(), now(), $2)""",
            ref_id, ref_name, body.referee_job_title or "Manager", ref_email,
            req["referee_email_domain"], req["domain_verified"],
        )

        # Link request -> reference, mark completed.
        await c.execute(
            "update reference_requests set status='completed', completed_at=now(), "
            "produced_reference_id=$2, worker_id=$3 where id=$1",
            req["id"], ref_id, worker_id,
        )
        # HOLD RELEASE: create the send as pending with a worker consent token.
        consent_raw, consent_thash = new_share_token()
        await c.execute(
            """insert into reference_sends
                 (reference_id, reference_version, sender_org_id, recipient_org_id,
                  recipient_email, recipient_name, consent_status, consent_token_hash, delivered_at)
               values ($1, 1, $2, $2, $3, $4, 'pending', $5, now())""",
            ref_id, org_id, ref_email, req["worker_name"], consent_thash,
        )
        await add_event(c, event_type="completed", reference_id=ref_id, request_id=req["id"],
                       actor_name=ref_name, actor_email=ref_email,
                       detail={"ref_number": ref_number},
                       ip_address=request.client.host if request.client else None)
        await add_event(c, event_type="sent", reference_id=ref_id, request_id=req["id"],
                       actor_org_id=org_id, detail={"recipient_org_id": str(org_id)})

        org = await c.fetchrow("select name from orgs where id = $1", org_id)

    # HOLD RELEASE: email the WORKER for consent; the requester is NOT notified until consent is granted.
    from .requests_mod import consent_request_html, referee_submitted_html, completed_awaiting_consent_html
    consent_link = f"{SITE_URL}/consent/{consent_raw}"
    if req["worker_email"]:
        await email.send_email(
            req["worker_email"],
            f"Your consent is needed for a reference ({ref_number})",
            consent_request_html(candidate=req["worker_name"], requester_org=org["name"],
                                referee_name=ref_name, ref_number=ref_number, link=consent_link),
        )
    # Notify the referee that their submission was received.
    try:
        if ref_email:
            await email.send_email(
                ref_email, f"Thank you \u2014 reference submitted ({ref_number})",
                referee_submitted_html(candidate=req["worker_name"], requester_org=org["name"],
                                       ref_number=ref_number))
    except Exception:
        pass
    # Notify the requester that the reference is completed and awaiting consent.
    try:
        async with db.pool().acquire() as _c2:
            _orow = await _c2.fetchrow(
                "select requester_org_id, worker_name from reference_requests where link_token_hash = $1",
                token_hash(token))
        _radm = await _requester_email(_orow["requester_org_id"]) if _orow else None
        if _radm:
            await email.send_email(
                _radm, f"Reference completed for {req['worker_name']} \u2014 awaiting consent",
                completed_awaiting_consent_html(candidate=req["worker_name"], referee_name=ref_name,
                                                ref_number=ref_number))
    except Exception:
        pass
    return {"reference_id": str(ref_id), "ref_number": ref_number, "status": "awaiting_consent"}


async def _requester_email(org_id):
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "select email from profiles where org_id = $1 and role='org_admin' order by created_at limit 1",
            org_id)
    return row["email"] if row and row.get("email") else None


async def _notify_completion(org_id, worker_name, referee_email, referee_name, ref_number, org_name):
    """Email the requesting org admin (reference received) and the candidate (notice + number)."""
    admin_email = await _requester_email(org_id)
    if admin_email:
        await email.send_email(
            admin_email,
            f"Reference received for {worker_name}",
            received_email_html(candidate=worker_name, referee_name=referee_name,
                               ref_number=ref_number, link=f"{SITE_URL}/dashboard"),
        )
    # We only have the candidate's name (not necessarily an email) at this stage;
    # the worker is notified/claims their number when an email is known. Logged for now.


@app.get("/me/requests")
async def my_requests(actor=Depends(require_org_actor)):
    """Portal: requests sent, and references received.
    Admins see the whole organisation (so references survive a manager leaving);
    members see only the requests they created and the references those produced."""
    org_id = actor["org_id"]
    is_admin = actor.get("role") == "org_admin"
    me_id = actor["profile_id"]
    async with db.pool().acquire() as c:
        if is_admin:
            sent = await c.fetch(
                """select id, worker_name, referee_email, referee_name, status,
                          sent_at, completed_at, produced_reference_id
                   from reference_requests where requester_org_id = $1
                   order by created_at desc""",
                org_id,
            )
            received = await c.fetch(
                """select s.id, s.reference_id, s.recipient_name as worker_name, s.consent_status,
                          s.created_at, r.ref_number, r.content_hash
                   from reference_sends s join "references" r on r.id = s.reference_id
                   where s.recipient_org_id = $1 and s.consent_status = 'granted'
                   order by s.created_at desc""",
                org_id,
            )
            consent_rows = await c.fetch(
                """select req.id as request_id, s.consent_status
                   from reference_requests req
                   join reference_sends s on s.reference_id = req.produced_reference_id
                   where req.requester_org_id = $1""",
                org_id,
            )
        else:
            sent = await c.fetch(
                """select id, worker_name, referee_email, referee_name, status,
                          sent_at, completed_at, produced_reference_id
                   from reference_requests
                   where requester_org_id = $1 and requested_by = $2
                   order by created_at desc""",
                org_id, me_id,
            )
            received = await c.fetch(
                """select s.id, s.reference_id, s.recipient_name as worker_name, s.consent_status,
                          s.created_at, r.ref_number, r.content_hash
                   from reference_sends s
                   join "references" r on r.id = s.reference_id
                   join reference_requests req on req.produced_reference_id = s.reference_id
                   where s.recipient_org_id = $1 and s.consent_status = 'granted'
                     and req.requested_by = $2
                   order by s.created_at desc""",
                org_id, me_id,
            )
            consent_rows = await c.fetch(
                """select req.id as request_id, s.consent_status
                   from reference_requests req
                   join reference_sends s on s.reference_id = req.produced_reference_id
                   where req.requester_org_id = $1 and req.requested_by = $2""",
                org_id, me_id,
            )
        consent_by_req = {str(r["request_id"]): r["consent_status"] for r in consent_rows}
    return {
        "sent": [dict(x) | {"id": str(x["id"]),
                            "produced_reference_id": str(x["produced_reference_id"]) if x["produced_reference_id"] else None,
                            "consent_status": consent_by_req.get(str(x["id"]))}
                 for x in sent],
        "received": [dict(x) | {"id": str(x["id"]), "reference_id": str(x["reference_id"])}
                     for x in received],
    }



# ---- Worker consent (hold-release) ------------------------------------------
@app.get("/consent/{token}")
async def consent_view(token: str, request: Request):
    """Public: the worker opens their consent link."""
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            '''select s.id, s.consent_status, s.recipient_name as worker_name, r.ref_number,
                      o.name as requester_org
               from reference_sends s
               join "references" r on r.id = s.reference_id
               join orgs o on o.id = s.recipient_org_id
               where s.consent_token_hash = $1''',
            token_hash(token),
        )
        if not row:
            raise HTTPException(404, "this consent link is not valid")
    return {
        "worker_name": row["worker_name"],
        "requester_org": row["requester_org"],
        "ref_number": row["ref_number"],
        "consent_status": row["consent_status"],
    }


class ConsentDecisionIn(BaseModel):
    decision: str  # 'grant' | 'decline'


@app.post("/consent/{token}")
async def consent_decide(token: str, body: ConsentDecisionIn, request: Request):
    """Public: the worker grants or declines. On grant, the reference releases to the requester."""
    if body.decision not in ("grant", "decline"):
        raise HTTPException(422, "decision must be 'grant' or 'decline'")
    new_status = "granted" if body.decision == "grant" else "declined"
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            '''select s.id, s.reference_id, s.consent_status, s.recipient_name as worker_name,
                      r.ref_number, s.recipient_org_id
               from reference_sends s join "references" r on r.id = s.reference_id
               where s.consent_token_hash = $1''',
            token_hash(token),
        )
        if not row:
            raise HTTPException(404, "this consent link is not valid")
        if row["consent_status"] != "pending":
            raise HTTPException(409, "a decision has already been recorded")
        await c.execute(
            "update reference_sends set consent_status=$2, consent_decided_at=now() where id=$1",
            row["id"], new_status,
        )
        if new_status == "granted":
            try:
                await webhooks.fire(c, row["recipient_org_id"], "consent_granted",
                                    {"reference_id": str(row["reference_id"]),
                                     "ref_number": row["ref_number"]})
                await webhooks.fire(c, row["recipient_org_id"], "reference_received",
                                    {"reference_id": str(row["reference_id"]),
                                     "ref_number": row["ref_number"]})
            except Exception:
                pass
            # Meter: charge one credit for this verified reference (idempotent, opt-in).
            await billing.consume_reference_credit(c, row["recipient_org_id"], row["reference_id"])
        await add_event(c, event_type=("consent_granted" if new_status == "granted" else "consent_declined"),
                       reference_id=row["reference_id"],
                       actor_name=row["worker_name"], detail={"ref_number": row["ref_number"]},
                       ip_address=request.client.host if request.client else None)
        org = await c.fetchrow("select name from orgs where id=$1", row["recipient_org_id"])
        admin = await c.fetchrow(
            "select email from profiles where org_id=$1 and role='org_admin' order by created_at limit 1",
            row["recipient_org_id"])
    # Notify the requester of the outcome.
    if admin and admin["email"]:
        from .requests_mod import consent_granted_html, consent_declined_html
        if new_status == "granted":
            await email.send_email(admin["email"], f"Reference now available ({row['ref_number']})",
                consent_granted_html(candidate=row["worker_name"], ref_number=row["ref_number"],
                                    link=f"{SITE_URL}/dashboard"))
            try:
                _w = await c.fetchrow(
                    "select rr.worker_email, o.name as org_name from reference_sends s "
                    "join reference_requests rr on rr.produced_reference_id = s.reference_id "
                    "join orgs o on o.id = s.recipient_org_id where s.consent_token_hash = $1",
                    token_hash(token))
                if _w and _w["worker_email"]:
                    from .requests_mod import consent_confirmed_html
                    await email.send_email(
                        _w["worker_email"], f"Consent recorded ({row['ref_number']})",
                        consent_confirmed_html(candidate=row["worker_name"], requester_org=_w["org_name"],
                                               ref_number=row["ref_number"]))
            except Exception:
                pass
        else:
            await email.send_email(admin["email"], f"Candidate declined consent ({row['ref_number']})",
                consent_declined_html(candidate=row["worker_name"], ref_number=row["ref_number"]))
    return {"consent_status": new_status, "ref_number": row["ref_number"]}


# ---- Org setup + form gating (References Received) ---------------------------
# Maps an org_type to the reference verticals it should see.
ORG_TYPE_VERTICALS = {
    "care_provider":   ["care"],
    "school":          ["teaching"],
    "mat":             ["teaching"],
    "nhs_trust":       ["healthcare"],
    "local_authority": ["social_work", "care", "healthcare", "teaching"],
    "agency":          ["social_work", "care", "healthcare", "teaching"],
}
ORG_TYPE_DEFAULT_VERTICAL = {
    "care_provider": "care", "school": "teaching", "mat": "teaching",
    "nhs_trust": "healthcare", "local_authority": "social_work", "agency": "care",
}


@app.get("/org/profile")
async def org_profile_get(actor=Depends(require_org_actor)):
    async with db.pool().acquire() as c:
        o = await c.fetchrow(
            "select id, name, org_type, vertical, setup_complete, logo_url, brand_color, "
            "email_signature, cqc_provider_id, contact_name, contact_phone, contact_email "
            "from orgs where id = $1", actor["org_id"])
    if not o:
        raise HTTPException(404, "organisation not found")
    d = dict(o); d["id"] = str(d["id"])
    d["verticals"] = ORG_TYPE_VERTICALS.get(d["org_type"], ["care"])
    d["default_vertical"] = ORG_TYPE_DEFAULT_VERTICAL.get(d["org_type"], "care")
    return d


class OrgProfileIn(BaseModel):
    org_type: str | None = None
    cqc_provider_id: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    logo_url: str | None = None
    brand_color: str | None = None
    email_signature: str | None = None


@app.post("/org/profile")
async def org_profile_set(body: OrgProfileIn, actor=Depends(require_org_admin)):
    valid_types = set(ORG_TYPE_VERTICALS.keys())
    if body.org_type is not None and body.org_type not in valid_types:
        raise HTTPException(422, f"org_type must be one of: {', '.join(sorted(valid_types))}")
    sets, vals = [], []
    i = 1
    for field in ("org_type", "cqc_provider_id", "contact_name", "contact_phone",
                  "contact_email", "logo_url", "brand_color", "email_signature"):
        v = getattr(body, field)
        if v is not None:
            sets.append(f"{field} = ${i}"); vals.append(v); i += 1
    if body.org_type is not None:
        sets.append(f"setup_complete = true")
    if not sets:
        raise HTTPException(422, "nothing to update")
    vals.append(actor["org_id"])
    async with db.pool().acquire() as c:
        await c.execute(f"update orgs set {', '.join(sets)} where id = ${i}", *vals)
    return {"ok": True}


@app.get("/org/templates")
async def org_templates(actor=Depends(require_org_actor)):
    """Return only the reference templates this org should see, based on its type."""
    async with db.pool().acquire() as c:
        o = await c.fetchrow("select org_type from orgs where id = $1", actor["org_id"])
        verticals = ORG_TYPE_VERTICALS.get(o["org_type"] if o else None, ["care"])
        rows = await c.fetch(
            "select id, name, vertical from reference_templates "
            "where vertical = any($1::vertical_t[]) and is_active = true order by name", verticals)
    return [{"id": str(r["id"]), "name": r["name"], "vertical": r["vertical"]} for r in rows]


class DraftEmailIn(BaseModel):
    worker_name: str
    referee_name: str | None = None
    prev_employer_name: str | None = None
    template_id: str | None = None


@app.post("/requests/draft-email")
async def draft_request_email_ep(body: DraftEmailIn, actor=Depends(require_org_actor)):
    """AI-draft the covering email body from the org profile + request details."""
    async with db.pool().acquire() as c:
        o = await c.fetchrow(
            "select name, setup_complete, cqc_provider_id, contact_name, contact_phone, "
            "contact_email from orgs where id = $1", actor["org_id"])
        if not o:
            raise HTTPException(404, "organisation not found")
        if not o["setup_complete"]:
            raise HTTPException(400, "Please complete your organisation setup first (Organisation tab).")
        vertical = None
        if body.template_id:
            t = await c.fetchrow("select vertical from reference_templates where id = $1", body.template_id)
            vertical = t["vertical"] if t else None
    text = await ai.draft_request_email(
        org_name=o["name"], cqc_id=o["cqc_provider_id"], contact_name=o["contact_name"],
        contact_phone=o["contact_phone"], contact_email=o["contact_email"],
        candidate=body.worker_name, prev_employer=body.prev_employer_name,
        referee_name=body.referee_name, vertical=vertical,
    )
    return {"body": text}


# ---- Attachments (private bucket, signed downloads) -------------------------
from fastapi import UploadFile, File
from . import storage as _storage

ATTACH_BUCKET = "attachments"
MAX_ATTACH_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_ATTACH_TYPES = {
    "application/pdf", "image/png", "image/jpeg", "image/jpg",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}


def _safe_name(name: str) -> str:
    keep = "".join(ch if (ch.isalnum() or ch in "._- ") else "_" for ch in (name or "file"))
    return keep[:120] or "file"


async def _store_attachment(c, *, request_id, reference_id, direction, upload, uploaded_by=None):
    raw = await upload.read()
    if len(raw) > MAX_ATTACH_BYTES:
        raise HTTPException(413, "File too large (max 10 MB).")
    ctype = upload.content_type or "application/octet-stream"
    if ctype not in ALLOWED_ATTACH_TYPES:
        raise HTTPException(422, "Unsupported file type. Use PDF, Word, image or text.")
    import secrets as _secrets
    key = f"{request_id or reference_id}/{direction}/{_secrets.token_hex(8)}-{_safe_name(upload.filename)}"
    await _storage.upload(ATTACH_BUCKET, key, raw, ctype)
    row = await c.fetchrow(
        """insert into reference_attachments
             (request_id, reference_id, direction, filename, content_type, byte_size, storage_key, uploaded_by)
           values ($1, $2, $3, $4, $5, $6, $7, $8::uuid)
           returning id""",
        request_id, reference_id, direction, _safe_name(upload.filename), ctype, len(raw), key,
        str(uploaded_by) if uploaded_by else None,
    )
    return {"id": str(row["id"]), "filename": _safe_name(upload.filename), "byte_size": len(raw)}


@app.post("/requests/{request_id}/attachments")
async def upload_outgoing_attachment(request_id: UUID, file: UploadFile = File(...),
                                     actor=Depends(require_org_actor)):
    """Requester uploads an outgoing document (e.g. job description) to their request."""
    if not _storage.configured():
        raise HTTPException(503, "File storage is not configured.")
    async with db.pool().acquire() as c:
        req = await c.fetchrow(
            "select id from reference_requests where id = $1 and requester_org_id = $2",
            request_id, actor["org_id"])
        if not req:
            raise HTTPException(404, "request not found")
        out = await _store_attachment(c, request_id=request_id, reference_id=None,
                                      direction="outgoing", upload=file, uploaded_by=actor["user_id"])
    return out


@app.post("/requests/{token}/attachments-by-link")
async def upload_returned_attachment(token: str, file: UploadFile = File(...)):
    """Referee (no account) uploads a returned document via their secure link token."""
    if not _storage.configured():
        raise HTTPException(503, "File storage is not configured.")
    async with db.pool().acquire() as c:
        req = await c.fetchrow(
            "select id, produced_reference_id from reference_requests where link_token_hash = $1",
            token_hash(token))
        if not req:
            raise HTTPException(404, "this reference link is not valid")
        out = await _store_attachment(c, request_id=req["id"], reference_id=req["produced_reference_id"],
                                      direction="returned", upload=file, uploaded_by=None)
    return out


@app.get("/requests/{request_id}/attachments")
async def list_request_attachments(request_id: UUID, actor=Depends(require_org_actor)):
    """List attachments on a request the caller's org owns (or received)."""
    async with db.pool().acquire() as c:
        req = await c.fetchrow(
            "select id from reference_requests where id = $1 and requester_org_id = $2",
            request_id, actor["org_id"])
        if not req:
            raise HTTPException(404, "request not found")
        rows = await c.fetch(
            "select id, direction, filename, content_type, byte_size, created_at "
            "from reference_attachments where request_id = $1 order by created_at", request_id)
    return [{"id": str(r["id"]), "direction": r["direction"], "filename": r["filename"],
             "content_type": r["content_type"], "byte_size": r["byte_size"],
             "created_at": r["created_at"].isoformat()} for r in rows]


@app.get("/attachments/{attachment_id}/download")
async def download_attachment(attachment_id: UUID, actor=Depends(require_org_actor)):
    """Return a short-lived signed URL, if the caller's org owns the related request."""
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            """select a.storage_key, a.filename, r.requester_org_id
               from reference_attachments a
               join reference_requests r on r.id = a.request_id
               where a.id = $1""", attachment_id)
        if not row:
            raise HTTPException(404, "attachment not found")
        if row["requester_org_id"] != actor["org_id"]:
            raise HTTPException(403, "not permitted")
    url = await _storage.signed_url(ATTACH_BUCKET, row["storage_key"], expires_in=300)
    return {"url": url, "filename": row["filename"]}


@app.get("/requests/{token}/attachments-by-link")
async def list_attachments_by_link(token: str):
    """Referee (no account) lists the OUTGOING attachments on their request, with signed URLs."""
    async with db.pool().acquire() as c:
        req = await c.fetchrow(
            "select id from reference_requests where link_token_hash = $1", token_hash(token))
        if not req:
            raise HTTPException(404, "this reference link is not valid")
        rows = await c.fetch(
            "select id, filename, content_type, byte_size, storage_key "
            "from reference_attachments where request_id = $1 and direction = 'outgoing' "
            "order by created_at", req["id"])
    out = []
    for r in rows:
        try:
            url = await _storage.signed_url(ATTACH_BUCKET, r["storage_key"], expires_in=300)
        except Exception:
            url = None
        out.append({"id": str(r["id"]), "filename": r["filename"],
                    "content_type": r["content_type"], "byte_size": r["byte_size"], "url": url})
    return out


# ---- View a received reference (full content, for the requesting org) --------
@app.get("/received/{reference_id}")
async def received_detail(reference_id: UUID, actor=Depends(require_org_actor)):
    """Full content of a reference that was sent to (and consented for) the caller's org."""
    async with db.pool().acquire() as c:
        send = await c.fetchrow(
            """select s.id, s.consent_status, s.recipient_name, s.created_at as received_at
               from reference_sends s
               where s.reference_id = $1 and s.recipient_org_id = $2""",
            reference_id, actor["org_id"])
        if not send:
            raise HTTPException(404, "reference not found for your organisation")
        if send["consent_status"] != "granted":
            raise HTTPException(403, "this reference has not been released (consent pending or declined)")
        ref = await c.fetchrow(
            """select r.id, r.ref_number, r.content, r.content_hash, r.published_at, r.created_at,
                      r.template_id, w.full_name as worker_name
               from "references" r join workers w on w.id = r.worker_id
               where r.id = $1""", reference_id)
        if not ref:
            raise HTTPException(404, "reference not found")
        tpl = None
        if ref["template_id"]:
            tpl = await c.fetchrow(
                "select name, vertical, field_schema from reference_templates where id = $1",
                ref["template_id"])
        referee = await c.fetchrow(
            "select full_name, job_title, work_email, domain_verified, submitted_at "
            "from referees where reference_id = $1 order by submitted_at desc limit 1", reference_id)
        events = await c.fetch(
            "select event_type, actor_name, created_at, detail from reference_events "
            "where reference_id = $1 order by created_at", reference_id)
        attachments = await c.fetch(
            "select id, direction, filename, content_type, byte_size from reference_attachments "
            "where reference_id = $1 or request_id in "
            "(select id from reference_requests where produced_reference_id = $1) order by created_at",
            reference_id)
    # Notify the worker that their consented reference was viewed (best-effort, deduped per org/day).
    try:
        async with db.pool().acquire() as _vc:
            _already = await _vc.fetchrow(
                "select 1 from reference_events where reference_id = $1 and event_type = 'viewed' "
                "and actor_org_id = $2 and created_at > now() - interval '1 day'",
                reference_id, actor["org_id"])
            if not _already:
                await add_event(_vc, event_type="viewed", reference_id=reference_id,
                                actor_org_id=actor["org_id"], actor_id=actor.get("user_id"),
                                actor_email=actor.get("email"))
                _w = await _vc.fetchrow(
                    'select rr.worker_email, o.name as org_name '
                    'from reference_requests rr join orgs o on o.id = $2 '
                    'where rr.produced_reference_id = $1 limit 1', reference_id, actor["org_id"])
                if _w and _w["worker_email"]:
                    from .requests_mod import reference_viewed_html
                    await email.send_email(
                        _w["worker_email"], f"Your reference was viewed ({ref['ref_number']})",
                        reference_viewed_html(candidate=ref["worker_name"], requester_org=_w["org_name"],
                                              ref_number=ref["ref_number"]))
    except Exception:
        pass

    return {
        "id": str(ref["id"]),
        "ref_number": ref["ref_number"],
        "worker_name": ref["worker_name"],
        "content": ref["content"],
        "content_hash": ref["content_hash"],
        "published_at": ref["published_at"].isoformat() if ref["published_at"] else None,
        "created_at": ref["created_at"].isoformat() if ref["created_at"] else None,
        "received_at": send["received_at"].isoformat() if send["received_at"] else None,
        "consent_status": send["consent_status"],
        "template": ({"name": tpl["name"], "vertical": tpl["vertical"],
                      "field_schema": tpl["field_schema"]} if tpl else None),
        "referee": (dict(referee) | {"submitted_at": referee["submitted_at"].isoformat() if referee["submitted_at"] else None}
                    if referee else None),
        "events": [{"event_type": e["event_type"], "actor_name": e["actor_name"],
                    "created_at": e["created_at"].isoformat() if e["created_at"] else None} for e in events],
        "attachments": [{"id": str(a["id"]), "direction": a["direction"], "filename": a["filename"],
                         "content_type": a["content_type"], "byte_size": a["byte_size"]} for a in attachments],
    }

# ============================================================================
# /v1 webhooks — integrators register a URL to receive signed lifecycle events.
# ============================================================================

class WebhookCreateIn(BaseModel):
    url: str
    events: list[str] | None = None


@app.post("/v1/webhooks", status_code=201)
async def v1_webhook_create(body: WebhookCreateIn, actor=Depends(apikeys.require_api_org)):
    """Register a webhook endpoint. Returns the signing secret ONCE — store it;
    you'll verify the X-Reffolio-Signature header against it."""
    url = (body.url or "").strip()
    if not (url.startswith("https://") or url.startswith("http://")):
        raise HTTPException(422, "url must be an http(s) URL")
    events = body.events or list(webhooks.EVENT_TYPES)
    bad = [e for e in events if e not in webhooks.EVENT_TYPES]
    if bad:
        raise HTTPException(422, {"error": "unknown events", "unknown": bad,
                                  "allowed": list(webhooks.EVENT_TYPES)})
    secret = "whsec_" + secrets.token_urlsafe(32)
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "insert into api_webhooks (org_id, url, secret, events) values ($1,$2,$3,$4) "
            "returning id, url, events, active, created_at",
            actor["org_id"], url, secret, events,
        )
    return {"id": str(row["id"]), "url": row["url"], "events": list(row["events"]),
            "active": row["active"], "secret": secret,
            "note": "Store this secret now — it is not shown again. Verify the "
                    "X-Reffolio-Signature header: sha256=HMAC_SHA256(secret, raw_body)."}


@app.get("/v1/webhooks")
async def v1_webhook_list(actor=Depends(apikeys.require_api_org)):
    """List your registered webhooks (secrets are never returned)."""
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            "select id, url, events, active, created_at, last_delivery_at, last_status "
            "from api_webhooks where org_id = $1 order by created_at desc",
            actor["org_id"],
        )
    return [{"id": str(r["id"]), "url": r["url"], "events": list(r["events"]),
             "active": r["active"],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None,
             "last_delivery_at": r["last_delivery_at"].isoformat() if r["last_delivery_at"] else None,
             "last_status": r["last_status"]} for r in rows]


@app.delete("/v1/webhooks/{webhook_id}")
async def v1_webhook_delete(webhook_id: UUID, actor=Depends(apikeys.require_api_org)):
    """Delete a webhook endpoint."""
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "delete from api_webhooks where id = $1 and org_id = $2 returning id",
            webhook_id, actor["org_id"],
        )
    if not row:
        raise HTTPException(404, "webhook not found")
    return {"deleted": True, "id": str(webhook_id)}


# ---------------------------------------------------------------------------
# Partner provisioning (super-admin). Manual onboarding: create a partner,
# attach an org, and issue an API key tied to both partner and org.
# ---------------------------------------------------------------------------
class PartnerCreateIn(BaseModel):
    name: str
    contact_email: str | None = None
    price_per_ref: float | None = None
    rev_share_pct: float | None = None
    notes: str | None = None


class PartnerAttachOrgIn(BaseModel):
    org_id: UUID


class PartnerIssueKeyIn(BaseModel):
    org_id: UUID
    name: str | None = None


@app.post("/admin/partners", status_code=201)
async def admin_create_partner(body: PartnerCreateIn, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        row = await c.fetchrow(
            "insert into partners (name, contact_email, price_per_ref, rev_share_pct, notes) "
            "values ($1, $2, $3, $4, $5) returning id, created_at",
            body.name.strip()[:200], body.contact_email, body.price_per_ref,
            body.rev_share_pct, body.notes,
        )
    return {"id": str(row["id"]), "created_at": row["created_at"].isoformat()}


@app.get("/admin/partners")
async def admin_list_partners(user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            "select id, name, contact_email, price_per_ref, rev_share_pct, active, created_at "
            "from partners order by created_at desc"
        )
    return [
        {"id": str(r["id"]), "name": r["name"], "contact_email": r["contact_email"],
         "price_per_ref": float(r["price_per_ref"]) if r["price_per_ref"] is not None else None,
         "rev_share_pct": float(r["rev_share_pct"]) if r["rev_share_pct"] is not None else None,
         "active": r["active"], "created_at": r["created_at"].isoformat()}
        for r in rows
    ]


@app.post("/admin/partners/{partner_id}/attach-org")
async def admin_attach_org(partner_id: UUID, body: PartnerAttachOrgIn, user=Depends(require_super_admin)):
    async with db.pool().acquire() as c:
        p = await c.fetchrow("select id from partners where id = $1", partner_id)
        if not p:
            raise HTTPException(404, "partner not found")
        r = await c.fetchrow(
            "update orgs set partner_id = $1 where id = $2 returning id", partner_id, body.org_id)
        if not r:
            raise HTTPException(404, "org not found")
    return {"attached": True, "partner_id": str(partner_id), "org_id": str(body.org_id)}


@app.post("/admin/partners/{partner_id}/issue-key", status_code=201)
async def admin_issue_partner_key(partner_id: UUID, body: PartnerIssueKeyIn, user=Depends(require_super_admin)):
    """Issue an API key tied to BOTH a partner and an org. The partner operates
    through this org; references created with this key attribute to the partner."""
    async with db.pool().acquire() as c:
        p = await c.fetchrow("select id from partners where id = $1", partner_id)
        if not p:
            raise HTTPException(404, "partner not found")
        o = await c.fetchrow("select id from orgs where id = $1", body.org_id)
        if not o:
            raise HTTPException(404, "org not found")
        raw, kh, prefix = apikeys.generate_key()
        row = await c.fetchrow(
            "insert into api_keys (org_id, name, key_hash, prefix, partner_id, created_by) "
            "values ($1, $2, $3, $4, $5, null) returning id, created_at",
            body.org_id, (body.name or "Partner key").strip()[:80], kh, prefix, partner_id,
        )
    return {
        "id": str(row["id"]),
        "partner_id": str(partner_id),
        "org_id": str(body.org_id),
        "key": raw,
        "note": "Store this key now — it is shown only once.",
    }


@app.get("/admin/partners-overview")
async def admin_partners_overview(user=Depends(require_super_admin)):
    """Reconciliation view across all partners: references generated (all-time and
    this calendar month), gross value, partner share, and Reffolio net — using each
    partner's price_per_ref and rev_share_pct. A 'reference' charge is one delta=-1
    row in billing_credits stamped with the partner_id."""
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            """
            with charges as (
                select partner_id,
                       count(*) filter (where reason='reference') as refs_all,
                       count(*) filter (
                           where reason='reference'
                           and created_at >= date_trunc('month', now())
                       ) as refs_month
                from billing_credits
                where partner_id is not null
                group by partner_id
            )
            select p.id, p.name, p.contact_email, p.price_per_ref, p.rev_share_pct,
                   p.active, p.created_at,
                   coalesce(ch.refs_all, 0)   as refs_all,
                   coalesce(ch.refs_month, 0) as refs_month
            from partners p
            left join charges ch on ch.partner_id = p.id
            order by coalesce(ch.refs_all,0) desc, p.created_at desc
            """
        )

    partners = []
    tot_refs_all = tot_refs_month = 0
    tot_gross_all = tot_share_all = tot_net_all = 0.0
    tot_gross_month = tot_share_month = tot_net_month = 0.0

    for r in rows:
        price = float(r["price_per_ref"]) if r["price_per_ref"] is not None else 0.0
        share_pct = float(r["rev_share_pct"]) if r["rev_share_pct"] is not None else 0.0
        refs_all = int(r["refs_all"]); refs_month = int(r["refs_month"])

        gross_all = round(refs_all * price, 2)
        share_all = round(gross_all * share_pct / 100.0, 2)
        net_all = round(gross_all - share_all, 2)

        gross_month = round(refs_month * price, 2)
        share_month = round(gross_month * share_pct / 100.0, 2)
        net_month = round(gross_month - share_month, 2)

        tot_refs_all += refs_all; tot_refs_month += refs_month
        tot_gross_all += gross_all; tot_share_all += share_all; tot_net_all += net_all
        tot_gross_month += gross_month; tot_share_month += share_month; tot_net_month += net_month

        partners.append({
            "id": str(r["id"]), "name": r["name"], "contact_email": r["contact_email"],
            "price_per_ref": price, "rev_share_pct": share_pct, "active": r["active"],
            "all_time":   {"refs": refs_all,   "gross": gross_all,   "partner_share": share_all,   "reffolio_net": net_all},
            "this_month": {"refs": refs_month, "gross": gross_month, "partner_share": share_month, "reffolio_net": net_month},
        })

    return {
        "partners": partners,
        "totals": {
            "all_time":   {"refs": tot_refs_all,   "gross": round(tot_gross_all,2),   "partner_share": round(tot_share_all,2),   "reffolio_net": round(tot_net_all,2)},
            "this_month": {"refs": tot_refs_month, "gross": round(tot_gross_month,2), "partner_share": round(tot_share_month,2), "reffolio_net": round(tot_net_month,2)},
        },
        "month_label": "current calendar month",
    }


@app.get("/partner/overview")
async def partner_overview(actor=Depends(require_org_actor)):
    """Partner-facing dashboard data. The logged-in user's org must be a partner
    home org (orgs.partner_id set). Returns references + revenue scoped to that
    partner across ALL orgs/keys attributed to them. Shows gross and their share."""
    async with db.pool().acquire() as c:
        partner_id = await c.fetchval(
            "select partner_id from orgs where id = $1", actor["org_id"]
        )
        if not partner_id:
            raise HTTPException(403, "this account is not a partner account")

        p = await c.fetchrow(
            "select id, name, price_per_ref, rev_share_pct, active from partners where id = $1",
            partner_id,
        )
        if not p:
            raise HTTPException(404, "partner not found")

        counts = await c.fetchrow(
            """
            select
              count(*) filter (where reason='reference') as refs_all,
              count(*) filter (
                  where reason='reference' and created_at >= date_trunc('month', now())
              ) as refs_month
            from billing_credits
            where partner_id = $1
            """,
            partner_id,
        )

    price = float(p["price_per_ref"]) if p["price_per_ref"] is not None else 0.0
    share_pct = float(p["rev_share_pct"]) if p["rev_share_pct"] is not None else 0.0
    refs_all = int(counts["refs_all"] or 0)
    refs_month = int(counts["refs_month"] or 0)

    def block(refs):
        gross = round(refs * price, 2)
        your_share = round(gross * share_pct / 100.0, 2)
        return {"refs": refs, "gross": gross, "your_share": your_share}

    return {
        "partner": {"name": p["name"], "price_per_ref": price,
                    "rev_share_pct": share_pct, "active": p["active"]},
        "all_time": block(refs_all),
        "this_month": block(refs_month),
        "month_label": "current calendar month",
    }

