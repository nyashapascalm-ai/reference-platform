'use client';
import Link from 'next/link';
import '../marketing.css';
import MarketingNav from '../../components/MarketingNav';
import MarketingFooter from '../../components/MarketingFooter';

const BASE = 'https://reference-platform-production.up.railway.app';

const ENDPOINTS = [
  { m: 'GET', p: '/v1/ping', d: 'Check your key and see which organisation it belongs to.',
    res: '{\n  "ok": true,\n  "org_id": "...",\n  "scope": "org"\n}' },
  { m: 'GET', p: '/v1/templates', d: 'List active reference templates. Optional ?vertical=care|social_work|healthcare|teaching.',
    res: '[\n  { "id": "...", "vertical": "care", "name": "CQC care & support reference", "version": "1" }\n]' },
  { m: 'POST', p: '/v1/workers/verify', d: 'Create/verify a worker record in your organisation.',
    req: '{\n  "full_name": "Sam Jones",\n  "vertical": "care",\n  "registration_body": "none",\n  "dbs_certificate_number": "001234567890"\n}',
    res: '{\n  "worker_id": "...",\n  "registration_status": "not_applicable"\n}' },
  { m: 'POST', p: '/v1/references', d: 'Create a draft reference for a worker.',
    req: '{\n  "worker_id": "...",\n  "template_id": "...",\n  "assignment_context": "Domiciliary care team",\n  "content": { "role": "Care Worker", "conduct": "..." },\n  "referee": { "full_name": "A. Manager", "job_title": "Registered Manager", "work_email": "manager@yourorg.co.uk" }\n}',
    res: '{\n  "reference_id": "...",\n  "status": "draft"\n}' },
  { m: 'POST', p: '/v1/references/{id}/publish', d: 'Publish a draft. Validates required fields, computes the tamper-evident hash, runs the sector AI assessment.',
    res: '{\n  "reference_id": "...",\n  "status": "published",\n  "content_hash": "770c44..."\n}' },
  { m: 'GET', p: '/v1/references/{id}', d: 'Fetch one reference with its status, hash and AI summary.',
    res: '{\n  "id": "...",\n  "status": "published",\n  "content_hash": "...",\n  "risk_score": 28,\n  "ai_summary": "..."\n}' },
  { m: 'GET', p: '/v1/references', d: 'List all references issued by your organisation.',
    res: '[\n  { "id": "...", "status": "published", "worker_name": "Sam Jones", "content_hash": "..." }\n]' },
];

const ERRORS = [
  ['401', 'Missing or invalid API key, or the key was revoked.'],
  ['402', 'Your plan does not include API access. Upgrade to Growth or Business.'],
  ['403', 'The organisation is suspended, or the resource belongs to another organisation.'],
  ['404', 'The reference was not found.'],
  ['409', 'Conflict (e.g. the reference is already published, or a duplicate registration).'],
  ['422', 'Validation error (e.g. required reference fields are missing).'],
];

function Code({ children }) {
  return <pre style={{ background: '#0c1020', color: '#e6e9f5', padding: '14px 16px', borderRadius: 10, overflowX: 'auto', fontSize: 13, lineHeight: 1.5, margin: '8px 0' }}><code>{children}</code></pre>;
}

export default function Developers() {
  return (
    <div className="mk">
      <MarketingNav />
      <section className="mk-pagehero">
        <div className="mk-container">
          <div className="mk-kicker" style={{ color: 'var(--violet)', fontWeight: 700, letterSpacing: '.08em' }}>DEVELOPERS</div>
          <h1 style={{ marginTop: 12 }}>Reffolio API</h1>
          <p>Connect your ATS or HR system to Reffolio: create and verify references, publish them with a tamper-evident hash, and read them back {'\u2014'} all programmatically. Available on the Growth and Business plans.</p>
        </div>
      </section>

      <section className="mk-section" style={{ paddingTop: 16 }}>
        <div className="mk-container" style={{ maxWidth: 860 }}>

          <h2 style={{ fontSize: 24 }}>Getting a key</h2>
          <p>An organisation admin generates keys in the dashboard under <b>API</b>. The full key (<code>rfl_live_{'\u2026'}</code>) is shown once {'\u2014'} store it securely. You can revoke a key at any time.</p>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Authentication</h2>
          <p>Send your key as a bearer token on every request:</p>
          <Code>{`Authorization: Bearer rfl_live_EXAMPLEKEY1234567890`}</Code>
          <p>Base URL:</p>
          <Code>{BASE}</Code>
          <p>A quick check from your terminal:</p>
          <Code>{`curl -H "Authorization: Bearer rfl_live_..." \\\n  ${BASE}/v1/ping`}</Code>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>A typical flow</h2>
          <ol style={{ lineHeight: 1.7 }}>
            <li>List templates {'\u2014'} <code>GET /v1/templates</code> {'\u2014'} pick the right <code>template_id</code> for the sector.</li>
            <li>Verify the worker {'\u2014'} <code>POST /v1/workers/verify</code> {'\u2014'} get a <code>worker_id</code>.</li>
            <li>Create the reference {'\u2014'} <code>POST /v1/references</code> {'\u2014'} get a <code>reference_id</code>.</li>
            <li>Publish it {'\u2014'} <code>POST /v1/references/{'{id}'}/publish</code> {'\u2014'} returns the <code>content_hash</code>.</li>
          </ol>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Endpoints</h2>
          {ENDPOINTS.map((e) => (
            <div key={e.p} style={{ border: '1px solid var(--line, #e7e9f2)', borderRadius: 12, padding: 16, margin: '12px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 12, padding: '2px 8px', borderRadius: 6, background: e.m === 'GET' ? '#e7f5ff' : '#fff4e6', color: e.m === 'GET' ? '#1c7ed6' : '#e8590c' }}>{e.m}</span>
                <code style={{ fontFamily: 'monospace', fontSize: 14 }}>{e.p}</code>
              </div>
              <p style={{ margin: '8px 0' }}>{e.d}</p>
              {e.req && <><div style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 700 }}>Request body</div><Code>{e.req}</Code></>}
              <div style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 700 }}>Response</div><Code>{e.res}</Code>
            </div>
          ))}

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Errors</h2>
          <p>Errors return a JSON body <code>{'{ "detail": "..." }'}</code> with a standard HTTP status:</p>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <tbody>
              {ERRORS.map(([code, desc]) => (
                <tr key={code}>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line, #eee)', fontFamily: 'monospace', fontWeight: 700, width: 70 }}>{code}</td>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line, #eee)' }}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2 style={{ fontSize: 24, marginTop: 32 }}>Notes</h2>
          <ul style={{ lineHeight: 1.7 }}>
            <li>Keys are scoped to one organisation and can only read or write that organisation{'\u2019'}s own data.</li>
            <li>Publishing through the API runs the same validation, AI assessment and hashing as the dashboard.</li>
            <li>Keep your keys secret. If one is exposed, revoke it in the dashboard and generate a new one.</li>
          </ul>

          <div className="mk-cta" style={{ marginTop: 40 }}>
            <h2>Ready to integrate?</h2>
            <p>Generate your first key in the dashboard, or talk to us about Enterprise integrations.</p>
            <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Go to dashboard</Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
