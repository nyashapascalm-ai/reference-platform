'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';

export default function CompleteReferencePage() {
  const { token } = useParams();
  const [info, setInfo] = useState(null);
  const [content, setContent] = useState({});
  const [refereeName, setRefereeName] = useState('');
  const [refereeTitle, setRefereeTitle] = useState('');
  const [result, setResult] = useState(null); // { ref_number }
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api(`/requests/${token}`, { auth: false })
      .then((d) => { setInfo(d); if (d.referee_name) setRefereeName(d.referee_name); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  const brandColor = info?.brand_color || 'var(--violet, #6C5CE7)';
  const logoUrl = info?.logo_url || null;

  const fields = (info?.template?.field_schema?.fields && info.template.field_schema.fields.length)
    ? info.template.field_schema.fields
    : ((info?.template?.field_schema?.required) || []).map((k) => ({ key: k, label: k, type: 'text' }));
  const required = (info?.template?.field_schema?.required) || [];

  function setField(key, val) { setContent((c) => ({ ...c, [key]: val })); }

  async function submit() {
    setBusy(true); setError('');
    const missing = required.filter((k) => !String(content[k] || '').trim());
    if (missing.length) { setError('Please complete: ' + missing.join(', ')); setBusy(false); return; }
    try {
      const r = await api(`/requests/${token}/complete`, {
        method: 'POST', auth: false,
        body: { content, referee_name: refereeName, referee_job_title: refereeTitle },
      });
      setResult(r);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  if (loading) return <div className="wrap"><p className="muted">Loading{'\u2026'}</p></div>;

  if (error && !info) return (
    <div className="wrap">
      <h1>Reference link invalid</h1>
      <p className="msg err">{error}</p>
      <p className="muted">This link may have already been used or is no longer valid.</p>
    </div>
  );

  if (result) return (
    <div className="wrap">
      <h1>Reference submitted {'\u2713'}</h1>
      <p className="muted">Thank you {'\u2014'} your reference has been recorded and sent securely to the requesting organisation.</p>
      <div className="card">
        <div className="kv">Reference for: <b style={{ color: 'var(--text)' }}>{info?.worker_name}</b></div>
        <div className="kv">Reference number: <b style={{ color: 'var(--text)' }}>{result.ref_number}</b></div>
      </div>
      <p className="muted" style={{ marginTop: 16 }}>
        You can create a free Reffolio account to keep track of references you provide {'\u2014'} or simply close this page.
      </p>
      <a href="/signin" className="btn-link">Create an account</a>
    </div>
  );

  return (
    <div className="wrap">
      {logoUrl ? <img src={logoUrl} alt="" style={{ maxHeight: 52, maxWidth: 180, marginBottom: 10 }} /> : null}
      <div style={{ height: 4, background: brandColor, borderRadius: 2, marginBottom: 14 }} />
      <h1>Complete a reference</h1>
      <p className="muted">
        <b style={{ color: 'var(--text)' }}>{info?.requester_org}</b> has requested an employment reference
        for <b style={{ color: 'var(--text)' }}>{info?.worker_name}</b>
        {info?.prev_employer_name ? <> (previously at {info.prev_employer_name})</> : null}.
      </p>
      {info?.message && <div className="card" style={{ background: 'rgba(108,92,231,.05)' }}><div className="kv">{info.message}</div></div>}

      <div className="card">
        <label>Your name</label>
        <input value={refereeName} onChange={(e) => setRefereeName(e.target.value)} placeholder="e.g. Jane Smith" />
        <label>Your job title</label>
        <input value={refereeTitle} onChange={(e) => setRefereeTitle(e.target.value)} placeholder="e.g. Registered Manager" />

        <div style={{ height: 1, background: 'var(--line, #e7e9f2)', margin: '18px 0' }} />

        {fields.map((f) => {
          const isReq = required.includes(f.key);
          const lbl = <label>{f.label || f.key}{isReq ? ' *' : ''}</label>;
          const val = content[f.key] || '';
          if (f.type === 'boolean' || f.type === 'yesno') {
            return (
              <div key={f.key}>
                {lbl}
                <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                  {['Yes', 'No'].map((opt) => (
                    <button key={opt} type="button"
                      className={val === opt ? '' : 'ghost'}
                      style={{ marginTop: 0, flex: '0 0 auto' }}
                      onClick={() => setField(f.key, opt)}>{opt}</button>
                  ))}
                </div>
              </div>
            );
          }
          if (f.type === 'select' && Array.isArray(f.options)) {
            return (
              <div key={f.key}>
                {lbl}
                <select value={val} onChange={(e) => setField(f.key, e.target.value)}>
                  <option value="">Select{'\u2026'}</option>
                  {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            );
          }
          if (f.type === 'textarea' || f.type === 'long') {
            return (
              <div key={f.key}>
                {lbl}
                <textarea value={val} onChange={(e) => setField(f.key, e.target.value)} rows={4} />
              </div>
            );
          }
          return (
            <div key={f.key}>
              {lbl}
              <input value={val} onChange={(e) => setField(f.key, e.target.value)} />
            </div>
          );
        })}

        <p className="muted" style={{ marginTop: 14 }}>
          By submitting, you confirm this reference is true and accurate to the best of your knowledge.
          It will be recorded with a tamper-evident timestamp and an audit trail.
        </p>
        <button onClick={submit} disabled={busy} style={{ background: brandColor }}>{busy ? 'Submitting\u2026' : 'Submit reference'}</button>
        {error && <div className="msg err">{error}</div>}
      </div>
    </div>
  );
}
