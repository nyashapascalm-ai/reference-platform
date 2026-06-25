

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
