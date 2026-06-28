

@app.get("/admin/partners-overview")
async def admin_partners_overview(user=Depends(require_super_admin)):
    """Reconciliation view across all partners: references generated (all-time and
    this calendar month), gross value, partner share, and Reffolio net — using each
    partner's price_per_ref and rev_share_pct. A 'reference' charge is one delta=-1
    row in billing_credits stamped with the partner_id."""
    async with db.pool().acquire() as c:
        rows = await c.fetch(
            """
            with charges as (
                select partner_id,
                       count(*) filter (where reason='reference') as refs_all,
                       count(*) filter (
                           where reason='reference'
                           and created_at >= date_trunc('month', now())
                       ) as refs_month
                from billing_credits
                where partner_id is not null
                group by partner_id
            )
            select p.id, p.name, p.contact_email, p.price_per_ref, p.rev_share_pct,
                   p.active, p.created_at,
                   coalesce(ch.refs_all, 0)   as refs_all,
                   coalesce(ch.refs_month, 0) as refs_month
            from partners p
            left join charges ch on ch.partner_id = p.id
            order by coalesce(ch.refs_all,0) desc, p.created_at desc
            """
        )

    partners = []
    tot_refs_all = tot_refs_month = 0
    tot_gross_all = tot_share_all = tot_net_all = 0.0
    tot_gross_month = tot_share_month = tot_net_month = 0.0

    for r in rows:
        price = float(r["price_per_ref"]) if r["price_per_ref"] is not None else 0.0
        share_pct = float(r["rev_share_pct"]) if r["rev_share_pct"] is not None else 0.0
        refs_all = int(r["refs_all"]); refs_month = int(r["refs_month"])

        gross_all = round(refs_all * price, 2)
        share_all = round(gross_all * share_pct / 100.0, 2)
        net_all = round(gross_all - share_all, 2)

        gross_month = round(refs_month * price, 2)
        share_month = round(gross_month * share_pct / 100.0, 2)
        net_month = round(gross_month - share_month, 2)

        tot_refs_all += refs_all; tot_refs_month += refs_month
        tot_gross_all += gross_all; tot_share_all += share_all; tot_net_all += net_all
        tot_gross_month += gross_month; tot_share_month += share_month; tot_net_month += net_month

        partners.append({
            "id": str(r["id"]), "name": r["name"], "contact_email": r["contact_email"],
            "price_per_ref": price, "rev_share_pct": share_pct, "active": r["active"],
            "all_time":   {"refs": refs_all,   "gross": gross_all,   "partner_share": share_all,   "reffolio_net": net_all},
            "this_month": {"refs": refs_month, "gross": gross_month, "partner_share": share_month, "reffolio_net": net_month},
        })

    return {
        "partners": partners,
        "totals": {
            "all_time":   {"refs": tot_refs_all,   "gross": round(tot_gross_all,2),   "partner_share": round(tot_share_all,2),   "reffolio_net": round(tot_net_all,2)},
            "this_month": {"refs": tot_refs_month, "gross": round(tot_gross_month,2), "partner_share": round(tot_share_month,2), "reffolio_net": round(tot_net_month,2)},
        },
        "month_label": "current calendar month",
    }
