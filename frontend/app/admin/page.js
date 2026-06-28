'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../../lib/supabaseClient';
import { api } from '../../lib/api';

export default function AdminConsole() {
  const router = useRouter();
  const [state, setState] = useState('loading'); // loading | signin | denied | ready
  const [email, setEmail] = useState('');
  const [overview, setOverview] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [orgs, setOrgs] = useState([]);
  const [partnersOverview, setPartnersOverview] = useState(null);
  const [npName, setNpName] = useState(''); const [npEmail, setNpEmail] = useState('');
  const [npPrice, setNpPrice] = useState(''); const [npShare, setNpShare] = useState('');
  const [issuedKey, setIssuedKey] = useState(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false);
  const [delTarget, setDelTarget] = useState(null); const [delText, setDelText] = useState('');

  const reload = useCallback(async (incArch) => {
    const [ov, an, og, po] = await Promise.all([
      api('/admin/overview'), api('/admin/analytics'),
      api(`/admin/orgs${incArch ? '?include_archived=true' : ''}`),
      api('/admin/partners-overview').catch(() => null),
    ]);
    setOverview(ov); setAnalytics(an); setOrgs(og.orgs || []); setPartnersOverview(po);
  }, []);

  async function createPartner() {
    setErr(false); setMsg('');
    if (!npName.trim()) { setErr(true); setMsg('Partner name is required.'); return; }
    try {
      await api('/admin/partners', { method: 'POST', body: {
        name: npName.trim(), contact_email: npEmail.trim() || null,
        price_per_ref: npPrice ? parseFloat(npPrice) : null,
        rev_share_pct: npShare ? parseFloat(npShare) : null,
      }});
      setNpName(''); setNpEmail(''); setNpPrice(''); setNpShare('');
      setMsg('Partner created.'); await reload(includeArchived);
    } catch (e) { setErr(true); setMsg(e.message); }
  }
  async function issuePartnerKey(partnerId) {
    setErr(false); setMsg(''); setIssuedKey(null);
    const orgId = window.prompt('Org ID this key operates through (the partner home org or a customer org):');
    if (!orgId) return;
    try {
      const r = await api(`/admin/partners/${partnerId}/issue-key`, { method: 'POST', body: { org_id: orgId.trim() } });
      setIssuedKey({ partner: partnerId, key: r.key });
      setMsg('Key issued - copy it now, it is shown once.');
    } catch (e) { setErr(true); setMsg(e.message); }
  }
  async function attachPartnerOrg(partnerId) {
    setErr(false); setMsg('');
    const orgId = window.prompt('Org ID to attach to this partner (references from it attribute to the partner):');
    if (!orgId) return;
    try {
      await api(`/admin/partners/${partnerId}/attach-org`, { method: 'POST', body: { org_id: orgId.trim() } });
      setMsg('Org attached to partner.'); await reload(includeArchived);
    } catch (e) { setErr(true); setMsg(e.message); }
  }

  const load = useCallback(async () => {
    let { data } = await supabase.auth.getSession();
    if (!data.session) { await new Promise((r) => setTimeout(r, 600)); ({ data } = await supabase.auth.getSession()); }
    if (!data.session) { setState('signin'); return; }
    try { const me = await api('/me'); setEmail(me.email || ''); } catch (e) { /* ignore */ }
    try { await reload(false); setState('ready'); } catch (e) { setState('denied'); }
  }, [reload]);
  useEffect(() => { load(); }, [load]);

  async function act(path, okMsg) {
    setMsg(''); setErr(false);
    try { await api(path, { method: 'POST' }); setMsg(okMsg); await reload(includeArchived); }
    catch (e) { setErr(true); setMsg(e.message); }
  }
  async function toggleArchived(next) {
    setIncludeArchived(next);
    try { await reload(next); } catch (e) { setErr(true); setMsg(e.message); }
  }
  async function confirmDelete() {
    if (!delTarget) return;
    setMsg(''); setErr(false);
    try {
      await api(`/admin/orgs/${delTarget.id}`, { method: 'DELETE', body: { confirm_name: delText } });
      setMsg(`Deleted ${delTarget.name}.`); setDelTarget(null); setDelText('');
      await reload(includeArchived);
    } catch (e) { setErr(true); setMsg(e.message); }
  }

  async function downloadReport(kind) {
    setMsg(''); setErr(false);
    let rep;
    try { rep = await api('/admin/report'); } catch (e) { setErr(true); setMsg(e.message); return; }
    const rows = rep.rows || [];
    const cols = ['name', 'org_type', 'vertical', 'plan', 'status', 'seats', 'members', 'refs', 'published', 'created_at', 'last_reference_at', 'is_suspended', 'archived_at'];
    if (kind === 'csv') {
      const esc = (v) => '"' + String(v ?? '').replace(/"/g, '""') + '"';
      const lines = [cols.join(',')].concat(rows.map((r) => cols.map((c) => esc(r[c])).join(',')));
      const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `reffolio-report-${new Date().toISOString().slice(0, 10)}.csv`; a.click();
      URL.revokeObjectURL(url);
    } else {
      const head = cols.map((c) => `<th>${c.replace(/_/g, ' ')}</th>`).join('');
      const body = rows.map((r) => '<tr>' + cols.map((c) => `<td>${r[c] == null ? '' : String(r[c])}</td>`).join('') + '</tr>').join('');
      const w = window.open('', '_blank');
      w.document.write(`<html><head><title>Reffolio report</title><style>
        body{font-family:-apple-system,Segoe UI,sans-serif;color:#0B0E1A;padding:28px}
        h1{font-size:20px;margin:0 0 4px} .sub{color:#4A5170;font-size:12px;margin-bottom:18px}
        table{border-collapse:collapse;width:100%;font-size:11px}
        th,td{border:1px solid #e7e9f2;padding:6px 8px;text-align:left}
        th{background:#f4f6fc;text-transform:uppercase;font-size:10px;letter-spacing:.04em}
      </style></head><body>
        <h1>Reffolio — platform report</h1>
        <div class="sub">Generated ${new Date(rep.generated_at).toLocaleString()} · ${rows.length} organisations</div>
        <table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
      </body></html>`);
      w.document.close(); w.focus(); setTimeout(() => w.print(), 300);
    }
  }

  if (state === 'loading') return <div className="wrap"><div className="muted">Loading…</div></div>;
  if (state === 'signin') return (
    <div className="wrap"><div className="card" style={{ maxWidth: 460, margin: '60px auto' }}>
      <div className="brand" style={{ fontSize: 26 }}>Reffolio</div>
      <h2 style={{ marginTop: 12 }}>Admin console</h2>
      <p className="muted">You need to be signed in to view this page.</p>
      <button onClick={() => router.push('/signin')}>Go to sign in</button>
    </div></div>
  );
  if (state === 'denied') return (
    <div className="wrap"><div className="card" style={{ maxWidth: 460, margin: '60px auto' }}>
      <div className="brand" style={{ fontSize: 26 }}>Reffolio</div>
      <h2 style={{ marginTop: 12 }}>Staff access only</h2>
      <p className="muted">This console is for Reffolio staff. The account you{'\u2019'}re signed in as doesn{'\u2019'}t have access.</p>
      {email && <p className="kv">Signed in as <b style={{ color: 'var(--text)' }}>{email}</b>. To grant access, add this exact address to <code>SUPER_ADMIN_EMAILS</code> in Railway.</p>}
      <button className="ghost" onClick={() => router.push('/dashboard')}>Back to dashboard</button>
    </div></div>
  );

  const t = overview.totals || {};
  const pct = (x) => `${Math.round((x || 0) * 100)}%`;
  const stat = (label, value, sub) => (
    <div className="card" style={{ flex: '1 1 150px', margin: 0, padding: '14px 16px' }}>
      <div className="kv" style={{ textTransform: 'uppercase', fontSize: 10 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, color: 'var(--text)' }}>{value}</div>
      {sub && <div className="kv" style={{ fontSize: 11 }}>{sub}</div>}
    </div>
  );

  const a = analytics || {};
  const subs = a.subscriptions || {}; const seats = a.seats || {}; const churn = a.churn || {}; const growth = a.growth || {}; const life = a.lifecycle || {};

  return (
    <div className="wrap">
      <div className="topbar">
        <div>
          <div className="brand" style={{ fontSize: 28 }}>Reffolio</div>
          <div className="muted">Admin console{email ? ` · ${email}` : ''}</div>
        </div>
        <button className="ghost" style={{ marginTop: 0 }} onClick={() => router.push('/dashboard')}>Exit</button>
      </div>

      <div className="row" style={{ gap: 12, alignItems: 'stretch' }}>
        {stat('Est. MRR', '\u00a3' + (overview.estimated_mrr_gbp || 0).toLocaleString())}
        {stat('Est. ARR', '\u00a3' + (overview.estimated_arr_gbp || 0).toLocaleString())}
        {stat('Churn (snapshot)', pct(churn.rate), `${churn.cancels_30d || 0} cancels / 30d`)}
        {stat('Seat utilisation', pct(seats.utilisation), `${seats.used || 0} of ${seats.subscribed || 0} seats`)}
      </div>
      <div className="row" style={{ gap: 12, alignItems: 'stretch', marginTop: 12 }}>
        {stat('Active subs', subs.active ?? 0)}
        {stat('Cancelled', subs.canceled ?? 0)}
        {stat('Past due', subs.past_due ?? 0)}
        {stat('Suspended', life.suspended ?? 0)}
      </div>
      <div className="row" style={{ gap: 12, alignItems: 'stretch', marginTop: 12 }}>
        {stat('New orgs 7d', growth.new_7d ?? 0)}
        {stat('New orgs 30d', growth.new_30d ?? 0)}
        {stat('New orgs 90d', growth.new_90d ?? 0)}
        {stat('References', t.references ?? 0, `${t.references_published ?? 0} published`)}
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <h2>Reports</h2>
        <p className="kv">Download the full per-organisation dataset (plan, status, seats, members, references, activity).</p>
        <div className="row" style={{ gap: 8 }}>
          <button onClick={() => downloadReport('csv')}>Download CSV</button>
          <button className="ghost" onClick={() => downloadReport('pdf')}>Download PDF</button>
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <h2 style={{ marginTop: 0 }}>Partners {partnersOverview?.partners ? `(${partnersOverview.partners.length})` : ''}</h2>
        <p className="kv">Per-reference revenue by partner. Gross = references &times; price. Their share = gross &times; rev-share %. Net = what Reffolio keeps.</p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end', margin: '12px 0 16px' }}>
          <div><div className="kv">Name</div><input value={npName} onChange={(e) => setNpName(e.target.value)} placeholder="e.g. uCheck" style={{ minWidth: 150 }} /></div>
          <div><div className="kv">Contact email</div><input value={npEmail} onChange={(e) => setNpEmail(e.target.value)} placeholder="partner@example.com" /></div>
          <div><div className="kv">£/ref</div><input value={npPrice} onChange={(e) => setNpPrice(e.target.value)} placeholder="5.00" style={{ width: 80 }} /></div>
          <div><div className="kv">Share %</div><input value={npShare} onChange={(e) => setNpShare(e.target.value)} placeholder="30" style={{ width: 70 }} /></div>
          <button onClick={createPartner}>Create partner</button>
        </div>
        {issuedKey && (
          <div className="card" style={{ background: 'rgba(0,184,166,.06)', border: '1px solid var(--accent, #00B8A6)', margin: '0 0 14px' }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>Partner key - copy it now</div>
            <code style={{ background: '#0c1020', color: '#fff', padding: '8px 12px', borderRadius: 8, wordBreak: 'break-all', display: 'inline-block', fontSize: 13 }}>{issuedKey.key}</code>
          </div>
        )}
        {!partnersOverview && <p className="kv">Loading partner data...</p>}
        {partnersOverview && partnersOverview.partners.length === 0 && <p className="kv">No partners yet. Create one above.</p>}
        {partnersOverview && partnersOverview.partners.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead><tr style={{ textAlign: 'left', borderBottom: '2px solid var(--line, #e7e9f2)' }}>
                <th style={{ padding: '8px 10px' }}>Partner</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>£/ref</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Share %</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Refs (mo)</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Net (mo)</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Refs (all)</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Gross (all)</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Their share</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Net (all)</th>
                <th style={{ padding: '8px 10px', textAlign: 'right' }}>Actions</th>
              </tr></thead>
              <tbody>
                {partnersOverview.partners.map((p) => (
                  <tr key={p.id} style={{ borderBottom: '1px solid var(--line, #eee)' }}>
                    <td style={{ padding: '8px 10px' }}>{p.name}{!p.active && <span className="kv"> (inactive)</span>}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>£{p.price_per_ref.toFixed(2)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>{p.rev_share_pct.toFixed(0)}%</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>{p.this_month.refs}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>£{p.this_month.reffolio_net.toFixed(2)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>{p.all_time.refs}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>£{p.all_time.gross.toFixed(2)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right' }}>£{p.all_time.partner_share.toFixed(2)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600 }}>£{p.all_time.reffolio_net.toFixed(2)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <button className="ghost" style={{ marginTop: 0, padding: '4px 8px', fontSize: 12 }} onClick={() => issuePartnerKey(p.id)}>Issue key</button>{' '}
                      <button className="ghost" style={{ marginTop: 0, padding: '4px 8px', fontSize: 12 }} onClick={() => attachPartnerOrg(p.id)}>Attach org</button>
                    </td>
                  </tr>
                ))}
                <tr style={{ borderTop: '2px solid var(--line, #e7e9f2)', fontWeight: 700 }}>
                  <td style={{ padding: '8px 10px' }}>Totals</td><td></td><td></td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>{partnersOverview.totals.this_month.refs}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>£{partnersOverview.totals.this_month.reffolio_net.toFixed(2)}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>{partnersOverview.totals.all_time.refs}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>£{partnersOverview.totals.all_time.gross.toFixed(2)}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>£{partnersOverview.totals.all_time.partner_share.toFixed(2)}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'right' }}>£{partnersOverview.totals.all_time.reffolio_net.toFixed(2)}</td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>Organisations ({orgs.length})</h2>
          <label className="kv" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" style={{ width: 'auto' }} checked={includeArchived} onChange={(e) => toggleArchived(e.target.checked)} />
            show archived
          </label>
        </div>
        {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
        {orgs.map((o) => (
          <div className="item" key={o.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
              <div>
                <div>
                  <b style={{ color: 'var(--text)' }}>{o.name}</b>{' '}
                  <span className="badge">{o.plan}</span> <span className="badge">{o.status}</span>
                  {o.is_suspended && <span className="badge" style={{ marginLeft: 4, background: '#fef0c7', color: '#92600a' }}>suspended</span>}
                  {o.archived_at && <span className="badge" style={{ marginLeft: 4, background: '#fde8e8', color: '#b42318' }}>archived</span>}
                </div>
                <div className="kv">
                  {(o.org_type || '').replace('_', ' ')} · {o.members} of {o.seats} seats · {o.refs} reference{o.refs === 1 ? '' : 's'} · joined {new Date(o.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
            <div className="row" style={{ gap: 6, marginTop: 8 }}>
              {o.is_suspended
                ? <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/admin/orgs/${o.id}/unsuspend`, `${o.name} unsuspended.`)}>Unsuspend</button>
                : <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/admin/orgs/${o.id}/suspend`, `${o.name} suspended.`)}>Suspend</button>}
              {o.archived_at
                ? <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/admin/orgs/${o.id}/unarchive`, `${o.name} restored.`)}>Unarchive</button>
                : <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/admin/orgs/${o.id}/archive`, `${o.name} archived.`)}>Archive</button>}
              {o.status === 'active' && <button className="ghost" style={{ marginTop: 0 }} onClick={() => act(`/admin/orgs/${o.id}/cancel-subscription`, `Subscription cancelled for ${o.name}.`)}>Cancel sub</button>}
              <button className="ghost" style={{ marginTop: 0, color: '#b42318', borderColor: '#f3c2c2' }} onClick={() => { setDelTarget(o); setDelText(''); }}>Delete</button>
            </div>
          </div>
        ))}
      </div>

      {delTarget && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(11,14,26,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 50 }} onClick={() => setDelTarget(null)}>
          <div className="card" style={{ maxWidth: 440, width: '100%', margin: 0 }} onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginTop: 0 }}>Delete {delTarget.name}?</h2>
            <p className="kv">This permanently deletes the organisation and <b style={{ color: 'var(--text)' }}>all its references</b>. This cannot be undone. For records you may need later, archive instead.</p>
            <label>Type the organisation name to confirm</label>
            <input value={delText} onChange={(e) => setDelText(e.target.value)} placeholder={delTarget.name} />
            <div className="row" style={{ gap: 8, marginTop: 10 }}>
              <button style={{ background: '#b42318' }} disabled={delText.trim() !== delTarget.name} onClick={confirmDelete}>Delete permanently</button>
              <button className="ghost" style={{ marginTop: 0 }} onClick={() => setDelTarget(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
