

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
