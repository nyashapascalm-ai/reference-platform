

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
