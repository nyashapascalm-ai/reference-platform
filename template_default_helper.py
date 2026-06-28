

async def resolve_default_template(conn, org_id):
    """Return an appropriate template_id for an org that didn't specify one.
    Picks the active template matching the org's vertical; falls back to any
    active template. Returns None only if no templates exist at all."""
    row = await conn.fetchrow(
        """select t.id
           from reference_templates t
           join orgs o on o.vertical = t.vertical
           where o.id = $1 and t.is_active
           order by t.name
           limit 1""",
        org_id,
    )
    if row:
        return row["id"]
    # Fallback: any active template (keeps the flow working even if vertical
    # doesn't match a template for some reason).
    row = await conn.fetchrow(
        "select id from reference_templates where is_active order by name limit 1"
    )
    return row["id"] if row else None
