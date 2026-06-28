

async def assert_credits(conn, org_id):
    """Raise 402 if per-reference metering is on AND the org is out of credits.
    Only gates NEW reference requests (the chargeable action). Reading or
    downloading existing references is never blocked. Dormant unless
    BILLING_METER is enabled, so it does nothing until metering goes live."""
    if not metering_enabled():
        return
    bal = await credits_balance(conn, org_id)
    if bal <= 0:
        from fastapi import HTTPException
        raise HTTPException(
            402,
            "Out of reference credits. Top up to request new references. "
            "Your existing references remain accessible.",
        )
