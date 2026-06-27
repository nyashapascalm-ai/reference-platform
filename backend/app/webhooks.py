"""Outbound webhooks for the /v1 API.

Lets an integrator register a URL that Reffolio POSTs to when key lifecycle
events happen (referee_submitted, consent_granted, reference_received).
Each delivery is signed with HMAC-SHA256 over the raw body using the webhook's
secret, sent as the `X-Reffolio-Signature: sha256=<hex>` header, so the
integrator can verify authenticity. All delivery is best-effort: a failing or
slow webhook never blocks or breaks the reference flow.
"""
import hashlib
import hmac
import json
import os

import httpx

EVENT_TYPES = ("referee_submitted", "consent_granted", "reference_received")
_TIMEOUT = float(os.environ.get("WEBHOOK_TIMEOUT_SECONDS", "5"))


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def fire(conn, org_id, event_type: str, payload: dict) -> None:
    """Deliver `event_type` to every active webhook for `org_id` subscribed to it.
    Best-effort: swallows all errors, records last status. Never raises."""
    try:
        hooks = await conn.fetch(
            "select id, url, secret, events from api_webhooks "
            "where org_id = $1 and active = true",
            org_id,
        )
    except Exception:
        return
    if not hooks:
        return

    envelope = {"event": event_type, "data": payload}
    body = json.dumps(envelope, separators=(",", ":"), default=str).encode("utf-8")

    for h in hooks:
        events = h["events"] or []
        if event_type not in events:
            continue
        sig = sign(h["secret"], body)
        status = None
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    h["url"],
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Reffolio-Signature": sig,
                        "X-Reffolio-Event": event_type,
                        "User-Agent": "Reffolio-Webhooks/1.0",
                    },
                )
                status = resp.status_code
        except Exception:
            status = None
        try:
            await conn.execute(
                "update api_webhooks set last_delivery_at = now(), last_status = $2 where id = $1",
                h["id"], status,
            )
        except Exception:
            pass
