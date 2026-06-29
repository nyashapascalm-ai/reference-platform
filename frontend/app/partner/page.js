'use client';
import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { api } from '../../lib/api';

function Icon({ name }) {
  const p = {
    home: <path d="M3 11l9-8 9 8M5 9v11h5v-6h4v6h5V9" />,
    chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
    key: <><circle cx="8" cy="15" r="4" /><path d="M10.8 12.2L20 3m-3 0l3 3m-5 2l2 2" /></>,
    activity: <><path d="M3 12h4l3 8 4-16 3 8h4" /></>,
  }[name] || null;
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{p}</svg>
  );
}

function Stat({ label, value }) {
  return (
    <div className="card" style={{ flex: '1 1 180px', margin: 0, padding: '16px 18px' }}>
      <div className="kv" style={{ textTransform: 'uppercase', fontSize: 10, letterSpacing: '.06em' }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700, marginTop: 6, color: 'var(--text)' }}>{value}</div>
    </div>
  );
}

export default function PartnerDashboard() {
  const [state, setState] = useState('loading'); // loading | signin | denied | ready
  const [data, setData] = useState(null);
  const [view, setView] = useState('overview');

  const load = useCallback(async () => {
    let { data: sess } = await supabase.auth.getSession();
    if (!sess.session) { await new Promise((r) => setTimeout(r, 600)); ({ data: sess } = await supabase.auth.getSession()); }
    if (!sess.session) { setState('signin'); return; }
    try {
      const d = await api('/partner/overview');
      setData(d); setState('ready');
    } catch (e) { setState('denied'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function signOut() { await supabase.auth.signOut(); window.location.href = '/'; }

  if (state === 'loading') return <div className="wrap"><div className="card" style={{ maxWidth: 460, margin: '60px auto' }}><p className="muted">Loading…</p></div></div>;

  if (state === 'signin') return (
    <div className="wrap"><div className="card" style={{ maxWidth: 460, margin: '60px auto' }}>
      <div className="brand" style={{ fontSize: 26 }}>Reffolio</div>
      <h2 style={{ marginTop: 12 }}>Partner dashboard</h2>
      <p className="muted">Please sign in to view your partner dashboard.</p>
      <a href="/signin" className="mk-btn mk-btn-primary" style={{ marginTop: 12, display: 'inline-block' }}>Sign in</a>
    </div></div>
  );

  if (state === 'denied') return (
    <div className="wrap"><div className="card" style={{ maxWidth: 460, margin: '60px auto' }}>
      <div className="brand" style={{ fontSize: 26 }}>Reffolio</div>
      <h2 style={{ marginTop: 12 }}>Not a partner account</h2>
      <p className="muted">This dashboard is for Reffolio integration partners. The account you{'\u2019'}re signed in as isn{'\u2019'}t linked to a partner.</p>
    </div></div>
  );

  const p = data.partner;
  const nav = [
    { id: 'overview', icon: 'chart', label: 'Overview' },
    { id: 'activity', icon: 'activity', label: 'Activity' },
    { id: 'apikeys', icon: 'key', label: 'API keys' },
  ];
  const NavItem = ({ id, icon, label }) => (
    <button onClick={() => setView(id)} style={{
      display: 'flex', alignItems: 'center', gap: 11, width: '100%', textAlign: 'left',
      background: view === id ? 'rgba(108,92,231,.10)' : 'transparent',
      color: view === id ? 'var(--violet, #6C5CE7)' : 'var(--text)',
      border: 'none', borderRadius: 10, padding: '10px 12px', margin: '2px 0', cursor: 'pointer',
      fontSize: 14, fontWeight: 600, boxShadow: 'none',
    }}><Icon name={icon} /> {label}</button>
  );

  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'stretch' }}>
      <aside style={{ width: 248, flexShrink: 0, borderRight: '1px solid var(--line-soft, #e7e9f2)', padding: '20px 14px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '4px 8px 16px', fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 19 }}>
          <img src="/icon.svg" alt="" style={{ width: 26, height: 26, borderRadius: 7 }} /> Reffolio
        </div>
        {nav.map((n) => <NavItem key={n.id} {...n} />)}
        <div style={{ marginTop: 'auto', padding: '12px 8px 4px', borderTop: '1px solid var(--line-soft, #e7e9f2)' }}>
          <div style={{ fontSize: 12.5, color: 'var(--muted)', marginBottom: 2 }}>{p.name}</div>
          <div style={{ fontSize: 11.5, color: 'var(--muted)', marginBottom: 8 }}>Integration partner</div>
          <button className="ghost" style={{ marginTop: 0, width: '100%' }} onClick={signOut}>Sign out</button>
        </div>
      </aside>

      <main style={{ flex: 1, minWidth: 0, padding: '28px 32px', maxWidth: 1080 }}>
        {view === 'overview' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
              <h1 style={{ margin: 0 }}>{p.name}</h1>
              <span className="kv">£{p.price_per_ref.toFixed(2)} per reference{!p.active && ' · (inactive)'}</span>
            </div>

            <h2 style={{ marginTop: 24, fontSize: 18 }}>This month</h2>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <Stat label="References" value={data.this_month.refs} />
              <Stat label="Amount due" value={`£${data.this_month.amount.toFixed(2)}`} />
            </div>

            <h2 style={{ marginTop: 28, fontSize: 18 }}>All time</h2>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <Stat label="References" value={data.all_time.refs} />
              <Stat label="Amount invoiced" value={`£${data.all_time.amount.toFixed(2)}`} />
            </div>

            <p className="kv" style={{ marginTop: 28, maxWidth: 620, lineHeight: 1.6 }}>
              Amount due is your references multiplied by your agreed fee of £{p.price_per_ref.toFixed(2)} per reference. You{'\u2019'}re invoiced monthly. Figures update as references reach verified consent.
            </p>
          </>
        )}

        {view === 'activity' && (
          <>
            <h1 style={{ margin: 0 }}>Activity</h1>
            <p className="kv" style={{ marginTop: 12 }}>A breakdown of references by your clients is coming soon. For now, your totals are on the Overview page.</p>
          </>
        )}

        {view === 'apikeys' && (
          <>
            <h1 style={{ margin: 0 }}>API keys</h1>
            <p className="kv" style={{ marginTop: 12 }}>Self-service API key management is coming soon. For now, your integration key was provided when your account was set up. Contact Reffolio if you need it reissued.</p>
          </>
        )}
      </main>
    </div>
  );
}
