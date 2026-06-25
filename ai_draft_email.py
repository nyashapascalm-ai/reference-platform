

async def draft_request_email(*, org_name, cqc_id, contact_name, contact_phone,
                              contact_email, candidate, prev_employer, referee_name,
                              vertical=None):
    """Draft the BODY of a covering email a hiring org sends to a referee when
    requesting a reference. Returns plain text (Reffolio adds the secure link
    and footer separately). Vertical-aware register."""
    p = _profile(vertical)
    contact_bits = []
    if contact_name:
        contact_bits.append(contact_name)
    if contact_phone:
        contact_bits.append(f"Tel: {contact_phone}")
    if contact_email:
        contact_bits.append(contact_email)
    contact_block = "\n".join(contact_bits) if contact_bits else org_name
    reg = f" (CQC/registration: {cqc_id})" if cqc_id else ""

    system = (
        f"You write short, professional covering emails that a UK employer in "
        f"{p['sector']} sends to a candidate's previous employer to request an "
        "employment reference. The tone is courteous, concise and plain. "
        "Write ONLY the email body as plain text. Do NOT include a subject line, "
        "do NOT include any link or button (the platform adds the secure link "
        "separately), and do NOT invent facts. End with the sender's contact "
        "details exactly as provided. Keep it under 160 words."
    )
    user = (
        f"Requesting organisation: {org_name}{reg}.\n"
        f"Candidate being hired: {candidate}.\n"
        f"Previous employer (the referee's organisation): {prev_employer or 'not specified'}.\n"
        f"Referee name: {referee_name or 'not specified'}.\n"
        f"Sender contact block to end with:\n{contact_block}\n\n"
        "Write the covering email body. Mention that the organisation is hiring "
        "the candidate and is seeking an employment reference, that safeguarding "
        "of vulnerable people makes references important, and that the reference "
        "can be completed securely online via the link provided below (the platform "
        "inserts it). Address the referee by name if provided."
    )
    return (await _complete(system, user, max_tokens=500)).strip()
