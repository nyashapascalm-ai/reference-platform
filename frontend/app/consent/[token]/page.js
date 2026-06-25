'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';

export default function ConsentPage() {
  const { token } = useParams();
  const [info, setInfo] = useState(null);
  const [decision, setDecision] = useState(null); // 'granted' | 'declined'
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api(`/consent/${token}`, { auth: false })
      .then((d) => { setInfo(d); if (d.consent_status !== 'pending') setDecision(d.consent_status); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  async function decide(choice) {
    setBusy(true); setError('');
    try {
      const r = await api(`/consent/${token}`, { method: 'POST', auth: false, body: { decision: choice } });
      setDecision(r.consent_status);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  if (loading) return <div className="wrap"><p className="muted">Loading{'\u2026'}</p></div>;
  if (error && !info) return (
    <div className="wrap"><h1>Consent link invalid</h1><p className="msg err">{error}</p>
      <p className="muted">This link may have already been used or is no longer valid.</p></div>
  );

  if (decision === 'granted') return (
    <div className="wrap">
      <h1>Consent given {'\u2713'}</h1>
      <p className="muted">Thank you. The reference has been released to {info?.requester_org}.</p>
      <div className="card"><div className="kv">Reference number: <b style={{ color: 'var(--text)' }}>{info?.ref_number}</b></div></div>
      <p className="muted" style={{ marginTop: 16 }}>Keep your reference number. In future you can ask a previous employer to send this same reference to a new employer using it.</p>
      <a href="/signin" className="btn-link">Create a free account</a>
    </div>
  );
  if (decision === 'declined') return (
    <div className="wrap">
      <h1>Consent declined</h1>
      <p className="muted">You have declined to release this reference. It will not be shared with {info?.requester_org}.</p>
      <div className="card"><div className="kv">Reference number: {info?.ref_number}</div></div>
    </div>
  );

  return (
    <div className="wrap">
      <h1>A reference about you</h1>
      <p className="muted"><b style={{ color: 'var(--text)' }}>{info?.requester_org}</b> has requested an employment reference about you, and a previous employer has completed it.</p>
      <div className="card">
        <div className="kv">Reference number: <b style={{ color: 'var(--text)' }}>{info?.ref_number}</b></div>
        <p className="muted" style={{ marginTop: 12 }}>
          This reference will <b style={{ color: 'var(--text)' }}>not</b> be shared with {info?.requester_org} unless you consent.
          You can release it, or decline.
        </p>
        <div style={{ display: 'flex', gap: 10, marginTop: 14, flexWrap: 'wrap' }}>
          <button onClick={() => decide('grant')} disabled={busy}>Consent and release</button>
          <button className="ghost" onClick={() => decide('decline')} disabled={busy} style={{ marginTop: 0 }}>Decline</button>
        </div>
        {error && <div className="msg err">{error}</div>}
      </div>
      <p className="muted" style={{ marginTop: 14, fontSize: 13 }}>
        Consenting records a timestamped entry in the reference{'\u2019'}s audit trail. You keep your reference number either way.
      </p>
    </div>
  );
}
