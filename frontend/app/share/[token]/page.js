'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';

export default function SharePage() {
  const { token } = useParams();
  const [ref, setRef] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api(`/share/${token}`, { auth: false })
      .then(setRef)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="wrap"><p className="muted">Verifying link…</p></div>;
  if (error) return (
    <div className="wrap">
      <h1>Reference unavailable</h1>
      <p className="msg err">{error}</p>
      <p className="muted">This link may have expired or been revoked by the worker.</p>
    </div>
  );

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
          {ref.ai.competency_map && ref.ai.competency_map.PCF && (
            <div className="kv">PCF: {(ref.ai.competency_map.PCF || []).join(', ')}</div>
          )}
          {ref.ai.competency_map && ref.ai.competency_map.KSS && (
            <div className="kv">KSS: {(ref.ai.competency_map.KSS || []).join(', ')}</div>
          )}
        </div>
      )}
    </div>
  );
}
