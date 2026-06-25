function ReferencesPanel({ me }) {
  const [tab, setTab] = useState('request');
  return (
    <div className="card">
      <h2>References</h2>
      <p className="muted">Request references about people you{'\u2019'}re hiring, and view references you{'\u2019'}ve received. Received references are your inspection-ready records.</p>
      <div style={{ display: 'flex', gap: 8, margin: '14px 0', flexWrap: 'wrap' }}>
        {[['request', 'Request a reference'], ['sent', 'Requests sent'], ['received', 'Received references']].map(([id, label]) => (
          <button key={id} className={tab === id ? '' : 'ghost'} style={{ marginTop: 0 }} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>
      {tab === 'request' && <RequestForm me={me} onSent={() => setTab('sent')} />}
      {tab === 'sent' && <RequestsList mode="sent" />}
      {tab === 'received' && <RequestsList mode="received" />}
    </div>
  );
}

function RequestForm({ me, onSent }) {
  const [templates, setTemplates] = useState([]);
  const [workerName, setWorkerName] = useState('');
  const [workerEmail, setWorkerEmail] = useState('');
  const [prevEmployer, setPrevEmployer] = useState('');
  const [refereeName, setRefereeName] = useState('');
  const [refereeEmail, setRefereeEmail] = useState('');
  const [templateId, setTemplateId] = useState('');
  const [message, setMessage] = useState('');
  const [drafting, setDrafting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false);

  useEffect(() => {
    api('/org/templates').then((t) => {
      setTemplates(t || []);
      const care = (t || []).find((x) => x.vertical === 'care');
      if (care) setTemplateId(care.id); else if ((t || [])[0]) setTemplateId(t[0].id);
    }).catch(() => {});
  }, []);

  async function draftEmail() {
    if (!workerName.trim()) { setErr(true); setMsg('Enter the candidate name first.'); return; }
    setDrafting(true); setMsg(''); setErr(false);
    try {
      const r = await api('/requests/draft-email', { method: 'POST', body: {
        worker_name: workerName, referee_name: refereeName || null,
        prev_employer_name: prevEmployer || null, template_id: templateId || null,
      } });
      setMessage(r.body || '');
    } catch (e) { setErr(true); setMsg(e.message); } finally { setDrafting(false); }
  }

  async function send() {
    setBusy(true); setMsg(''); setErr(false);
    try {
      const r = await api('/requests', { method: 'POST', body: {
        worker_name: workerName, worker_email: workerEmail, prev_employer_name: prevEmployer || null,
        referee_name: refereeName || null, referee_email: refereeEmail,
        template_id: templateId || null, message: message || null,
      } });
      setErr(false);
      setMsg(r.email_sent ? 'Request sent \u2014 the referee has been emailed a secure link.' : 'Request created, but the email could not be sent. Check the address.');
      setWorkerName(''); setWorkerEmail(''); setPrevEmployer(''); setRefereeName(''); setRefereeEmail(''); setMessage('');
      if (r.email_sent && onSent) setTimeout(onSent, 1200);
    } catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
  }

  const valid = workerName.trim() && workerEmail.includes('@') && refereeEmail.includes('@');
  return (
    <div>
      <label>Candidate name *</label>
      <input value={workerName} onChange={(e) => setWorkerName(e.target.value)} placeholder="The person you’re hiring" />
      <label>Candidate email *</label>
      <input value={workerEmail} onChange={(e) => setWorkerEmail(e.target.value)} placeholder="candidate@email.com" />
      <label>Previous employer</label>
      <input value={prevEmployer} onChange={(e) => setPrevEmployer(e.target.value)} placeholder="e.g. Sunrise Care Ltd" />
      <label>Referee name</label>
      <input value={refereeName} onChange={(e) => setRefereeName(e.target.value)} placeholder="The manager who will complete it" />
      <label>Referee work email *</label>
      <input value={refereeEmail} onChange={(e) => setRefereeEmail(e.target.value)} placeholder="manager@theiremployer.co.uk" />
      <label>Reference form</label>
      <select value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
        {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select>
      <label>Covering email</label>
      <button type="button" className="ghost" style={{ marginTop: 0, marginBottom: 6 }}
        onClick={draftEmail} disabled={drafting}>{drafting ? 'Drafting\u2026' : 'Generate email with AI'}</button>
      <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={8} placeholder="Write a note to the referee, or generate one with AI. The secure link is added automatically." />
      <p className="muted" style={{ marginTop: 8 }}>The referee completes it on a secure link {'\u2014'} no account needed. The candidate is then asked to consent before the reference is released to you. Attachments are coming soon.</p>
      <button onClick={send} disabled={busy || !valid} style={{ marginTop: 10 }}>{busy ? 'Sending\u2026' : 'Send request'}</button>
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
    </div>
  );
}

function RequestsList({ mode }) {
  const [data, setData] = useState(null);
  const [q, setQ] = useState('');
  const [err, setErr] = useState('');
  useEffect(() => {
    api('/me/requests').then(setData).catch((e) => setErr(e.message));
  }, []);
  if (err) return <div className="msg err">{err}</div>;
  if (!data) return <p className="muted">Loading{'\u2026'}</p>;

  const list = mode === 'sent' ? (data.sent || []) : (data.received || []);
  const filtered = list.filter((x) => {
    if (!q.trim()) return true;
    const hay = ((x.worker_name || '') + ' ' + (x.ref_number || '') + ' ' + (x.referee_email || '')).toLowerCase();
    return hay.includes(q.toLowerCase());
  });

  return (
    <div>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or reference number" />
      {filtered.length === 0 && <p className="kv" style={{ marginTop: 12 }}>Nothing here yet.</p>}
      {filtered.map((x) => (
        <div className="item" key={x.id} style={{ marginTop: 10 }}>
          {mode === 'sent' ? (
            <>
              <div><b>{x.worker_name}</b> {x.ref_number ? <span className="kv">{'\u00b7'} {x.ref_number}</span> : null}</div>
              <div className="kv">Referee: {x.referee_name || x.referee_email}</div>
              <div className="kv">Status: <b style={{ color: 'var(--text)' }}>{x.status}</b>
                {x.completed_at ? ' \u00b7 completed ' + new Date(x.completed_at).toLocaleDateString() : ''}</div>
              {x.consent_status ? <div className="kv">Consent: <b style={{ color: x.consent_status === 'granted' ? '#0a7' : x.consent_status === 'declined' ? '#c33' : 'var(--text)' }}>{x.consent_status === 'pending' ? 'awaiting candidate' : x.consent_status}</b></div> : null}
            </>
          ) : (
            <>
              <div><b>{x.worker_name || 'Candidate'}</b> <span className="kv">{'\u00b7'} {x.ref_number}</span></div>
              <div className="kv">Consent: {x.consent_status}</div>
              <div className="kv" style={{ fontFamily: 'monospace', fontSize: 11 }}>Verified {'\u00b7'} hash {(x.content_hash || '').slice(0, 16)}{'\u2026'}</div>
              <div className="kv">Received {new Date(x.created_at).toLocaleDateString()}</div>
            </>
          )}
        </div>
      ))}
    </div>
  );
}

