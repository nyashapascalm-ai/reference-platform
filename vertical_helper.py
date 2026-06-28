

# Accepted vertical hints from API partners -> mapped to the org's template pool.
_VERTICAL_ALIASES = {
    "care": "care", "social_care": "care", "cqc": "care",
    "health": "healthcare", "healthcare": "healthcare", "nhs": "healthcare",
    "nmc": "healthcare", "hcpc": "healthcare",
    "education": "teaching", "teaching": "teaching", "school": "teaching",
    "kcsie": "teaching",
    "social_work": "social_work", "socialwork": "social_work", "swe": "social_work",
}


async def resolve_template_for_vertical(conn, vertical_hint):
    """Map a partner-supplied vertical hint (e.g. 'care', 'nhs') to an active
    template id. Returns None if the hint is unknown or no template matches,
    so the caller can fall back to the org default."""
    if not vertical_hint:
        return None
    key = _VERTICAL_ALIASES.get(str(vertical_hint).strip().lower())
    if not key:
        return None
    row = await conn.fetchrow(
        "select id from reference_templates where vertical = $1::vertical_t "
        "and is_active order by name limit 1",
        key,
    )
    return row["id"] if row else None
