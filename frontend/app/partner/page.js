'use client';
import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { api } from '../../lib/api';

function Stat({ label, value }) {
  return (
    <div className="card" style={{ flex: '1 1 160px', margin: 0, padding: '14px 16px' }}>
      <div className="kv" style={{ textTransform: 'uppercase', fontSize: 10, letterSpacing: '.06em' }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}

export default function PartnerDashboard() {
  const [state, setState] = useState('loading'); // loading | signin | denied | ready
  const [data, setData] = useState(null);

  const load = useCallback(async () => {
    let { data: sess } = await supabase.auth.getSession();
    if (!sess.session) { await new Promise((r) => setTimeout(r, 600)); ({ data: sess } = await supabase.auth.getSession()); }
    if (!sess.session) { setState('signin'); return; }
    try {
      const d = await api('/partner/overview');
      setData(d); setState('ready');
    } catch (e) {
      setState('denied');
    }
  }, []);
  useEffect(() => { load(); }, [load]);

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
  return (
    <div className="wrap" style={{ maxWidth: 920, margin: '0 auto', padding: '24px 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
        <h1 style={{ margin: 0 }}>{p.name}</h1>
        <span className="kv">Partner dashboard</span>
      </div>
      <p className="kv" style={{ marginTop: 4 }}>
        £{p.price_per_ref.toFixed(2)} per reference
        {!p.active && ' · (inactive)'}
      </p>

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

      <p className="kv" style={{ marginTop: 28 }}>
        Amount due is your references multiplied by your agreed fee. You're invoiced monthly. Figures update as references reach verified consent.
      </p>
    </div>
  );
}
