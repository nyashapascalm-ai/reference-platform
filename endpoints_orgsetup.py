

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
