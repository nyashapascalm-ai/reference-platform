

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
