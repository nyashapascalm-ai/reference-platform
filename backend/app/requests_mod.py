"""References Received: employer-to-employer request flow helpers.

A hiring provider creates a request about a candidate. The previous employer
(referee) completes it on a secure link without needing an account. On
completion a frozen, hashed reference is produced, stored at org level with a
permanent reference number, sent to the requester, and the worker is notified.

This module holds the small reusable pieces; the endpoints live in main.py.
"""
import secrets
from . import db


# ---- reference numbers -------------------------------------------------------
def new_ref_number() -> str:
    """REF-XXXX-XXXX, uppercase hex, matching the migration's format."""
    a = secrets.token_hex(2).upper()
    b = secrets.token_hex(2).upper()
    return f"REF-{a}-{b}"


# ---- audit trail -------------------------------------------------------------
async def add_event(conn, *, event_type, reference_id=None, request_id=None,
                    actor_org_id=None, actor_id=None, actor_name=None,
                    actor_email=None, detail=None, ip_address=None):
    """Append one row to the append-only reference_events audit trail.
    Never raises out: auditing must not break the main operation."""
    try:
        await conn.execute(
            "insert into reference_events "
            "(reference_id, request_id, event_type, actor_org_id, actor_id, "
            " actor_name, actor_email, detail, ip_address) "
            "values ($1, $2, $3, $4, $5::uuid, $6, $7, $8::jsonb, $9::inet)",
            reference_id, request_id, event_type, actor_org_id,
            str(actor_id) if actor_id else None, actor_name, actor_email,
            _json(detail), str(ip_address) if ip_address else None,
        )
    except Exception:
        pass


def _json(obj):
    import json
    if obj is None:
        return None
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


# ---- email bodies ------------------------------------------------------------
def request_email_html(*, candidate, requester_org, referee_name, link, message):
    greeting = f"Dear {referee_name}," if referee_name else "Hello,"
    extra = f"<p>{message}</p>" if message else ""
    return f"""
      <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#1a1a2e">
        <h2 style="color:#6C5CE7">Reference request</h2>
        <p>{greeting}</p>
        <p><b>{requester_org}</b> has requested an employment reference for
           <b>{candidate}</b>, who has named you as a referee from a previous role.</p>
        {extra}
        <p>You can complete it securely online \u2014 no account needed. It takes a few minutes.</p>
        <p><a href="{link}" style="display:inline-block;background:#6C5CE7;color:#fff;
           text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600">
           Complete the reference</a></p>
        <p style="font-size:13px;color:#666">If the button doesn't work, paste this link:<br>{link}</p>
        <p style="font-size:12px;color:#999;margin-top:24px">Sent via Reffolio on behalf of {requester_org}.
           If you weren't expecting this, you can ignore it.</p>
      </div>"""


def received_email_html(*, candidate, referee_name, ref_number, link):
    return f"""
      <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#1a1a2e">
        <h2 style="color:#6C5CE7">Reference received</h2>
        <p>The reference you requested for <b>{candidate}</b> has been completed
           {("by " + referee_name) if referee_name else ""}.</p>
        <p>Reference number: <b>{ref_number}</b></p>
        <p><a href="{link}" style="display:inline-block;background:#6C5CE7;color:#fff;
           text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600">
           View in Reffolio</a></p>
        <p style="font-size:12px;color:#999;margin-top:24px">It's stored in your Received references for
           your records and inspections.</p>
      </div>"""


def worker_notice_html(*, candidate, requester_org, ref_number):
    return f"""
      <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#1a1a2e">
        <h2 style="color:#6C5CE7">A reference about you was completed</h2>
        <p>Hello {candidate},</p>
        <p>A previous employer has completed an employment reference about you,
           requested by <b>{requester_org}</b>.</p>
        <p>Your reference number is <b>{ref_number}</b>. Keep it \u2014 in future you can ask a previous
           employer to send this same reference to a new employer using this number, instead of
           starting from scratch.</p>
        <p>You can create a free Reffolio account to see references about you and manage your consent.</p>
        <p style="font-size:12px;color:#999;margin-top:24px">Reffolio \u2014 verified, tamper-evident references.</p>
      </div>"""
