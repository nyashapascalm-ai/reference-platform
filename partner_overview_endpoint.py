

@app.get("/partner/overview")
async def partner_overview(actor=Depends(require_org_actor)):
    """Partner-facing dashboard data. The logged-in user's org must be a partner
    home org (orgs.partner_id set). Returns references + revenue scoped to that
    partner across ALL orgs/keys attributed to them. Shows gross and their share."""
    async with db.pool().acquire() as c:
        partner_id = await c.fetchval(
            "select partner_id from orgs where id = $1", actor["org_id"]
        )
        if not partner_id:
            raise HTTPException(403, "this account is not a partner account")

        p = await c.fetchrow(
            "select id, name, price_per_ref, rev_share_pct, active from partners where id = $1",
            partner_id,
        )
        if not p:
            raise HTTPException(404, "partner not found")

        counts = await c.fetchrow(
            """
            select
              count(*) filter (where reason='reference') as refs_all,
              count(*) filter (
                  where reason='reference' and created_at >= date_trunc('month', now())
              ) as refs_month
            from billing_credits
            where partner_id = $1
            """,
            partner_id,
        )

    price = float(p["price_per_ref"]) if p["price_per_ref"] is not None else 0.0
    share_pct = float(p["rev_share_pct"]) if p["rev_share_pct"] is not None else 0.0
    refs_all = int(counts["refs_all"] or 0)
    refs_month = int(counts["refs_month"] or 0)

    def block(refs):
        gross = round(refs * price, 2)
        your_share = round(gross * share_pct / 100.0, 2)
        return {"refs": refs, "gross": gross, "your_share": your_share}

    return {
        "partner": {"name": p["name"], "price_per_ref": price,
                    "rev_share_pct": share_pct, "active": p["active"]},
        "all_time": block(refs_all),
        "this_month": block(refs_month),
        "month_label": "current calendar month",
    }
