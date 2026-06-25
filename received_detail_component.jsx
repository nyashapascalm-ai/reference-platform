function ReceivedDetail({ referenceId, onBack }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState('');
  const [dlBusy, setDlBusy] = useState('');

  useEffect(() => {
    api(`/received/${referenceId}`).then(setD).catch((e) => setErr(e.message));
  }, [referenceId]);

  async function downloadAttachment(id) {
    setDlBusy(id);
    try {
      const r = await api(`/attachments/${id}/download`);
      if (r.url) window.open(r.url, '_blank', 'noopener');
    } catch (e) { setErr(e.message); } finally { setDlBusy(''); }
  }

  function savePdf() { window.print(); }

  if (err) return <div><button className="ghost" onClick={onBack} style={{ marginTop: 0 }}>{'\u2190'} Back</button><div className="msg err" style={{ marginTop: 10 }}>{err}</div></div>;
  if (!d) return <p className="muted">Loading{'\u2026'}</p>;

  const fields = (d.template?.field_schema?.fields) || [];
  const labelFor = (k) => { const f = fields.find((x) => x.key === k); return f ? f.label : k; };
  const ordered = fields.length ? fields.map((f) => f.key) : Object.keys(d.content || {});

  return (
    <div className="received-detail">
      <div className="no-print" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, gap: 8, flexWrap: 'wrap' }}>
        <button className="ghost" onClick={onBack} style={{ marginTop: 0 }}>{'\u2190'} Back to received</button>
        <button onClick={savePdf} style={{ marginTop: 0 }}>Save as PDF</button>
      </div>

      <div style={{ border: '1px solid var(--line, #e7e9f2)', borderRadius: 12, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>Employment reference</h2>
        <div className="kv">Reference number: <b style={{ color: 'var(--text)' }}>{d.ref_number}</b></div>
        <div className="kv">Candidate: <b style={{ color: 'var(--text)' }}>{d.worker_name}</b></div>
        {d.template && <div className="kv">Form: {d.template.name}</div>}
        <div className="kv">Received: {d.received_at ? new Date(d.received_at).toLocaleString() : '\u2014'}</div>

        {d.referee && (
          <div style={{ marginTop: 12 }}>
            <div className="kv">Referee: <b style={{ color: 'var(--text)' }}>{d.referee.full_name}</b>{d.referee.job_title ? ', ' + d.referee.job_title : ''}</div>
            <div className="kv">Referee email: {d.referee.work_email} {d.referee.domain_verified ? '\u00b7 domain verified' : '\u00b7 domain unverified'}</div>
          </div>
        )}

        <div style={{ height: 1, background: 'var(--line, #e7e9f2)', margin: '16px 0' }} />
        <h3 style={{ fontSize: 16 }}>Reference details</h3>
        {ordered.map((k) => {
          const v = (d.content || {})[k];
          if (v === undefined || v === null || v === '') return null;
          return (
            <div key={k} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 13, color: 'var(--muted, #667)', fontWeight: 600 }}>{labelFor(k)}</div>
              <div style={{ color: 'var(--text)' }}>{String(v)}</div>
            </div>
          );
        })}

        {d.attachments && d.attachments.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <h3 style={{ fontSize: 16 }}>Attachments</h3>
            {d.attachments.map((a) => (
              <div key={a.id} className="kv">
                {a.direction === 'returned' ? 'From referee: ' : 'Sent with request: '}
                <button className="ghost no-print" style={{ marginTop: 0, padding: '2px 10px' }}
                  onClick={() => downloadAttachment(a.id)} disabled={dlBusy === a.id}>
                  {dlBusy === a.id ? 'Opening\u2026' : a.filename}
                </button>
                <span className="print-only" style={{ display: 'none' }}>{a.filename}</span>
              </div>
            ))}
          </div>
        )}

        <div style={{ height: 1, background: 'var(--line, #e7e9f2)', margin: '16px 0' }} />
        <h3 style={{ fontSize: 16 }}>Verification & audit trail</h3>
        <div className="kv" style={{ fontFamily: 'monospace', fontSize: 11, wordBreak: 'break-all' }}>Tamper-evident hash: {d.content_hash}</div>
        <div className="kv">Consent: {d.consent_status}</div>
        {(d.events || []).map((e, i) => (
          <div key={i} className="kv">{e.event_type}{e.actor_name ? ' \u2014 ' + e.actor_name : ''} {e.created_at ? '\u00b7 ' + new Date(e.created_at).toLocaleString() : ''}</div>
        ))}
        <p className="muted" style={{ marginTop: 14, fontSize: 12 }}>
          This reference is verified and tamper-evident, with a full audit trail. Reffolio reference {d.ref_number}.
        </p>
      </div>
    </div>
  );
}
