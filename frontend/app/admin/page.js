'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../../lib/supabaseClient';
import { api } from '../../lib/api';

export default function AdminConsole() {
  const router = useRouter();
  const [state, setState] = useState('loading'); // loading | denied | ready
  const [overview, setOverview] = useState(null);
  const [orgs, setOrgs] = useState([]);

  const load = useCallback(async () => {
    const { data } = await supabase.auth.getSession();
    if (!data.session) { router.push('/'); return; }
    try {
      const [ov, og] = await Promise.all([api('/admin/overview'), api('/admin/orgs')]);
      setOverview(ov); setOrgs(og.orgs || []); setState('ready');
    } catch (e) {
      setState('denied');
    }
  }, [router]);
  useEffect(() => { load(); }, [load]);

  if (state === 'loading') return <div className="wrap"><div className="muted">Loading…</div></div>;
  if (state === 'denied') return (
    <div className="center">
      <div className="brand">Reffolio</div>
      <div className="card" style={{ marginTop: 20 }}>
        <h2>Admin console</h2>
        <p className="muted">This area is for Reffolio staff only. Your account doesn\u2019t have access.</p>
        <button onClick={() => router.push('/dashboard')}>Back to dashboard</button>
      </div>
    </div>
  );

  const t = overview.totals || {};
  const stat = (label, value) => (
    <div className="card" style={{ flex: '1 1 150px', margin: 0, padding: '16px 18px' }}>
      <div className="kv" style={{ textTransform: 'uppercase', fontSize: 11 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 700, color: 'var(--text)' }}>{value}</div>
    </div>
  );

  return (
    <div className="wrap">
      <div className="topbar">
        <div>
          <div className="brand" style={{ fontSize: 28 }}>Reffolio</div>
          <div className="muted">Admin console — platform overview</div>
        </div>
        <button className="ghost" style={{ marginTop: 0 }} onClick={() => router.push('/dashboard')}>Exit</button>
      </div>

      <div className="row" style={{ gap: 12, alignItems: 'stretch' }}>
        {stat('Est. MRR', '\u00a3' + (overview.estimated_mrr_gbp || 0).toLocaleString())}
        {stat('Est. ARR', '\u00a3' + (overview.estimated_arr_gbp || 0).toLocaleString())}
        {stat('Organisations', t.orgs ?? 0)}
        {stat('Workers', t.workers ?? 0)}
      </div>
      <div className="row" style={{ gap: 12, alignItems: 'stretch', marginTop: 12 }}>
        {stat('References', t.references ?? 0)}
        {stat('Published', t.references_published ?? 0)}
        {stat('Org members', t.org_members ?? 0)}
        {stat('New orgs (7d)', t.new_orgs_7d ?? 0)}
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <h2>Subscriptions</h2>
        {Object.keys(overview.active_subscriptions || {}).length === 0 && <div className="muted">No active subscriptions yet.</div>}
        {Object.entries(overview.active_subscriptions || {}).map(([plan, n]) => (
          <div className="item" key={plan} style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>{plan}</div><div className="kv">{n} active</div>
          </div>
        ))}
        <div className="kv" style={{ marginTop: 10 }}>Credits outstanding: {t.credits_outstanding ?? 0} · SWE register rows: {t.swe_register_rows ?? 0}</div>
      </div>

      <div className="card">
        <h2>Users by role</h2>
        {Object.entries(overview.roles || {}).map(([role, n]) => (
          <div className="item" key={role} style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>{(role || '').replace('_', ' ')}</div><div className="kv">{n}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Organisations ({orgs.length})</h2>
        {orgs.map((o) => (
          <div className="item" key={o.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div><b style={{ color: 'var(--text)' }}>{o.name}</b> <span className="badge">{o.plan}</span> <span className="badge">{o.status}</span></div>
              <div className="kv">{new Date(o.created_at).toLocaleDateString()}</div>
            </div>
            <div className="kv">{(o.org_type || '').replace('_', ' ')} · {(o.vertical || '').replace('_', ' ')} · {o.members} member{o.members === 1 ? '' : 's'} of {o.seats} seats · {o.refs} reference{o.refs === 1 ? '' : 's'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
