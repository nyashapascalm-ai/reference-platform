function OrgPanel({ me }) {
  const [templates, setTemplates] = useState([]);
  const [refs, setRefs] = useState([]);
  const [tpl, setTpl] = useState(null);
  const [content, setContent] = useState({});
  const [meta, setMeta] = useState({ worker_id: '', assignment_context: '', ref_name: '', ref_title: '', ref_email: '' });
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false); const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState(''); const [aiMsg, setAiMsg] = useState(''); const [flags, setFlags] = useState(null); const [analysis, setAnalysis] = useState({}); const [draftScore, setDraftScore] = useState(null);
  const [step, setStep] = useState('compose'); // 'compose' | 'review'

  async function aiDraft() {
    setAiMsg('Drafting\u2026'); setErr(false);
    try { const r = await api('/ai/draft', { method: 'POST', body: { notes, template_id: tpl.id } }); setContent(r.content); setAiMsg('AI draft inserted \u2014 edit anything, then continue to review.'); }
    catch (e) { setErr(true); setAiMsg(e.message); }
  }
  async function aiCheck() {
    setErr(false); setFlags(null);
    try { const r = await api('/ai/check', { method: 'POST', body: { content } }); setFlags(r); return r; }
    catch (e) { setErr(true); setAiMsg(e.message); return null; }
  }
  function applyRewrite() { if (flags?.rewritten) { setContent({ ...content, ...flags.rewritten }); setFlags(null); setAiMsg('Rewrite applied \u2014 re-run review to re-check.'); } }
  async function analyseDraft() {
    setErr(false); setDraftScore(null);
    try { const r = await api('/ai/analyse', { method: 'POST', body: { content, assignment_context: meta.assignment_context, vertical: tpl?.vertical } }); setDraftScore(r); return r; }
    catch (e) { setErr(true); setAiMsg(e.message); return null; }
  }
  async function analyse(id) {
    setAiMsg('Analysing\u2026'); setErr(false);
    try { const r = await api(`/references/${id}/analyse`, { method: 'POST' }); setAnalysis({ ...analysis, [id]: r }); setAiMsg(''); }
    catch (e) { setErr(true); setAiMsg(e.message); }
  }

  const load = useCallback(async () => {
    try {
      const t = await api('/templates', { auth: false });
      setTemplates(t); if (t[0]) setTpl(t[0]);
      const r = await api('/me/references'); setRefs(r.as_org || []);
    } catch (e) { setErr(true); setMsg(e.message); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const required = (tpl?.field_schema?.required) || [];
  const fields = (tpl?.field_schema?.fields && tpl.field_schema.fields.length)
    ? tpl.field_schema.fields
    : required.map((k) => ({ key: k, label: k, type: 'text' }));
  const up = (k) => (e) => setMeta({ ...meta, [k]: e.target.value });
  const upc = (k) => (e) => setContent({ ...content, [k]: e.target.value });

  const validId = /^[0-9a-fA-F-]{36}$/.test((meta.worker_id || '').trim());
  const missingRequired = required.filter((k) => !(content[k] || '').toString().trim());
  const canReview = !!tpl && validId && missingRequired.length === 0;

  // Step 1 -> 2: run both AI passes together, then show the review panel.
  async function goReview() {
    setMsg(''); setErr(false); setAiMsg('Reviewing \u2014 checking fairness and analysing\u2026');
    setStep('review');
    await aiCheck();
    await analyseDraft();
    setAiMsg('');
  }

  // Step 3: create the draft and publish it in one confirmed action.
  async function confirmAndPublish() {
    setMsg(''); setErr(false);
    if (!canReview) { setErr(true); setMsg('Please complete the required fields first.'); return; }
    setBusy(true);
    try {
      const body = {
        worker_id: meta.worker_id, template_id: tpl.id,
        assignment_context: meta.assignment_context, content,
        referee: meta.ref_email ? { full_name: meta.ref_name, job_title: meta.ref_title, work_email: meta.ref_email } : null,
      };
      const created = await api('/references', { method: 'POST', body });
      const pub = await api(`/references/${created.reference_id}/publish`, { method: 'POST' });
      setContent({}); setNotes(''); setDraftScore(null); setFlags(null); setStep('compose');
      setMeta({ worker_id: '', assignment_context: '', ref_name: '', ref_title: '', ref_email: '' });
      setMsg('Published \u00b7 tamper-evident hash ' + (pub.content_hash || '').slice(0, 16) + '\u2026 \u2014 the worker can now share it.');
      load();
    } catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
  }

  // Save as a draft without publishing (goes to the board for later).
  async function saveDraftOnly() {
    setMsg(''); setErr(false);
    if (!canReview) { setErr(true); setMsg('Please complete the required fields first.'); return; }
    setBusy(true);
    try {
      const body = {
        worker_id: meta.worker_id, template_id: tpl.id,
        assignment_context: meta.assignment_context, content,
        referee: meta.ref_email ? { full_name: meta.ref_name, job_title: meta.ref_title, work_email: meta.ref_email } : null,
      };
      await api('/references', { method: 'POST', body });
      setContent({}); setNotes(''); setDraftScore(null); setFlags(null); setStep('compose');
      setMeta({ worker_id: '', assignment_context: '', ref_name: '', ref_title: '', ref_email: '' });
      setMsg('Saved as a draft \u2014 it\u2019s in the Draft column. Drag it to Published when ready.');
      load();
    } catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
  }
  async function publish(id) {
    setMsg(''); setErr(false);
    try { const r = await api(`/references/${id}/publish`, { method: 'POST' }); setMsg('Published \u00b7 hash ' + r.content_hash); load(); }
    catch (e) { setErr(true); setMsg(e.message); }
  }

  const stepBadge = (n, labelTxt, active, done) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, opacity: active || done ? 1 : 0.5 }}>
      <span style={{ width: 22, height: 22, borderRadius: '50%', background: active ? 'var(--grad, #6C5CE7)' : (done ? 'var(--accent, #00B8A6)' : 'var(--line)'), color: '#fff', fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{done ? '\u2713' : n}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: active ? 'var(--text)' : 'var(--muted)' }}>{labelTxt}</span>
    </div>
  );

  return (
    <div className="card">
      <h2>Issue a reference</h2>
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', margin: '6px 0 18px' }}>
        {stepBadge(1, 'Compose', step === 'compose', step === 'review')}
        {stepBadge(2, 'Review', step === 'review', false)}
        {stepBadge(3, 'Publish', false, false)}
      </div>

      {step === 'compose' && (
        <>
          <p className="muted">Fill in the reference (or let AI draft it from your notes). You{'\u2019'}ll review it before anything is published.</p>
          <label>Template <Help text="The reference format. Templates follow the statutory/regulatory standard for the sector and set which fields are required." /></label>
          <select value={tpl?.id || ''} onChange={(e) => setTpl(templates.find((t) => t.id === e.target.value))}>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.version})</option>)}
          </select>
          <label>Worker ID (from the worker{'\u2019'}s portal) <Help text="Every worker has a unique Reffolio Worker ID shown in their portal. Paste it here so the reference is bound to the right person." /></label>
          <input value={meta.worker_id} onChange={up('worker_id')} placeholder="paste worker_id" />
          {meta.worker_id && !validId && <div className="kv" style={{ color: 'var(--danger, #c0392b)' }}>That doesn{'\u2019'}t look like a valid Worker ID.</div>}

          <label>Draft with AI (paste rough notes) <Help text="Paste rough notes about the worker. AI turns them into a fair, evidence-based draft you can edit." /></label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
            style={{ width: '100%', background: 'var(--ink)', border: '1px solid var(--line)', color: 'var(--text)', borderRadius: 9, padding: '10px 12px', fontFamily: 'inherit', fontSize: 14 }}
            placeholder="e.g. Sam worked here 2022-24 as senior practitioner, strong on assessments, no conduct issues" />
          <button className="ghost" onClick={aiDraft} disabled={!tpl || !notes}>Draft with AI</button>

          <label>Assignment context <Help text="The role or setting this reference relates to (e.g. the team or service the worker was in)." /></label>
          <input value={meta.assignment_context} onChange={up('assignment_context')} placeholder="e.g. Domiciliary care team" />

          {fields.map((fld) => (
            <div key={fld.key}>
              <label>{fld.label}{required.includes(fld.key) ? ' *' : ''}</label>
              {fld.type === 'textarea'
                ? <textarea rows={3} value={content[fld.key] || ''} onChange={upc(fld.key)} />
                : <input value={content[fld.key] || ''} onChange={upc(fld.key)} />}
            </div>
          ))}

          <label>Referee name</label><input value={meta.ref_name} onChange={up('ref_name')} />
          <label>Referee job title</label><input value={meta.ref_title} onChange={up('ref_title')} />
          <label>Referee work email (should match your domain) <Help text="The named referee's work email. A matching domain is marked 'domain verified', and the referee is emailed a link to confirm authorship." /></label>
          <input value={meta.ref_email} onChange={up('ref_email')} placeholder="manager@yourorg.gov.uk" />

          <button onClick={goReview} disabled={!canReview} style={{ marginTop: 14 }}>Review before publishing &rarr;</button>
          {!canReview && (tpl ? (missingRequired.length > 0
            ? <div className="kv">Complete the required fields ({missingRequired.length} left) and a valid Worker ID to continue.</div>
            : <div className="kv">Paste a valid Worker ID to continue.</div>) : null)}
        </>
      )}

      {step === 'review' && (
        <>
          <p className="muted">Review the AI{'\u2019'}s checks below. If you{'\u2019'}re happy, publish, or go back to edit.</p>

          {aiMsg && <div className={'msg' + (err ? ' err' : '')}>{aiMsg}</div>}

          <div style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 16, margin: '8px 0' }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Fairness &amp; defamation check</div>
            {flags == null ? <div className="kv">Running...</div>
              : flags.ok ? <div className="kv" style={{ color: 'var(--accent)' }}>{'\u2713'} No fairness or defamation issues found.</div>
              : <>
                  {(flags.flags || []).map((fl, i) => (
                    <div className="kv" key={i}>{'\u26a0'} {fl.field}: {fl.issue} <span className="badge">{fl.severity}</span></div>
                  ))}
                  {Object.keys(flags.rewritten || {}).length > 0 &&
                    <button className="ghost" onClick={applyRewrite} style={{ marginTop: 8 }}>Apply AI rewrite</button>}
                </>}
          </div>

          <div style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 16, margin: '8px 0' }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Sector assessment {tpl ? <span className="badge">{tpl.name}</span> : null}</div>
            {draftScore == null ? <div className="kv">Running...</div>
              : <>
                  <div className="kv">Risk score: <b style={{ color: 'var(--text)' }}>{draftScore.risk_score}</b> / 100</div>
                  <div className="kv">{draftScore.summary}</div>
                </>}
          </div>

          <div className="row" style={{ marginTop: 14, gap: 8, flexWrap: 'wrap' }}>
            <button className="ghost" onClick={() => { setStep('compose'); setAiMsg(''); }}>&larr; Back to edit</button>
            <button className="ghost" onClick={goReview}>Re-run review</button>
            <button className="ghost" onClick={saveDraftOnly} disabled={busy}>Save as draft</button>
            <button onClick={confirmAndPublish} disabled={busy}>I{'\u2019'}m happy {'\u2014'} publish now</button>
          </div>
          <p className="muted" style={{ marginTop: 8, fontSize: 12.5 }}>Publishing computes the tamper-evident hash and lets the worker share it. The named referee is emailed to confirm authorship.</p>
        </>
      )}

      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}

      <h2 style={{ marginTop: 24 }}>Issued references <Help text="Your references as a board. Draft: created but not live. Published: finalised with a tamper-evident hash. Viewed: opened by a recipient. Drag a draft into Published to publish it." /></h2>
      <p className="muted">Drag a draft into <b>Published</b> to publish it (the tamper-evident hash is generated on drop).</p>
      <ReferenceBoard refs={refs} onPublish={publish} />
    </div>
  );
}

