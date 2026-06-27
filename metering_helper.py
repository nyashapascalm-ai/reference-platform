

def metering_enabled() -> bool:
    """Per-reference metering is opt-in via BILLING_METER, so it never surprises
    existing subscription customers. When off, references are never charged."""
    return os.environ.get("BILLING_METER", "").lower() in ("1", "true", "yes")


async def consume_reference_credit(conn, org_id, ref_id) -> None:
    """Charge one credit for a verified (consent-granted) reference.
    Idempotent: the unique index on (org_id, ref_id) where reason='reference'
    guarantees a reference is charged at most once, even if called twice.
    Best-effort: never raises into the reference flow."""
    if not metering_enabled():
        return
    try:
        await conn.execute(
            "insert into billing_credits (org_id, delta, reason, ref_id) "
            "values ($1, -1, 'reference', $2) "
            "on conflict (org_id, ref_id) where reason = 'reference' and ref_id is not null "
            "do nothing",
            org_id, ref_id,
        )
    except Exception:
        # Metering must never break reference delivery.
        pass
