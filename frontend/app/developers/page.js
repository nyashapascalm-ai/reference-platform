'use client';
import Link from 'next/link';
import '../marketing.css';
import MarketingNav from '../../components/MarketingNav';
import MarketingFooter from '../../components/MarketingFooter';

const BASE = 'https://reference-platform-production.up.railway.app';

const ENDPOINTS = [
  { m: 'POST', p: '/v1/requests', d: 'Request a reference about a candidate from a previous employer. Reffolio emails the referee a secure link and, once completed, asks the candidate to consent — exactly as the dashboard does.',
    req: '{\n  "worker_name": "Sam Jones",\n  "worker_email": "sam@example.com",\n  "referee_email": "manager@previousemployer.co.uk",\n  "referee_name": "A. Manager",\n  "prev_employer_name": "Previous Employer Ltd",\n  "template_id": null,\n  "message": "Optional note shown to the referee."\n}',
    res: '{\n  "request_id": "...",\n  "status": "pending",\n  "email_sent": true,\n  "domain_verified": true\n}' },
  { m: 'GET', p: '/v1/requests/{id}', d: 'Poll one request: its lifecycle status, and the produced reference + consent state once available.',
    res: '{\n  "request_id": "...",\n  "status": "received",\n  "candidate_name": "Sam Jones",\n  "referee_email": "manager@previousemployer.co.uk",\n  "consent_status": "granted",\n  "reference": {\n    "reference_id": "...",\n    "ref_number": "REF-2026-000123",\n    "content_hash": "770c44...",\n    "readable": true\n  }\n}' },
  { m: 'GET', p: '/v1/requests', d: 'List your organisation’s reference requests with their current lifecycle status.',
    res: '[\n  { "request_id": "...", "status": "awaiting_consent", "candidate_name": "Sam Jones", "consent_status": "pending" }\n]' },
  { m: 'GET', p: '/v1/references/{id}', d: 'Fetch a received reference’s full content. Only references sent to your organisation with consent granted are readable.',
    res: '{\n  "reference_id": "...",\n  "ref_number": "REF-2026-000123",\n  "candidate_name": "Sam Jones",\n  "sector": "care",\n  "content": { "...": "..." },\n  "content_hash": "770c44...",\n  "consent_status": "granted"\n}' },
];

const WEBHOOK_ENDPOINTS = [
  { m: 'POST', p: '/v1/webhooks', d: 'Register an endpoint to receive signed event deliveries. The signing secret is returned ONCE.',
    req: '{\n  "url": "https://your-system.example.com/reffolio/hook",\n  "events": ["referee_submitted", "consent_granted", "reference_received"]\n}',
    res: '{\n  "id": "...",\n  "url": "https://your-system.example.com/reffolio/hook",\n  "events": ["referee_submitted", "consent_granted", "reference_received"],\n  "active": true,\n  "secret": "whsec_..."\n}' },
  { m: 'GET', p: '/v1/webhooks', d: 'List your registered webhooks and their last delivery status. Secrets are never returned.',
    res: '[\n  { "id": "...", "url": "...", "events": ["..."], "active": true, "last_status": 200 }\n]' },
  { m: 'DELETE', p: '/v1/webhooks/{id}', d: 'Delete a webhook endpoint.',
    res: '{\n  "deleted": true,\n  "id": "..."\n}' },
];

const EVENTS = [
  ['referee_submitted', 'The previous employer has completed the reference. It is held pending the candidate’s consent.'],
  ['consent_granted', 'The candidate has consented; the reference is now released to you.'],
  ['reference_received', 'Fired alongside consent_granted — the reference is now readable via GET /v1/references/{id}.'],
];

const LIFECYCLE = [
  ['pending', 'Request created; the referee has been emailed but hasn’t opened the link.'],
  ['opened', 'The referee has opened the secure link.'],
  ['awaiting_consent', 'The referee has completed the reference; waiting for the candidate to consent.'],
  ['received', 'The candidate consented; the reference is readable.'],
  ['declined', 'The candidate declined consent; the reference is not released.'],
];

const ERRORS = [
  ['401', 'Missing or invalid API key, or the key was revoked.'],
  ['402', 'Your plan does not include API access. Upgrade to Growth or Business.'],
  ['403', 'The resource belongs to another organisation, or consent has not been granted.'],
  ['404', 'The request, reference or webhook was not found.'],
  ['422', 'Validation error (e.g. a required field is missing or the URL is invalid).'],
];

function Code({ children }) {
  return <pre style={{ background: '#0c1020', color: '#e6e9f5', padding: '14px 16px', borderRadius: 10, overflowX: 'auto', fontSize: 13, lineHeight: 1.5, margin: '8px 0' }}><code>{children}</code></pre>;
}

function EndpointCard({ e }) {
  const colour = e.m === 'GET' ? ['#e7f5ff', '#1c7ed6'] : e.m === 'DELETE' ? ['#ffe3e3', '#e03131'] : ['#fff4e6', '#e8590c'];
  return (
    <div style={{ border: '1px solid var(--line, #e7e9f2)', borderRadius: 12, padding: 16, margin: '12px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 12, padding: '2px 8px', borderRadius: 6, background: colour[0], color: colour[1] }}>{e.m}</span>
        <code style={{ fontFamily: 'monospace', fontSize: 14 }}>{e.p}</code>
      </div>
      <p style={{ margin: '8px 0' }}>{e.d}</p>
      {e.req && <><div style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 700 }}>Request body</div><Code>{e.req}</Code></>}
      <div style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 700 }}>Response</div><Code>{e.res}</Code>
    </div>
  );
}

export default function Developers() {
  return (
    <div className="mk">
      <MarketingNav />
      <section className="mk-pagehero">
        <div className="mk-container">
          <div className="mk-kicker" style={{ color: 'var(--violet)', fontWeight: 700, letterSpacing: '.08em' }}>DEVELOPERS</div>
          <h1 style={{ marginTop: 12 }}>Reffolio API</h1>
          <p>Request employment references programmatically, track them through to consent, and receive the verified record — with webhooks or polling. Available on the Growth and Business plans.</p>
        </div>
      </section>

      <section className="mk-section" style={{ paddingTop: 16 }}>
        <div className="mk-container" style={{ maxWidth: 860 }}>

          <h2 style={{ fontSize: 24 }}>How it works</h2>
          <p>The API mirrors the Reffolio workflow exactly. You create a request; Reffolio emails the previous employer a secure link; they complete a sector-specific form; the candidate consents; you receive a verified, tamper-evident record. You can be notified by webhook at each step, or poll for status.</p>
          <ol style={{ lineHeight: 1.7 }}>
            <li>Create a request — <code>POST /v1/requests</code> — get a <code>request_id</code> (status <code>pending</code>).</li>
            <li>The referee completes the reference — you receive a <code>referee_submitted</code> webhook (status becomes <code>awaiting_consent</code>).</li>
            <li>The candidate consents — you receive <code>consent_granted</code> and <code>reference_received</code> (status becomes <code>received</code>).</li>
            <li>Read the reference — <code>GET /v1/references/{'{id}'}</code>.</li>
          </ol>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Authentication</h2>
          <p>An organisation admin generates keys in the dashboard under <b>API</b>. The full key (<code>rfl_live_{'\u2026'}</code>) is shown once — store it securely. Send it as a bearer token on every request:</p>
          <Code>{`Authorization: Bearer rfl_live_EXAMPLEKEY1234567890`}</Code>
          <p>Base URL:</p>
          <Code>{BASE}</Code>
          <p>A quick check from your terminal:</p>
          <Code>{`curl -H "Authorization: Bearer rfl_live_..." \\\n  ${BASE}/v1/ping`}</Code>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Requests &amp; references</h2>
          {ENDPOINTS.map((e) => <EndpointCard key={e.p} e={e} />)}

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Request lifecycle</h2>
          <p>The <code>status</code> field on a request moves through these values:</p>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <tbody>
              {LIFECYCLE.map(([s, d]) => (
                <tr key={s}>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line, #eee)', fontFamily: 'monospace', fontWeight: 700, width: 170, verticalAlign: 'top' }}>{s}</td>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line, #eee)' }}>{d}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Webhooks</h2>
          <p>Register a URL and Reffolio will POST a signed JSON payload when events happen. Polling (<code>GET /v1/requests/{'{id}'}</code>) is always available as a fallback.</p>
          {WEBHOOK_ENDPOINTS.map((e) => <EndpointCard key={e.p} e={e} />)}

          <h3 style={{ fontSize: 18, marginTop: 24 }}>Events</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <tbody>
              {EVENTS.map(([s, d]) => (
                <tr key={s}>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line, #eee)', fontFamily: 'monospace', fontWeight: 700, width: 200, verticalAlign: 'top' }}>{s}</td>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line, #eee)' }}>{d}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3 style={{ fontSize: 18, marginTop: 24 }}>Payload &amp; signature</h3>
          <p>Each delivery has this shape, with the event name and data:</p>
          <Code>{`{\n  "event": "reference_received",\n  "data": {\n    "reference_id": "...",\n    "ref_number": "REF-2026-000123"\n  }\n}`}</Code>
          <p>Verify authenticity using the <code>X-Reffolio-Signature</code> header, which is <code>sha256=</code> followed by the HMAC-SHA256 of the raw request body, keyed with your webhook secret:</p>
          <Code>{`import hmac, hashlib\n\ndef verify(secret, raw_body, header):\n    expected = "sha256=" + hmac.new(\n        secret.encode(), raw_body, hashlib.sha256\n    ).hexdigest()\n    return hmac.compare_digest(expected, header)`}</Code>
          <p style={{ fontSize: 13.5, color: 'var(--muted)' }}>Delivery is best-effort: respond with a 2xx status quickly. If your endpoint is unavailable, use polling to reconcile any missed events.</p>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Errors</h2>
          <p>Errors return a JSON body <code>{'{ "detail": "..." }'}</code> with a standard HTTP status:</p>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <tbody>
              {ERRORS.map(([code, desc]) => (
                <tr key={code}>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line, #eee)', fontFamily: 'monospace', fontWeight: 700, width: 70, verticalAlign: 'top' }}>{code}</td>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line, #eee)' }}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Notes</h2>
          <ul style={{ lineHeight: 1.7 }}>
            <li>Keys are scoped to one organisation and only ever access that organisation&rsquo;s own data.</li>
            <li>Requests created via the API send the same emails and follow the same consent flow as the dashboard.</li>
            <li>References are only readable once the candidate has granted consent.</li>
            <li>Keep your keys and webhook secrets safe. If a key is exposed, revoke it in the dashboard and generate a new one.</li>
          </ul>

          <div className="mk-cta" style={{ marginTop: 40 }}>
            <h2>Ready to integrate?</h2>
            <p>Generate your first key in the dashboard, or talk to us about integrations.</p>
            <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Go to dashboard</Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
