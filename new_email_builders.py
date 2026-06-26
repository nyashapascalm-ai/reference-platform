

def referee_opened_html(*, candidate, referee_name, ref_hint=None):
    who = referee_name or "The referee"
    inner = (
        '<h2 style="color:#6C5CE7">Your reference request was opened</h2>'
        f'<p>{who} has opened the reference request for <b>{candidate}</b> but has not submitted it yet.</p>'
        '<p>No action is needed from you. We will let you know as soon as it is completed and the '
        'candidate has given consent.</p>'
    )
    return _branded_shell(inner_html=inner)


def referee_submitted_html(*, candidate, requester_org, ref_number):
    inner = (
        '<h2 style="color:#6C5CE7">Thank you \u2014 reference submitted</h2>'
        f'<p>Thank you for completing the reference for <b>{candidate}</b> on behalf of {requester_org}.</p>'
        f'<p>It has been recorded securely with reference number <b>{ref_number}</b>. '
        'The reference is released to the requesting organisation once the candidate gives consent.</p>'
        '<p>You can close this safely \u2014 no account is needed. If you would like to keep track of '
        'references you provide, you can create a free Reffolio account.</p>'
    )
    return _branded_shell(inner_html=inner)


def completed_awaiting_consent_html(*, candidate, referee_name, ref_number):
    who = referee_name or "The referee"
    inner = (
        '<h2 style="color:#6C5CE7">Reference completed \u2014 awaiting consent</h2>'
        f'<p>{who} has completed the reference for <b>{candidate}</b> (reference '
        f'<b>{ref_number}</b>).</p>'
        '<p>The candidate has been asked to give consent. As soon as they approve, the reference '
        'will appear in your Received references.</p>'
    )
    return _branded_shell(inner_html=inner)


def consent_confirmed_html(*, candidate, requester_org, ref_number):
    inner = (
        '<h2 style="color:#6C5CE7">Thank you \u2014 consent recorded</h2>'
        f'<p>You approved the release of your reference (<b>{ref_number}</b>) to {requester_org}.</p>'
        '<p>It has now been shared with them. No further action is needed.</p>'
    )
    return _branded_shell(inner_html=inner)


def reference_viewed_html(*, candidate, requester_org, ref_number):
    inner = (
        '<h2 style="color:#6C5CE7">Your reference was viewed</h2>'
        f'<p>{requester_org} has viewed your reference (<b>{ref_number}</b>), which you consented '
        'to share with them.</p>'
        '<p>This is a routine notification for your records. No action is needed.</p>'
    )
    return _branded_shell(inner_html=inner)
