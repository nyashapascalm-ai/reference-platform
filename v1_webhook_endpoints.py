

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
