"""Outbound email via Resend.

Configured with RESEND_API_KEY and EMAIL_FROM. If the key is absent, send_email is a
no-op that returns False — so every feature that uses email degrades gracefully rather
than erroring when email isn't set up yet.
"""
import os

import httpx


async def send_email(to: str, subject: str, html: str) -> bool:
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        return False
    sender = os.environ.get("EMAIL_FROM", "Reference Custody <onboarding@resend.dev>")
    try:
        async with httpx.AsyncClient(timeout=15) as cx:
            r = await cx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {key}"},
                json={"from": sender, "to": [to], "subject": subject, "html": html},
            )
            return r.status_code < 300
    except Exception:
        return False
