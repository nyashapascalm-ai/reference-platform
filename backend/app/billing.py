"""Stripe billing for Reffolio.

One billing record per organisation. Per-seat subscription plans, plus a
pay-as-you-go credit ledger for occasional verifiers. Stripe is the source of
truth for subscription state; we mirror it into billing_customers via webhooks.

Degrades gracefully: if STRIPE_SECRET_KEY isn't set, checkout/portal raise a
clear error but the rest of the app (and the free tier) keep working.
"""
import os
from datetime import datetime, timezone

import stripe

# Plan definitions — seats is the billing unit (per manager seat).
PLANS = {
    "free":       {"seats": 2,      "api": False, "white_label": False, "label": "Free"},
    "starter":    {"seats": 3,      "api": False, "white_label": False, "label": "Team Starter"},
    "growth":     {"seats": 10,     "api": True,  "white_label": True,  "label": "Growth"},
    "enterprise": {"seats": 100000, "api": True,  "white_label": True,  "label": "Enterprise"},
}
_PRICE_ENV = {"starter": "STRIPE_PRICE_STARTER", "growth": "STRIPE_PRICE_GROWTH", "enterprise": "STRIPE_PRICE_ENTERPRISE"}


def configured() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def enforce() -> bool:
    return os.environ.get("BILLING_ENFORCE", "").lower() in ("1", "true", "yes")


def _init():
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise RuntimeError("billing is not configured")
    stripe.api_key = key


def plan_price(plan: str):
    env = _PRICE_ENV.get(plan)
    return os.environ.get(env) if env else None


def price_to_plan() -> dict:
    m = {}
    for plan, env in _PRICE_ENV.items():
        pid = os.environ.get(env)
        if pid:
            m[pid] = plan
    return m


def features(plan: str) -> dict:
    p = PLANS.get(plan, PLANS["free"])
    return {"plan": plan, "label": p["label"], "seats": p["seats"], "api": p["api"], "white_label": p["white_label"]}


# ---- DB helpers (async, take an asyncpg connection) ----
async def get_billing(conn, org_id):
    row = await conn.fetchrow("select * from billing_customers where org_id = $1", org_id)
    if not row:
        await conn.execute("insert into billing_customers (org_id) values ($1) on conflict do nothing", org_id)
        row = await conn.fetchrow("select * from billing_customers where org_id = $1", org_id)
    return row


async def credits_balance(conn, org_id) -> int:
    v = await conn.fetchval("select coalesce(sum(delta),0) from billing_credits where org_id = $1", org_id)
    return int(v or 0)


async def seats_used(conn, org_id) -> int:
    members = await conn.fetchval("select count(*) from profiles where org_id = $1", org_id)
    pending = await conn.fetchval("select count(*) from org_invites where org_id = $1 and accepted_at is null", org_id)
    return int(members or 0) + int(pending or 0)


# ---- Stripe operations ----
async def get_or_create_customer(conn, org_id, org_name, email) -> str:
    row = await get_billing(conn, org_id)
    if row["stripe_customer_id"]:
        return row["stripe_customer_id"]
    _init()
    cust = stripe.Customer.create(name=org_name, email=email, metadata={"org_id": str(org_id)})
    await conn.execute(
        "update billing_customers set stripe_customer_id = $2, updated_at = now() where org_id = $1",
        org_id, cust["id"],
    )
    return cust["id"]


def checkout_subscription(customer_id, price_id, success_url, cancel_url, org_id) -> str:
    _init()
    s = stripe.checkout.Session.create(
        mode="subscription", customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url, cancel_url=cancel_url,
        metadata={"org_id": str(org_id)},
    )
    return s["url"]


def checkout_credits(customer_id, price_id, quantity, success_url, cancel_url, org_id) -> str:
    _init()
    s = stripe.checkout.Session.create(
        mode="payment", customer=customer_id,
        line_items=[{"price": price_id, "quantity": quantity}],
        success_url=success_url, cancel_url=cancel_url,
        metadata={"org_id": str(org_id), "credits": str(quantity)},
    )
    return s["url"]


def billing_portal(customer_id, return_url) -> str:
    _init()
    s = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return s["url"]


# ---- Webhook handling (async; takes parsed event + connection) ----
async def handle_event(event: dict, conn) -> None:
    t = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}

    if t == "checkout.session.completed" and obj.get("mode") == "payment":
        md = obj.get("metadata") or {}
        org_id = md.get("org_id")
        qty = int(md.get("credits") or 0)
        if org_id and qty:
            await conn.execute(
                "insert into billing_credits (org_id, delta, reason) values ($1, $2, 'purchase')",
                org_id, qty,
            )

    elif t in ("customer.subscription.created", "customer.subscription.updated"):
        cust = obj.get("customer")
        status = obj.get("status", "active")
        items = (obj.get("items") or {}).get("data") or []
        price = items[0]["price"]["id"] if items else None
        plan = price_to_plan().get(price, "free")
        seats = PLANS.get(plan, PLANS["free"])["seats"]
        pe = obj.get("current_period_end")
        pe_ts = datetime.fromtimestamp(pe, tz=timezone.utc) if pe else None
        await conn.execute(
            "update billing_customers set plan=$2, status=$3, seats=$4, stripe_subscription_id=$5, "
            "current_period_end=$6, updated_at=now() where stripe_customer_id=$1",
            cust, plan, status, seats, obj.get("id"), pe_ts,
        )

    elif t == "customer.subscription.deleted":
        cust = obj.get("customer")
        await conn.execute(
            "update billing_customers set plan='free', status='canceled', seats=$2, updated_at=now() "
            "where stripe_customer_id=$1",
            cust, PLANS["free"]["seats"],
        )

    elif t == "invoice.payment_failed":
        cust = obj.get("customer")
        if cust:
            await conn.execute(
                "update billing_customers set status='past_due', updated_at=now() where stripe_customer_id=$1",
                cust,
            )
