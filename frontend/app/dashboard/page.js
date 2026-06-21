'use client';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../../lib/supabaseClient';
import { api } from '../../lib/api';

function Help({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="help">
      <button type="button" className="help-btn" onClick={() => setOpen((o) => !o)} aria-label="Help">?</button>
      {open && (<>
        <div className="help-backdrop" onClick={() => setOpen(false)} />
        <div className="help-pop">
          <button type="button" className="help-close" onClick={() => setOpen(false)} aria-label="Close">×</button>
          <span className="help-text" dangerouslySetInnerHTML={{ __html: text }} />
        </div>
      </>)}
    </span>
  );
}

export default function Dashboard() {
  const router = useRouter();
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [setupRole, setSetupRole] = useState(null);

  useEffect(() => {
    try { const p = new URLSearchParams(window.location.search).get('setup'); if (p) setSetupRole(p); } catch {}
  }, []);

  const loadMe = useCallback(async () => {
    try { setMe(await api('/me')); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) { router.push('/'); return; }
      loadMe();
    });
  }, [router, loadMe]);

  async function signOut() { await supabase.auth.signOut(); router.push('/'); }

  if (loading) return <div className="wrap"><p className="muted">Loading…</p></div>;

  return (
    <div className="wrap">
      <div className="topbar">
        <div>
          <h1>{me?.role === 'org_admin' ? 'Management console' : 'Dashboard'}</h1>
          <p className="muted">{me?.email}{me?.role ? ` · ${me.role === 'org_admin' ? 'admin' : (me.role || '').replace('_', ' ')}` : ''}</p>
        </div>
        <button className="ghost" onClick={signOut}>Sign out</button>
      </div>
      {error && <div className="msg err">{error}</div>}

      {me?.is_super_admin && (
        <div className="card" style={{ borderLeft: '3px solid var(--violet, #6C5CE7)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div><b style={{ color: 'var(--text)' }}>You{'\u2019'}re signed in as Reffolio staff</b></div>
              <div className="kv">Manage organisations, billing, analytics and reports in the operator console.</div>
            </div>
            <button style={{ marginTop: 0 }} onClick={() => router.push('/admin')}>Open admin console</button>
          </div>
        </div>
      )}

      {!me?.org_id && !me?.worker_id && !me?.is_super_admin && <Onboarding onDone={loadMe} role={setupRole} setRole={setSetupRole} />}
      {!me?.org_id && !me?.worker_id && me?.is_super_admin && (
        <div className="card">
          <h2>Staff account</h2>
          <p className="kv">This account isn{'\u2019'}t set up as an organisation or worker — that{'\u2019'}s expected for a staff login. Use the admin console above.</p>
        </div>
      )}

      {me?.org_id && me.role === 'org_admin' ? (
        <>
          <AdminOversightPanel me={me} />
          <TeamPanel me={me} />
          <BillingPanel me={me} />
          <div className="kv" style={{ textTransform: 'uppercase', fontSize: 11, letterSpacing: '0.04em', margin: '28px 0 12px' }}>
            You can also issue a reference
          </div>
          <OrgPanel me={me} />
        </>
      ) : me?.org_id ? (
        <>
          <OrgPanel me={me} />
          <TeamPanel me={me} />
          <BillingPanel me={me} />
        </>
      ) : null}

      {me?.worker_id && <WorkerPanel me={me} />}
    </div>
  );
}

function Onboarding({ onDone, role, setRole }) {
  const back = (
    <button className="ghost" style={{ marginTop: 0 }} onClick={() => setRole(null)}>← Choose a different role</button>
  );
  if (role === 'org') return (<><div className="row" style={{ marginBottom: 8 }}>{back}</div><CreateOrg onDone={onDone} /></>);
  if (role === 'worker') return (<><div className="row" style={{ marginBottom: 8 }}>{back}</div><RegisterWorker onDone={onDone} /></>);
  return (
    <div className="card">
      <h2>What brings you here?</h2>
      <p className="muted">Choose how you’ll use Reffolio. You can change this by signing out.</p>
      <div className="row">
        <button onClick={() => setRole('org')}>I issue references (organisation)</button>
        <button className="ghost" onClick={() => setRole('worker')}>I collect my references (worker)</button>
      </div>
    </div>
  );
}

function CreateOrg({ onDone }) {
  const [f, setF] = useState({ name: '', org_type: 'local_authority', vertical: 'social_work', email_domain: '', full_name: '' });
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false); const [busy, setBusy] = useState(false);
  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit() {
    setBusy(true); setMsg(''); setErr(false);
    try { await api('/onboarding/org', { method: 'POST', body: f }); onDone(); }
    catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
  }
  return (
    <div className="card">
      <h2>Set up an organisation</h2>
      <label>Organisation name</label><input value={f.name} onChange={up('name')} />
      <label>Your name</label><input value={f.full_name} onChange={up('full_name')} />
      <label>Type</label>
      <select value={f.org_type} onChange={up('org_type')}>
        <option value="local_authority">Local authority</option>
        <option value="agency">Agency</option>
        <option value="nhs_trust">NHS trust</option>
        <option value="care_provider">Care provider</option>
        <option value="school">School</option>
        <option value="mat">MAT</option>
      </select>
      <label>Verified email domain</label><input value={f.email_domain} onChange={up('email_domain')} placeholder="barchester.gov.uk" />
      <button onClick={submit} disabled={busy}>Create organisation</button>
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
    </div>
  );
}

function RegisterWorker({ onDone }) {
  const [f, setF] = useState({ full_name: '', vertical: 'social_work', registration_body: 'swe', registration_number: '', dbs_certificate_number: '' });
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false); const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit() {
    setBusy(true); setMsg(''); setErr(false);
    try { const r = await api('/workers/verify', { method: 'POST', body: f }); setResult(r); }
    catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
  }
  if (result) {
    const st = result.registration_status; const reg = result.register || {};
    return (
      <div className="card">
        <h2>Registration check</h2>
        <div className="kv">Status: {st === 'verified' ? <span style={{ color: 'var(--accent)' }}>Verified on the SWE register ✓</span> : st === 'failed' ? 'Not found on the SWE register' : 'Pending — manual verification'}</div>
        {reg.registered_name && <div className="kv">Register name: {reg.registered_name}</div>}
        {reg.registered_until && <div className="kv">Registered until: {reg.registered_until}</div>}
        {reg.detail && <div className="kv">{reg.detail}</div>}
        <button onClick={onDone}>Continue to your portal</button>
      </div>
    );
  }
  return (
    <div className="card">
      <h2>Register as a worker</h2>
      <label>Full name</label><input value={f.full_name} onChange={up('full_name')} />
      <label>Registration body</label>
      <select value={f.registration_body} onChange={up('registration_body')}>
        <option value="swe">Social Work England (SWE)</option>
        <option value="nmc">NMC</option><option value="gmc">GMC</option>
        <option value="hcpc">HCPC</option><option value="trn">TRN</option>
      </select>
      <label>Registration number</label><input value={f.registration_number} onChange={up('registration_number')} placeholder="SW123456" />
      <label>DBS certificate number (optional)</label><input value={f.dbs_certificate_number} onChange={up('dbs_certificate_number')} />
      <button onClick={submit} disabled={busy}>Verify & register</button>
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
    </div>
  );
}

function OrgPanel({ me }) {
  const [templates, setTemplates] = useState([]);
  const [refs, setRefs] = useState([]);
  const [tpl, setTpl] = useState(null);
  const [content, setContent] = useState({});
  const [meta, setMeta] = useState({ worker_id: '', assignment_context: '', ref_name: '', ref_title: '', ref_email: '' });
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false); const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState(''); const [aiMsg, setAiMsg] = useState(''); const [flags, setFlags] = useState(null); const [analysis, setAnalysis] = useState({}); const [draftScore, setDraftScore] = useState(null);

  async function aiDraft() {
    setAiMsg('Drafting…'); setErr(false);
    try { const r = await api('/ai/draft', { method: 'POST', body: { notes, template_id: tpl.id } }); setContent(r.content); setAiMsg('AI draft inserted — review before publishing.'); }
    catch (e) { setErr(true); setAiMsg(e.message); }
  }
  async function aiCheck() {
    setAiMsg('Checking…'); setErr(false); setFlags(null);
    try { const r = await api('/ai/check', { method: 'POST', body: { content } });
      setFlags(r); setAiMsg(r.ok ? 'No fairness or defamation issues found.' : `${r.flags.length} issue(s) flagged.`); }
    catch (e) { setErr(true); setAiMsg(e.message); }
  }
  function applyRewrite() { if (flags?.rewritten) { setContent({ ...content, ...flags.rewritten }); setFlags(null); setAiMsg('Rewrite applied.'); } }
  async function analyseDraft() {
    setAiMsg('Analysing draft…'); setErr(false); setDraftScore(null);
    try { const r = await api('/ai/analyse', { method: 'POST', body: { content, assignment_context: meta.assignment_context } }); setDraftScore(r); setAiMsg(''); }
    catch (e) { setErr(true); setAiMsg(e.message); }
  }
  async function analyse(id) {
    setAiMsg('Analysing…'); setErr(false);
    try { const r = await api(`/references/${id}/analyse`, { method: 'POST' }); setAnalysis({ ...analysis, [id]: r }); setAiMsg(''); }
    catch (e) { setErr(true); setAiMsg(e.message); }
  }

  const load = useCallback(async () => {
    try {
      const t = await api('/templates?vertical=social_work', { auth: false });
      setTemplates(t); if (t[0]) setTpl(t[0]);
      const r = await api('/me/references'); setRefs(r.as_org || []);
    } catch (e) { setErr(true); setMsg(e.message); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const required = (tpl?.field_schema?.required) || [];
  const up = (k) => (e) => setMeta({ ...meta, [k]: e.target.value });
  const upc = (k) => (e) => setContent({ ...content, [k]: e.target.value });

  async function draft() {
    setMsg(''); setErr(false);
    if (!meta.worker_id || !/^[0-9a-fA-F-]{36}$/.test(meta.worker_id.trim())) {
      setErr(true); setMsg('Paste a valid Worker ID first (from the worker\u2019s portal).'); return;
    }
    setBusy(true);
    try {
      const body = {
        worker_id: meta.worker_id, template_id: tpl.id,
        assignment_context: meta.assignment_context, content,
        referee: meta.ref_email ? { full_name: meta.ref_name, job_title: meta.ref_title, work_email: meta.ref_email } : null,
      };
      const r = await api('/references', { method: 'POST', body });
      setContent({}); setNotes(''); setDraftScore(null); setFlags(null);
      setMeta({ worker_id: '', assignment_context: '', ref_name: '', ref_title: '', ref_email: '' });
      setMsg('Draft created' + (r.referee ? ` · referee domain verified: ${r.referee.domain_verified}` : '') + ' — it’s now in the Draft column. Drag it to Published when ready.');
      load();
    } catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
  }
  async function publish(id) {
    setMsg(''); setErr(false);
    try { const r = await api(`/references/${id}/publish`, { method: 'POST' }); setMsg('Published · hash ' + r.content_hash); load(); }
    catch (e) { setErr(true); setMsg(e.message); }
  }

  return (
    <div className="card">
      <h2>Issue a reference</h2>
      <p className="muted">Organisation set up. Draft a practice-based reference, then publish it (server computes the tamper-evident hash).</p>
      <label>Template <Help text="The reference format you are filling in. Templates follow the statutory/regulatory standard for the sector (e.g. the social-work practice-based reference) and set which fields are required." /></label>
      <select value={tpl?.id || ''} onChange={(e) => setTpl(templates.find((t) => t.id === e.target.value))}>
        {templates.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.version})</option>)}
      </select>
      <label>Worker ID (from the worker’s portal) <Help text="Every worker has a unique Reffolio Worker ID shown in their portal. Ask the worker to send it to you, then paste it here so the reference is bound to the right person." /></label>
      <input value={meta.worker_id} onChange={up('worker_id')} placeholder="paste worker_id" />
      <label>Draft with AI (paste rough notes) <Help text="Paste your rough notes about the worker. Reffolio's AI turns them into a fair, evidence-based reference filling the required fields. You can edit everything before publishing." /></label>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
        style={{ width: '100%', background: 'var(--ink)', border: '1px solid var(--line)', color: 'var(--text)', borderRadius: 9, padding: '10px 12px', fontFamily: 'inherit', fontSize: 14 }}
        placeholder="e.g. Sam worked here 2022-24 as senior practitioner, strong on assessments, no conduct issues" />
      <button className="ghost" onClick={aiDraft} disabled={!tpl || !notes}>Draft with AI</button>
      <label>Assignment context <Help text="The role or setting this reference relates to — e.g. the team, service or placement the worker was in (such as 'Children & Families team'). It gives the reader context for the reference." /></label>
      <input value={meta.assignment_context} onChange={up('assignment_context')} placeholder="Children & Families team" />
      {required.map((field) => (
        <div key={field}>
          <label>{field}</label>
          <input value={content[field] || ''} onChange={upc(field)} />
        </div>
      ))}
      <label>Referee name</label><input value={meta.ref_name} onChange={up('ref_name')} />
      <label>Referee job title</label><input value={meta.ref_title} onChange={up('ref_title')} />
      <label>Referee work email (must match your domain) <Help text="The named referee's work email. If its domain matches your organisation's verified domain, Reffolio marks it 'domain verified'. The referee is also emailed a link to personally confirm they provided the reference." /></label>
      <input value={meta.ref_email} onChange={up('ref_email')} placeholder="manager@barchester.gov.uk" />
      <div className="row">
        <button onClick={draft} disabled={busy || !tpl}>Create draft</button>
        <Help text="Saves the reference as a draft and places it in the Draft column. Nothing is published or shared yet — you publish later by dragging it to Published." />
        <button className="ghost" onClick={aiCheck} disabled={Object.keys(content).length === 0}>Check fairness</button>
        <Help text="Runs an AI check for unfair, discriminatory or potentially defamatory wording, and offers a safer rewrite you can apply with one click." />
        <button className="ghost" onClick={analyseDraft} disabled={Object.keys(content).length === 0}>Analyse draft</button>
        <Help text="Scores the draft for risk (0–100) and maps the evidence to professional frameworks (PCF/KSS), so you can sense-check it before publishing." />
        {flags && !flags.ok && Object.keys(flags.rewritten || {}).length > 0 && <button className="ghost" onClick={applyRewrite}>Apply AI rewrite</button>}
      </div>
      {draftScore && (
        <div style={{ marginTop: 8 }}>
          <div className="kv">Draft risk score: <b style={{ color: 'var(--text)' }}>{draftScore.risk_score}</b> / 100</div>
          <div className="kv">{draftScore.summary}</div>
        </div>
      )}
      {aiMsg && <div className={'msg' + (err ? ' err' : '')}>{aiMsg}</div>}
      {flags && flags.flags && flags.flags.map((fl, i) => (
        <div className="kv" key={i}>⚠ {fl.field}: {fl.issue} <span className="badge">{fl.severity}</span></div>
      ))}
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}

      <h2 style={{ marginTop: 24 }}>Issued references <Help text="Your references as a board. <b>Draft</b>: created but not yet live. <b>Published</b>: finalised with a tamper-evident hash. <b>Viewed</b>: a published reference that someone has opened. Drag a draft into Published to publish it." /></h2>
      <p className="muted">Drag a draft into <b>Published</b> to publish it (the tamper-evident hash is generated on drop).</p>
      <ReferenceBoard refs={refs} onPublish={publish} />
    </div>
  );
}

function ReferenceBoard({ refs, onPublish }) {
  const [dragId, setDragId] = useState(null);
  const [overCol, setOverCol] = useState(null);

  const drafts = refs.filter((r) => r.status !== 'published');
  const published = refs.filter((r) => r.status === 'published' && !(r.opens > 0));
  const viewed = refs.filter((r) => r.status === 'published' && r.opens > 0);

  async function onDrop(col) {
    const id = dragId; setOverCol(null); setDragId(null);
    if (!id) return;
    const ref = refs.find((r) => r.id === id);
    if (col === 'published' && ref && ref.status !== 'published') {
      await onPublish(id);
    }
  }

  const Card = (r) => {
    const isDraft = r.status !== 'published';
    return (
      <div
        key={r.id}
        className={'refcard' + (isDraft ? ' draggable' : '') + (dragId === r.id ? ' dragging' : '')}
        draggable={isDraft}
        onDragStart={isDraft ? (e) => { setDragId(r.id); e.dataTransfer.effectAllowed = 'move'; } : undefined}
        onDragEnd={() => { setDragId(null); setOverCol(null); }}
      >
        <div className="title">{r.worker_name}</div>
        <div className="kv">{r.assignment_context || '—'}</div>
        {r.published_at && <div className="kv">{new Date(r.published_at).toLocaleString()}</div>}
        {r.opens > 0 && <div className="kv">Opened {r.opens}×{r.last_opened ? ' · ' + new Date(r.last_opened).toLocaleString() : ''}</div>}
        {r.content_hash && <div className="hash">{r.content_hash.slice(0, 28)}…</div>}
      </div>
    );
  };

  const Column = (key, title, rail, cards, droppable, hint) => (
    <div
      className={'column' + (overCol === key ? ' over' : '')}
      onDragOver={droppable ? (e) => { e.preventDefault(); setOverCol(key); } : undefined}
      onDragLeave={() => setOverCol((c) => (c === key ? null : c))}
      onDrop={droppable ? () => onDrop(key) : undefined}
    >
      <div className="column-head">{title} <span className="col-count">{cards.length}</span></div>
      <div className={'col-rail rail-' + rail} />
      <div className="dropzone">
        {cards.length === 0 && <div className="col-hint">{hint}</div>}
        {cards.map(Card)}
      </div>
    </div>
  );

  return (
    <div className="board">
      {Column('draft', 'Draft', 'draft', drafts, false, 'Drafts you create appear here')}
      {Column('published', 'Published', 'published', published, true, 'Drop a draft here to publish')}
      {Column('viewed', 'Viewed', 'viewed', viewed, false, 'Published references that have been opened')}
    </div>
  );
}

function AdminOversightPanel({ me }) {
  const [activity, setActivity] = useState(null);
  const [records, setRecords] = useState([]);
  const [tab, setTab] = useState('usage');
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false);

  const load = useCallback(async () => {
    try {
      const [a, r] = await Promise.all([api('/org/activity'), api('/org/records')]);
      setActivity(a); setRecords(r.records || []);
    } catch (e) { setErr(true); setMsg(e.message); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function act(path, okMsg) {
    setMsg(''); setErr(false);
    try { await api(path, { method: 'POST' }); setMsg(okMsg); load(); }
    catch (e) { setErr(true); setMsg(e.message); }
  }

  function exportCsv() {
    const cols = ['worker_name', 'author_name', 'assignment_context', 'status', 'risk_score', 'referee_confirmed', 'opens', 'published_at', 'content_hash', 'frozen_at'];
    const esc = (v) => '"' + String(v ?? '').replace(/"/g, '""') + '"';
    const lines = [cols.join(',')].concat(records.map((r) => cols.map((c) => esc(r[c])).join(',')));
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `reffolio-records-${new Date().toISOString().slice(0, 10)}.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  if (!activity) return null;
  const t = activity.totals || {};
  const fmtDate = (d) => (d ? new Date(d).toLocaleDateString() : '—');
  const stat = (label, value) => (
    <div style={{ flex: '1 1 110px', background: 'var(--bg-soft, #fff)', border: '1px solid var(--line, #e7e9f2)', borderRadius: 12, padding: '12px 14px' }}>
      <div className="kv" style={{ textTransform: 'uppercase', fontSize: 10 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>{value}</div>
    </div>
  );

  return (
    <div className="card">
      <h2>Oversight <Help text="Your management view. See how each member uses Reffolio, browse the full record of issued references for audits or hearings, and lock a member or freeze a reference if an issue arises. Visible to admins only." /></h2>

      <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
        {stat('References', t.total ?? 0)}
        {stat('Published', t.published ?? 0)}
        {stat('Drafts', t.drafts ?? 0)}
        {stat('Recipient opens', t.total_opens ?? 0)}
        {stat('Frozen', t.frozen ?? 0)}
      </div>

      <div className="row" style={{ gap: 8, marginTop: 16 }}>
        <button className={tab === 'usage' ? '' : 'ghost'} style={{ marginTop: 0 }} onClick={() => setTab('usage')}>Team usage</button>
        <button className={tab === 'records' ? '' : 'ghost'} style={{ marginTop: 0 }} onClick={() => setTab('records')}>Records ({records.length})</button>
      </div>
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}

      {tab === 'usage' && (
        <div style={{ marginTop: 12 }}>
          {activity.members.map((m) => (
            <div className="item" key={m.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
              <div>
                <div>
                  {m.full_name} <span className="badge">{m.title || (m.role === 'org_admin' ? 'Admin' : 'Member')}</span>
                  {m.role === 'org_admin' && <span className="badge pub" style={{ marginLeft: 6 }}>admin</span>}
                  {m.is_locked && <span className="badge" style={{ marginLeft: 6, background: '#fde8e8', color: '#b42318' }}>locked</span>}
                </div>
                <div className="kv">{m.published} published · {m.drafts} drafts · last active {fmtDate(m.last_active)}</div>
              </div>
              {m.id !== me?.user_id && (
                m.is_locked
                  ? <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/org/members/${m.id}/unlock`, 'Member unlocked.')}>Unlock</button>
                  : <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/org/members/${m.id}/lock`, 'Member locked.')}>Lock</button>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === 'records' && (
        <div style={{ marginTop: 12 }}>
          <button className="ghost" style={{ marginTop: 0, marginBottom: 8 }} onClick={exportCsv} disabled={!records.length}>Download records (CSV)</button>
          {records.length === 0 && <div className="kv">No references issued yet.</div>}
          {records.map((r) => (
            <div className="item" key={r.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                <div>
                  <div>
                    <b style={{ color: 'var(--text)' }}>{r.worker_name}</b>
                    <span className="badge" style={{ marginLeft: 6 }}>{r.status}</span>
                    {r.referee_confirmed && <span className="badge pub" style={{ marginLeft: 6 }}>referee confirmed</span>}
                    {r.frozen_at && <span className="badge" style={{ marginLeft: 6, background: '#fef0c7', color: '#92600a' }}>frozen</span>}
                  </div>
                  <div className="kv">
                    by {r.author_name || '—'} · {r.assignment_context || 'no context'} · {r.opens} open{r.opens === 1 ? '' : 's'}
                    {r.risk_score != null && <> · risk {r.risk_score}</>}
                    {r.published_at && <> · published {fmtDate(r.published_at)}</>}
                  </div>
                  {r.content_hash && <div className="kv" style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>hash {String(r.content_hash).slice(0, 16)}…</div>}
                </div>
                {r.frozen_at
                  ? <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/org/references/${r.id}/unfreeze`, 'Reference unfrozen.')}>Unfreeze</button>
                  : <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/org/references/${r.id}/freeze`, 'Reference frozen — share links are now blocked.')}>Freeze</button>
                }
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WorkerPanel({ me }) {
  const [refs, setRefs] = useState([]);
  const [links, setLinks] = useState({});
  const [recipient, setRecipient] = useState({});
  const [draft, setDraft] = useState({});   // { id: { subject, body } }
  const [activity, setActivity] = useState({});
  const [pin, setPin] = useState({});
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false);

  const load = useCallback(async () => {
    try { const r = await api('/me/references'); setRefs(r.as_worker || []); }
    catch (e) { setErr(true); setMsg(e.message); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function share(r) {
    setMsg(''); setErr(false);
    const p = pin[r.id] || {};
    const body = { reference_id: r.id };
    if (p.verify && p.email && p.email.trim()) body.granted_to_email = p.email.trim();
    try {
      const resp = await api('/grants', { method: 'POST', body });
      setLinks({ ...links, [r.id]: `${window.location.origin}/share/${resp.share_token}` });
      if (p.email) setRecipient({ ...recipient, [r.id]: p.email });
    } catch (e) { setErr(true); setMsg(e.message); }
  }

  async function loadActivity(id) {
    try { const a = await api(`/references/${id}/activity`); setActivity({ ...activity, [id]: a }); }
    catch (e) { setErr(true); setMsg(e.message); }
  }

  async function generateEmail(r) {
    setMsg('Drafting email with AI…'); setErr(false);
    let subject = 'Verified employment reference', body = '';
    try { const m = await api('/ai/share-message', { method: 'POST', body: { issuing_org: r.issuing_org } });
      subject = m.subject; body = m.body; }
    catch (e) { body = 'Hello,\n\nI would like to share a verified employment reference with you.\n\nKind regards'; }
    const full = `${body}\n\nView the verified reference:\n${links[r.id]}`;
    setDraft({ ...draft, [r.id]: { subject, body: full } });
    setMsg('Email drafted — edit if you like, then copy it or open your webmail.');
  }

  async function copyEmail(id) {
    const d = draft[id]; const text = `Subject: ${d.subject}\n\n${d.body}`;
    try { await navigator.clipboard.writeText(text); setErr(false); setMsg('Email copied — paste into your email and send.'); }
    catch { setErr(true); setMsg('Copy failed — select the text and copy manually.'); }
  }
  async function copyLink(id) {
    try { await navigator.clipboard.writeText(links[id]); setErr(false); setMsg('Link copied.'); }
    catch { setErr(true); setMsg('Copy failed — select the link manually.'); }
  }
  function openWebmail(provider, id) {
    const d = draft[id];
    const to = encodeURIComponent((recipient[id] || '').trim());
    const su = encodeURIComponent(d.subject);
    const bo = encodeURIComponent(d.body);
    const urls = {
      gmail: `https://mail.google.com/mail/?view=cm&fs=1&to=${to}&su=${su}&body=${bo}`,
      outlook: `https://outlook.live.com/mail/0/deeplink/compose?to=${to}&subject=${su}&body=${bo}`,
      yahoo: `https://compose.mail.yahoo.com/?to=${to}&subject=${su}&body=${bo}`,
    };
    if (provider === 'mailto') { window.location.href = `mailto:${to}?subject=${su}&body=${bo}`; return; }
    window.open(urls[provider], '_blank');
  }

  const ta = { width: '100%', background: 'var(--ink)', border: '1px solid var(--line)', color: 'var(--text)', borderRadius: 9, padding: '10px 12px', fontFamily: 'inherit', fontSize: 14 };

  return (
    <div className="card">
      <h2>Your worker identity <Help text="Your Worker ID identifies you to organisations. Give it to an employer or council so they can write a reference bound to you. It also confirms your professional registration (e.g. Social Work England)." /></h2>
      <p className="muted">Give this Worker ID to an issuing organisation so they can write you a reference:</p>
      <div className="share">{me.worker_id}</div>

      <h2 style={{ marginTop: 24 }}>Your references <Help text="References issued about you. Create a share link to send one to an employer. You'll see when it's opened and by whom — these are your read receipts." /></h2>
      {refs.length === 0 && <p className="muted">No references yet. Once an organisation issues one, it appears here.</p>}
      {refs.map((r) => (
        <div className="item" key={r.id}>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div>
              <div>{r.issuing_org} <span className={'badge' + (r.status === 'published' ? ' pub' : '')}>{r.status}</span></div>
              <div className="kv">{r.assignment_context || '—'}</div>
              {r.status === 'published' && (
                <div className="kv">
                  {r.opens > 0
                    ? `Opened ${r.opens} time${r.opens === 1 ? '' : 's'}${r.last_opened ? ' · last ' + new Date(r.last_opened).toLocaleString() : ''}`
                    : 'Not opened yet'}
                  {r.opens > 0 && <button className="ghost" style={{ marginTop: 0, marginLeft: 10, padding: '2px 8px' }} onClick={() => loadActivity(r.id)}>View opens</button>}
                </div>
              )}
            </div>
          </div>
          {r.status === 'published' && !links[r.id] && (
            <div style={{ marginTop: 8 }}>
              <label>Recipient email (optional)</label>
              <input value={pin[r.id]?.email || ''} onChange={(e) => setPin({ ...pin, [r.id]: { ...pin[r.id], email: e.target.value } })} placeholder="hr@employer.com" />
              <div className="kv" style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                <input type="checkbox" style={{ width: 'auto' }} checked={pin[r.id]?.verify || false} onChange={(e) => setPin({ ...pin, [r.id]: { ...pin[r.id], verify: e.target.checked } })} />
                Require recipient to verify their email (one-time code) <Help text="When on, the person you send the link to must enter a one-time code emailed to that address before they can view the reference — proving they control the inbox. Your activity log then marks them as identity-verified." />
              </div>
              <button onClick={() => share(r)}>Create share link</button>
            </div>
          )}
          {activity[r.id] && (
            <div style={{ marginTop: 6 }}>
              {activity[r.id].map((a, i) => (
                <div className="kv" key={i}>👁 {a.accessed_by_name || 'Someone'}{a.accessed_by_email ? ` (${a.accessed_by_email})` : ''}{a.viewer_org ? ` · ${a.viewer_org}` : ''}{a.verified ? ' · ✓ verified' : ''} · {new Date(a.accessed_at).toLocaleString()}</div>
              ))}
            </div>
          )}

          {links[r.id] && (
            <div style={{ marginTop: 8 }}>
              <div className="share">{links[r.id]}</div>
              <label>Send to (employer email, optional)</label>
              <input value={recipient[r.id] || ''} onChange={(e) => setRecipient({ ...recipient, [r.id]: e.target.value })} placeholder="hr@employer.com" />

              {!draft[r.id] && (
                <div className="row">
                  <button onClick={() => generateEmail(r)}>Generate email with AI</button>
                  <button className="ghost" onClick={() => copyLink(r.id)}>Copy link only</button>
                </div>
              )}

              {draft[r.id] && (
                <div>
                  <label>Subject</label>
                  <input value={draft[r.id].subject} onChange={(e) => setDraft({ ...draft, [r.id]: { ...draft[r.id], subject: e.target.value } })} />
                  <label>Message (editable)</label>
                  <textarea rows={9} style={ta} value={draft[r.id].body} onChange={(e) => setDraft({ ...draft, [r.id]: { ...draft[r.id], body: e.target.value } })} />
                  <div className="row">
                    <button onClick={() => copyEmail(r.id)}>Copy email</button>
                    <button className="ghost" onClick={() => openWebmail('gmail', r.id)}>Gmail</button>
                    <button className="ghost" onClick={() => openWebmail('outlook', r.id)}>Outlook</button>
                    <button className="ghost" onClick={() => openWebmail('yahoo', r.id)}>Yahoo</button>
                    <button className="ghost" onClick={() => openWebmail('mailto', r.id)}>Email app</button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
    </div>
  );
}


function TeamPanel({ me }) {
  const [data, setData] = useState({ members: [], pending_invites: [], is_admin: false, me: '' });
  const [form, setForm] = useState({ email: '', title: '', grant_admin: false });
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false); const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setData(await api('/org/members')); } catch (e) { /* ignore */ }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function invite() {
    if (!form.email.trim()) { setErr(true); setMsg('Enter an email to invite.'); return; }
    setBusy(true); setMsg(''); setErr(false);
    try {
      const r = await api('/org/invites', { method: 'POST', body: form });
      setMsg(r.sent ? 'Invite emailed.' : 'Invite created — email isn\u2019t configured, so share this link: ' + r.invite_link);
      setForm({ email: '', title: '', grant_admin: false });
      load();
    } catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
  }
  async function removeMember(id) {
    setMsg(''); setErr(false);
    try { await api(`/org/members/${id}`, { method: 'DELETE' }); load(); }
    catch (e) { setErr(true); setMsg(e.message); }
  }
  async function cancelInvite(id) {
    setMsg(''); setErr(false);
    try { await api(`/org/invites/${id}`, { method: 'DELETE' }); load(); }
    catch (e) { setErr(true); setMsg(e.message); }
  }

  const isAdmin = me.role === 'org_admin';
  const titleOf = (x) => x.title || (x.role === 'org_admin' ? 'Admin' : 'Member');
  return (
    <div className="card">
      <h2>Team <Help text="Everyone in your organisation. The admin holds the subscription and seats; members can work but can't change billing or the team. Job title is just a label." /></h2>
      {data.members.map((m) => (
        <div className="item" key={m.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div>{m.full_name} <span className="badge">{titleOf(m)}</span>{m.role === 'org_admin' && <span className="badge pub" style={{ marginLeft: 6 }}>admin</span>}</div>
            <div className="kv">{m.email}</div>
          </div>
          {isAdmin && m.id !== data.me && (
            <button className="ghost" style={{ marginTop: 0 }} onClick={() => removeMember(m.id)}>Remove</button>
          )}
        </div>
      ))}
      {isAdmin && (
        <div style={{ marginTop: 16 }}>
          <h2>Invite a colleague <Help text="Send a seat to a colleague. They sign in with the invited email to join. Pick or type their job title, and tick admin only if they should manage billing and the team. Each member or pending invite uses one seat." /></h2>
          <label>Email</label>
          <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="colleague@yourcouncil.gov.uk" />
          <label>Job title (pick one or type your own)</label>
          <input list="titlesuggest" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Team Manager" />
          <datalist id="titlesuggest">
            <option value="Social Worker" /><option value="Senior Social Worker" /><option value="Senior Practitioner" />
            <option value="Team Manager" /><option value="Practice Manager" /><option value="Service Manager" />
            <option value="Head of Service" /><option value="Principal Social Worker" /><option value="Independent Reviewing Officer" />
            <option value="Practice Educator" /><option value="HR Manager" /><option value="Recruitment Manager" />
            <option value="Compliance Officer" /><option value="Business Support Officer" />
            <option value="Recruitment Consultant" /><option value="Senior Consultant" /><option value="Principal Consultant" />
            <option value="Managing Consultant" /><option value="Account Manager" /><option value="Branch Manager" />
            <option value="Team Leader" /><option value="Resourcing Lead" /><option value="Compliance Manager" />
            <option value="Candidate Manager" /><option value="Registration Officer" /><option value="Director" />
          </datalist>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, textTransform: 'none', letterSpacing: 0, fontSize: 13 }}>
            <input type="checkbox" style={{ width: 'auto' }} checked={form.grant_admin} onChange={(e) => setForm({ ...form, grant_admin: e.target.checked })} />
            Grant admin access (manage billing &amp; team)
          </label>
          <button onClick={invite} disabled={busy}>Send invite</button>
          {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
          {data.pending_invites.length > 0 && (
            <div style={{ marginTop: 14 }}>
              <div className="kv" style={{ textTransform: 'uppercase', fontSize: 11 }}>Pending invites</div>
              {data.pending_invites.map((p) => (
                <div className="item" key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="kv">{p.email} · {titleOf(p)}{p.role === 'org_admin' ? ' · admin' : ''}</div>
                  <button className="ghost" style={{ marginTop: 0 }} onClick={() => cancelInvite(p.id)}>Cancel</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BillingPanel({ me }) {
  const [b, setB] = useState(null);
  const [busy, setBusy] = useState('');
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false);
  const isAdmin = me.role === 'org_admin';

  const load = useCallback(async () => {
    try { setB(await api('/billing/me')); } catch (e) { /* ignore */ }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function go(path, body, key) {
    setBusy(key); setMsg(''); setErr(false);
    try { const r = await api(path, { method: 'POST', body }); if (r.url) window.location.href = r.url; else { setBusy(''); load(); } }
    catch (e) { setErr(true); setMsg(e.message); setBusy(''); }
  }

  if (!b) return null;
  const f = b.features || {};
  return (
    <div className="card">
      <h2>Billing &amp; plan <Help text="Your subscription. The admin manages the plan and seats centrally; charges are billed to the organisation. Upgrading adds seats and features." /></h2>
      <div className="kv">Plan: <b style={{ color: 'var(--text)' }}>{f.label || b.plan}</b> · {b.status}</div>
      <div className="kv">Seats: {b.seats_used} of {b.seats} used</div>
      <div className="kv">Pay-as-you-go credits: {b.credits}</div>
      {b.current_period_end && <div className="kv">Renews: {new Date(b.current_period_end).toLocaleDateString()}</div>}

      {!isAdmin && <div className="kv" style={{ marginTop: 10 }}>Billing is managed by your organisation admin.</div>}

      {isAdmin && (
        <>
          {!b.configured && <div className="msg">Billing isn\u2019t fully configured yet.</div>}
          <div className="kv" style={{ textTransform: 'uppercase', fontSize: 11, marginTop: 14 }}>Change plan</div>
          <div className="row" style={{ marginTop: 6 }}>
            <button onClick={() => go('/billing/checkout', { plan: 'starter' }, 's')} disabled={!!busy}>Starter · £49</button>
            <button onClick={() => go('/billing/checkout', { plan: 'growth' }, 'g')} disabled={!!busy}>Growth · £149</button>
            <button onClick={() => go('/billing/checkout', { plan: 'business' }, 'b')} disabled={!!busy}>Business · £299</button>
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <button className="ghost" onClick={() => go('/billing/credits/checkout', { quantity: 10 }, 'c')} disabled={!!busy}>Buy 10 credits</button>
            <button className="ghost" onClick={() => go('/billing/portal', {}, 'p')} disabled={!!busy}>Manage subscription</button>
          </div>
          {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
        </>
      )}
    </div>
  );
}
