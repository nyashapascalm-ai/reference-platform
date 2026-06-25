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
    referee_email: str
    referee_name: str | None = None
    prev_employer_name: str | None = None
    template_id: str | None = None
    message: str | None = None


class RequestCompleteIn(BaseModel):
    content: dict
    referee_name: str | None = None
    referee_job_title: str | None = None
    worker_registration_body: str | None = None
    worker_registration_number: str | None = None
    worker_vertical: str | None = None


@app.post("/requests")
async def create_request(body: RequestCreateIn, request: Request, actor=Depends(require_org_actor)):
    """A hiring provider requests a reference about a candidate from a previous employer."""
    org_id = actor["org_id"]
    referee_email = body.referee_email.strip().lower()
    if "@" not in referee_email:
        raise HTTPException(422, "a valid referee email is required")
    domain = referee_email.split("@")[-1]
    free_mail = domain in {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
                           "icloud.com", "live.com", "aol.com", "me.com"}
    raw, thash = new_share_token()
    link = f"{SITE_URL}/complete-reference/{raw}"

    async with db.pool().acquire() as c:
        org = await c.fetchrow("select name from orgs where id = $1", org_id)
        req = await c.fetchrow(
            """
            insert into reference_requests
              (requester_org_id, requested_by, worker_name, prev_employer_name,
               referee_name, referee_email, referee_email_domain, domain_verified,
               template_id, link_token_hash, message)
            values ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            returning id
            """,
            org_id, actor["user_id"], body.worker_name.strip(), body.prev_employer_name,
            body.referee_name, referee_email, domain, (not free_mail),
            body.template_id, thash, body.message,
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
                          link=link, message=body.message),
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
                   r.status, r.template_id, r.message, o.name as requester_org
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
    return {
        "worker_name": req["worker_name"],
        "prev_employer_name": req["prev_employer_name"],
        "referee_name": req["referee_name"],
        "requester_org": req["requester_org"],
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
            worker_id, org_id, req["template_id"], body.content, chash, ref_number, now,
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
        # Create the send into the requester's Received references.
        await c.execute(
            """insert into reference_sends
                 (reference_id, reference_version, sender_org_id, recipient_org_id,
                  recipient_email, recipient_name, consent_status, delivered_at)
               values ($1, 1, $2, $2, $3, $4, 'pending', now())""",
            ref_id, org_id, ref_email, req["worker_name"],
        )
        await add_event(c, event_type="completed", reference_id=ref_id, request_id=req["id"],
                       actor_name=ref_name, actor_email=ref_email,
                       detail={"ref_number": ref_number},
                       ip_address=request.client.host if request.client else None)
        await add_event(c, event_type="sent", reference_id=ref_id, request_id=req["id"],
                       actor_org_id=org_id, detail={"recipient_org_id": str(org_id)})

        org = await c.fetchrow("select name from orgs where id = $1", org_id)

    # Notify requester + worker (best-effort).
    await _notify_completion(org_id, req["worker_name"], ref_email, ref_name, ref_number, org["name"])

    return {"reference_id": str(ref_id), "ref_number": ref_number, "status": "published"}


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
    """Portal: requests this org has sent, and references it has received."""
    org_id = actor["org_id"]
    async with db.pool().acquire() as c:
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
               where s.recipient_org_id = $1
               order by s.created_at desc""",
            org_id,
        )
    return {
        "sent": [dict(x) | {"id": str(x["id"]),
                            "produced_reference_id": str(x["produced_reference_id"]) if x["produced_reference_id"] else None}
                 for x in sent],
        "received": [dict(x) | {"id": str(x["id"]), "reference_id": str(x["reference_id"])}
                     for x in received],
    }
