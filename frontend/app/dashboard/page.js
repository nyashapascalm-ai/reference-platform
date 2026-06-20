'use client';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../../lib/supabaseClient';
import { api } from '../../lib/api';

export default function Dashboard() {
  const router = useRouter();
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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
          <h1>Dashboard</h1>
          <p className="muted">{me?.email}{me?.role ? ` · ${me.role}` : ''}</p>
        </div>
        <button className="ghost" onClick={signOut}>Sign out</button>
      </div>
      {error && <div className="msg err">{error}</div>}

      {!me?.org_id && !me?.worker_id && <Onboarding onDone={loadMe} />}
      {me?.org_id && <OrgPanel me={me} />}
      {me?.worker_id && <WorkerPanel me={me} />}
    </div>
  );
}

function Onboarding({ onDone }) {
  return (
    <>
      <p className="muted">You’re signed in but not set up yet. Choose one:</p>
      <CreateOrg onDone={onDone} />
      <RegisterWorker onDone={onDone} />
    </>
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
  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit() {
    setBusy(true); setMsg(''); setErr(false);
    try { await api('/workers/verify', { method: 'POST', body: f }); onDone(); }
    catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
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
  const [notes, setNotes] = useState(''); const [aiMsg, setAiMsg] = useState(''); const [flags, setFlags] = useState(null); const [analysis, setAnalysis] = useState({});

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
    setBusy(true); setMsg(''); setErr(false);
    try {
      const body = {
        worker_id: meta.worker_id, template_id: tpl.id,
        assignment_context: meta.assignment_context, content,
        referee: meta.ref_email ? { full_name: meta.ref_name, job_title: meta.ref_title, work_email: meta.ref_email } : null,
      };
      const r = await api('/references', { method: 'POST', body });
      setMsg('Draft created' + (r.referee ? ` · referee domain_verified: ${r.referee.domain_verified}` : ''));
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
      <label>Template</label>
      <select value={tpl?.id || ''} onChange={(e) => setTpl(templates.find((t) => t.id === e.target.value))}>
        {templates.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.version})</option>)}
      </select>
      <label>Worker ID (from the worker’s portal)</label>
      <input value={meta.worker_id} onChange={up('worker_id')} placeholder="paste worker_id" />
      <label>Draft with AI (paste rough notes)</label>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
        style={{ width: '100%', background: 'var(--ink)', border: '1px solid var(--line)', color: 'var(--text)', borderRadius: 9, padding: '10px 12px', fontFamily: 'inherit', fontSize: 14 }}
        placeholder="e.g. Sam worked here 2022-24 as senior practitioner, strong on assessments, no conduct issues" />
      <button className="ghost" onClick={aiDraft} disabled={!tpl || !notes}>Draft with AI</button>
      <label>Assignment context</label>
      <input value={meta.assignment_context} onChange={up('assignment_context')} placeholder="Children & Families team" />
      {required.map((field) => (
        <div key={field}>
          <label>{field}</label>
          <input value={content[field] || ''} onChange={upc(field)} />
        </div>
      ))}
      <label>Referee name</label><input value={meta.ref_name} onChange={up('ref_name')} />
      <label>Referee job title</label><input value={meta.ref_title} onChange={up('ref_title')} />
      <label>Referee work email (must match your domain)</label>
      <input value={meta.ref_email} onChange={up('ref_email')} placeholder="manager@barchester.gov.uk" />
      <div className="row">
        <button onClick={draft} disabled={busy || !tpl}>Create draft</button>
        <button className="ghost" onClick={aiCheck} disabled={Object.keys(content).length === 0}>Check fairness</button>
        {flags && !flags.ok && Object.keys(flags.rewritten || {}).length > 0 && <button className="ghost" onClick={applyRewrite}>Apply AI rewrite</button>}
      </div>
      {aiMsg && <div className={'msg' + (err ? ' err' : '')}>{aiMsg}</div>}
      {flags && flags.flags && flags.flags.map((fl, i) => (
        <div className="kv" key={i}>⚠ {fl.field}: {fl.issue} <span className="badge">{fl.severity}</span></div>
      ))}
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}

      <h2 style={{ marginTop: 24 }}>Issued references</h2>
      {refs.length === 0 && <p className="muted">None yet.</p>}
      {refs.map((r) => (
        <div className="item" key={r.id}>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div>
              <div>{r.worker_name} <span className={'badge' + (r.status === 'published' ? ' pub' : '')}>{r.status}</span></div>
              <div className="kv">{r.assignment_context || '—'}</div>
              {r.content_hash && <div className="hash">{r.content_hash}</div>}
            </div>
            {r.status !== 'published' && <button onClick={() => publish(r.id)}>Publish</button>}
            {r.status === 'published' && <button className="ghost" onClick={() => analyse(r.id)}>Analyse with AI</button>}
          </div>
          {analysis[r.id] && (
            <div style={{ marginTop: 8 }}>
              <div className="kv">Risk score: <b style={{ color: 'var(--text)' }}>{analysis[r.id].risk_score}</b> / 100</div>
              <div className="kv">{analysis[r.id].summary}</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function WorkerPanel({ me }) {
  const [refs, setRefs] = useState([]);
  const [links, setLinks] = useState({});
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false);

  const load = useCallback(async () => {
    try { const r = await api('/me/references'); setRefs(r.as_worker || []); }
    catch (e) { setErr(true); setMsg(e.message); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function share(id) {
    setMsg(''); setErr(false);
    try {
      const r = await api('/grants', { method: 'POST', body: { reference_id: id } });
      const url = `${window.location.origin}/share/${r.share_token}`;
      setLinks({ ...links, [id]: url });
    } catch (e) { setErr(true); setMsg(e.message); }
  }

  return (
    <div className="card">
      <h2>Your worker identity</h2>
      <p className="muted">Give this Worker ID to an issuing organisation so they can write you a reference:</p>
      <div className="share">{me.worker_id}</div>

      <h2 style={{ marginTop: 24 }}>Your references</h2>
      {refs.length === 0 && <p className="muted">No references yet. Once an organisation issues one, it appears here.</p>}
      {refs.map((r) => (
        <div className="item" key={r.id}>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div>
              <div>{r.issuing_org} <span className={'badge' + (r.status === 'published' ? ' pub' : '')}>{r.status}</span></div>
              <div className="kv">{r.assignment_context || '—'}</div>
            </div>
            {r.status === 'published' && <button onClick={() => share(r.id)}>Create share link</button>}
          </div>
          {links[r.id] && <div className="share">{links[r.id]}</div>}
        </div>
      ))}
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
    </div>
  );
}
