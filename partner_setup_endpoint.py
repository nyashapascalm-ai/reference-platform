

class PartnerSetupIn(BaseModel):
    email: str


@app.post("/admin/partners/{partner_id}/setup", status_code=201)
async def admin_setup_partner(partner_id: UUID, body: PartnerSetupIn, user=Depends(require_super_admin)):
    """One-shot partner setup: create the partner's home org (tagged with the
    partner), send a login invite (they click it to create their account and set
    a password), and issue an API key against that home org. Returns the key once
    and the invite link. Idempotent on the home org (reuses it if already made)."""
    email_in = body.email.strip()
    if "@" not in email_in:
        raise HTTPException(422, "a valid email is required")
    async with db.pool().acquire() as c:
        p = await c.fetchrow("select id, name from partners where id = $1", partner_id)
        if not p:
            raise HTTPException(404, "partner not found")

        # Reuse an existing home org for this partner if one exists, else create.
        home = await c.fetchrow(
            "select id from orgs where partner_id = $1 order by created_at limit 1", partner_id
        )
        async with c.transaction():
            if home:
                org_id = home["id"]
            else:
                org = await c.fetchrow(
                    "insert into orgs (name, org_type, vertical, partner_id) "
                    "values ($1, 'care_provider'::org_type_t, 'care'::vertical_t, $2) returning id",
                    f"{p['name']} (partner)"[:200], partner_id,
                )
                org_id = org["id"]

            # Invite (login) — reuse org_invites + token.
            raw_invite, thash = new_share_token()
            await c.execute(
                "insert into org_invites (org_id, email, role, title, token_hash, invited_by, expires_at) "
                "values ($1, $2, 'org_admin'::user_role_t, $3, $4, null, $5)",
                org_id, email_in, "Partner admin", thash, _now() + timedelta(days=14),
            )

            # API key against the home org, tagged to the partner.
            raw_key, kh, prefix = apikeys.generate_key()
            await c.execute(
                "insert into api_keys (org_id, name, key_hash, prefix, partner_id, created_by) "
                "values ($1, $2, $3, $4, $5, null)",
                org_id, "Partner integration key", kh, prefix, partner_id,
            )

    base = os.environ.get("PUBLIC_APP_URL", "https://reference-platform.vercel.app").rstrip("/")
    link = f"{base}/invite/{raw_invite}"
    sent = await email.send_email(
        email_in,
        f"Your Reffolio partner account for {p['name']}",
        f"<p>You've been set up as a Reffolio integration partner for <b>{p['name']}</b>.</p>"
        f"<p>Click below to create your account (set a password) and open your dashboard, "
        f"where you'll see your reference volumes and earnings:</p>"
        f"<p><a href='{link}'>{link}</a></p>"
        f"<p>Use this email address when you sign up.</p>",
    )
    return {
        "ok": True,
        "invite_sent": bool(sent),
        "invite_link": link,
        "org_id": str(org_id),
        "api_key": raw_key,
        "partner_id": str(partner_id),
    }
