'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';

export default function SharePage() {
  const { token } = useParams();
  const [preview, setPreview] = useState(null);
  const [ref, setRef] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // unpinned: simple identify form
  const [form, setForm] = useState({ name: '', email: '', organisation: '' });
  // pinned: one-time code flow
  const [stage, setStage] = useState('email'); // 'email' | 'code'
  const [info, setInfo] = useState('');

  useEffect(() => {
    api(`/share/${token}`, { auth: false })
      .then(setPreview)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  // unpinned reveal
  async function reveal() {
    if (!form.name.trim() || !form.email.trim()) { setError('Please enter your name and work email.'); return; }
    setBusy(true); setError('');
    try { const r = await api(`/share/${token}`, { method: 'POST', auth: false, body: form }); setRef(r); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  // pinned: request a code
  async function requestCode() {
    if (!form.email.trim()) { setError('Enter the email this reference was sent to.'); return; }
    setBusy(true); setError(''); setInfo('');
    try {
      const r = await api(`/share/${token}/request-code`, { method: 'POST', auth: false, body: { email: form.email } });
      if (r.sent) { setStage('code'); setInfo('We’ve emailed you a 6-digit code. Enter it below (check spam too).'); }
      else { setError('Email isn’t configured for this link yet — please ask the sender to share another way.'); }
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  // pinned: verify the code
  async function verifyCode() {
    if (!form.code || !form.code.trim()) { setError('Enter the code from your email.'); return; }
    setBusy(true); setError('');
    try {
      const r = await api(`/share/${token}/verify`, { method: 'POST', auth: false, body: { email: form.email, code: form.code, name: form.name, organisation: form.organisation } });
      setRef(r);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  if (loading) return <div className="wrap"><p className="muted">Verifying link…</p></div>;
  if (error && !ref && !preview) return (
    <div className="wrap"><h1>Reference unavailable</h1><p className="msg err">{error}</p>
      <p className="muted">This link may have expired or been revoked by the worker.</p></div>
  );

  if (!ref) {
    const heading = (
      <>
        <h1>Verified reference</h1>
        <p className="muted">
          {preview?.worker_name ? `Reference for ${preview.worker_name}` : 'Verified reference'}
          {preview?.issuing_org ? ` · issued by ${preview.issuing_org}` : ''}
        </p>
      </>
    );

    // PINNED: verified-recipient code flow
    if (preview?.pinned) return (
      <div className="wrap">
        {heading}
        <div className="card">
          <h2>Verify it’s you</h2>
          <p className="muted">This reference was sent to {preview.recipient_hint}. Enter that email to receive a one-time code.</p>
          <label>Email it was sent to</label>
          <input value={form.email} onChange={set('email')} placeholder={preview.recipient_hint || 'you@employer.com'} disabled={stage === 'code'} />
          {stage === 'email' && <button onClick={requestCode} disabled={busy}>Email me a code</button>}
          {stage === 'code' && (
            <>
              <label>6-digit code</label>
              <input value={form.code || ''} onChange={set('code')} placeholder="123456" />
              <label>Your name</label>
              <input value={form.name} onChange={set('name')} />
              <label>Organisation</label>
              <input value={form.organisation} onChange={set('organisation')} />
              <div className="row">
                <button onClick={verifyCode} disabled={busy}>Verify &amp; view</button>
                <button className="ghost" onClick={requestCode} disabled={busy}>Resend code</button>
              </div>
            </>
          )}
          {info && <div className="msg">{info}</div>}
          {error && <div className="msg err">{error}</div>}
        </div>
      </div>
    );

    // UNPINNED: self-declared identify form
    return (
      <div className="wrap">
        {heading}
        <div className="card">
          <h2>Confirm who’s viewing</h2>
          <p className="muted">The worker will be able to see that you viewed this reference. Please identify yourself to continue.</p>
          <label>Your name</label><input value={form.name} onChange={set('name')} />
          <label>Work email</label><input value={form.email} onChange={set('email')} placeholder="you@employer.com" />
          <label>Organisation</label><input value={form.organisation} onChange={set('organisation')} />
          <button onClick={reveal} disabled={busy}>View reference</button>
          {error && <div className="msg err">{error}</div>}
        </div>
      </div>
    );
  }

  // Revealed reference
  return (
    <div className="wrap">
      <div className="topbar">
        <div>
          <h1>Verified reference</h1>
          <p className="muted">Shared with consent · pulled directly from source</p>
        </div>
        <button className="noprint ghost" onClick={() => window.print()}>Download PDF</button>
      </div>
      <div className="card">
        <h2>{ref.worker.name}</h2>
        <div className="kv">Registration: {ref.worker.registration}</div>
        <div className="kv">Register check: {
          ref.worker.registration_status === 'verified' ? <span style={{ color: 'var(--accent)' }}>Verified on the SWE register ✓</span>
          : ref.worker.registration_status === 'failed' ? 'Not found / unverified'
          : ref.worker.registration_status === 'expired' ? 'Registration expired'
          : 'Verification pending (manual)'
        }</div>
        <div className="kv">Issued by: {ref.issuing_org}</div>
        <div className="kv">Context: {ref.assignment_context || '—'}</div>
        {ref.published_at && <div className="kv">Published: {new Date(ref.published_at).toLocaleString()}</div>}
      </div>
      <div className="card">
        <h2>Reference content</h2>
        {Object.entries(ref.content || {}).map(([k, v]) => (
          <div className="item" key={k}><div className="kv" style={{ textTransform: 'uppercase', fontSize: 11 }}>{k}</div><div>{String(v)}</div></div>
        ))}
      </div>
      <div className="card">
        <h2>Provenance</h2>
        {ref.referee && (
          <div className="item">
            <div>Referee: {ref.referee.full_name} · {ref.referee.job_title}</div>
            <div className="kv">Domain {ref.referee.domain_verified ? 'verified ✓' : 'unverified'} ({ref.referee.email_domain})</div>
            {ref.referee.confirmed_at
              ? <div className="kv" style={{ color: 'var(--accent)' }}>Referee confirmed ✓ {ref.referee.confirmed_name ? `by ${ref.referee.confirmed_name} ` : ''}on {new Date(ref.referee.confirmed_at).toLocaleString()}</div>
              : <div className="kv">Awaiting referee confirmation</div>}
          </div>
        )}
        <div className="item">
          <div className="kv" style={{ textTransform: 'uppercase', fontSize: 11 }}>Tamper-evident hash</div>
          <div className="hash">{ref.content_hash}</div>
        </div>
      </div>
      {ref.ai && (ref.ai.summary || ref.ai.risk_score !== null) && (
        <div className="card">
          <h2>AI assessment</h2>
          {ref.ai.risk_score !== null && <div className="kv">Risk score: <b style={{ color: 'var(--text)' }}>{ref.ai.risk_score}</b> / 100</div>}
          {ref.ai.summary && <div className="item">{ref.ai.summary}</div>}
          {ref.ai.competency_map && ref.ai.competency_map.PCF && <div className="kv">PCF: {(ref.ai.competency_map.PCF || []).join(', ')}</div>}
          {ref.ai.competency_map && ref.ai.competency_map.KSS && <div className="kv">KSS: {(ref.ai.competency_map.KSS || []).join(', ')}</div>}
        </div>
      )}
    </div>
  );
}
