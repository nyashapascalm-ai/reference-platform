'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';

export default function ConfirmPage() {
  const { token } = useParams();
  const [info, setInfo] = useState(null);
  const [name, setName] = useState('');
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api(`/confirm/${token}`, { auth: false })
      .then((d) => { setInfo(d); if (d.referee_name) setName(d.referee_name); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  async function confirm() {
    setBusy(true); setError('');
    try { await api(`/confirm/${token}`, { method: 'POST', auth: false, body: { name } }); setDone(true); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  if (loading) return <div className="wrap"><p className="muted">Loading…</p></div>;
  if (error && !info) return (
    <div className="wrap"><h1>Confirmation link invalid</h1><p className="msg err">{error}</p>
      <p className="muted">This link may have already been used or expired.</p></div>
  );

  if (done || info?.already_confirmed) return (
    <div className="wrap">
      <h1>Reference confirmed ✓</h1>
      <p className="muted">Thank you — your confirmation has been recorded.</p>
      <div className="card">
        <div className="kv">Reference for: {info?.worker_name}</div>
        <div className="kv">Issued by: {info?.issuing_org}</div>
      </div>
    </div>
  );

  return (
    <div className="wrap">
      <h1>Confirm a reference</h1>
      <p className="muted">{info?.issuing_org} has named you as the referee for an employment reference.</p>
      <div className="card">
        <div className="kv">Candidate: <b style={{ color: 'var(--text)' }}>{info?.worker_name}</b></div>
        <div className="kv">Issuing organisation: {info?.issuing_org}</div>
        {info?.assignment_context && <div className="kv">Context: {info.assignment_context}</div>}
        <label>Your name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} />
        <p className="muted" style={{ marginTop: 12 }}>By confirming, you attest that you provided this reference for the candidate above.</p>
        <button onClick={confirm} disabled={busy}>Yes, I confirm I provided this reference</button>
        {error && <div className="msg err">{error}</div>}
      </div>
    </div>
  );
}
