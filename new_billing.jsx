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
  const current = (b.plan || 'free').toLowerCase();

  // Columns reflect what the backend actually enforces (seats, api, white_label).
  const PLANS = [
    { id: 'free',     name: 'Free',     price: '£0',       blurb: 'Trying Reffolio or a single team.' },
    { id: 'starter',  name: 'Starter',  price: '£49/mo',   blurb: 'A small team running references regularly.' },
    { id: 'growth',   name: 'Growth',   price: '£149/mo',  blurb: 'Busy departments and growing agencies.', popular: true },
    { id: 'business', name: 'Business', price: '£299/mo',  blurb: 'Large teams and multi-branch agencies.' },
  ];
  // Each row: label, help, and value per plan ('yes' | 'no' | custom string).
  const ROWS = [
    { label: 'Manager seats', vals: { free: '2', starter: '3', growth: '10', business: '25' } },
    { label: 'Issue & verify references', vals: { free: 'yes', starter: 'yes', growth: 'yes', business: 'yes' } },
    { label: 'Tamper-evident records', vals: { free: 'yes', starter: 'yes', growth: 'yes', business: 'yes' } },
    { label: 'Consent-based worker sharing', vals: { free: 'yes', starter: 'yes', growth: 'yes', business: 'yes' } },
    { label: 'AI fairness + sector analysis', vals: { free: 'yes', starter: 'yes', growth: 'yes', business: 'yes' } },
    { label: 'Team management & invites', vals: { free: 'yes', starter: 'yes', growth: 'yes', business: 'yes' } },
    { label: 'Admin oversight & records', vals: { free: 'yes', starter: 'yes', growth: 'yes', business: 'yes' } },
    { label: 'Pay-as-you-go credits', vals: { free: 'yes', starter: 'yes', growth: 'yes', business: 'yes' } },
    { label: 'API access', vals: { free: 'no', starter: 'no', growth: 'yes', business: 'yes' } },
    { label: 'White-label', vals: { free: 'no', starter: 'no', growth: 'yes', business: 'yes' } },
    { label: 'Support', vals: { free: 'Community', starter: 'Email', growth: 'Priority', business: 'Priority' } },
  ];

  const cell = (v) => {
    if (v === 'yes') return <span style={{ color: 'var(--accent, #00B8A6)', fontWeight: 700 }}>{'\u2713'}</span>;
    if (v === 'no') return <span style={{ color: 'var(--muted)' }}>{'\u2014'}</span>;
    return <span style={{ color: 'var(--text)' }}>{v}</span>;
  };
  const planAction = (p) => {
    if (p.id === 'free') {
      return current === 'free'
        ? <span className="badge pub">Current plan</span>
        : <span className="kv" style={{ fontSize: 12 }}>Downgrade via Manage</span>;
    }
    if (current === p.id) {
      return <button className="ghost" style={{ marginTop: 0, width: '100%' }} onClick={() => go('/billing/portal', {}, 'p')} disabled={!!busy}>Manage</button>;
    }
    const key = p.id[0];
    return <button style={{ marginTop: 0, width: '100%' }} onClick={() => go('/billing/checkout', { plan: p.id }, key)} disabled={!!busy}>Choose {p.name}</button>;
  };

  return (
    <div className="card">
      <h2>Billing &amp; plan <Help text="Your subscription. The admin manages the plan and seats centrally; charges are billed to the organisation. Upgrading adds seats and features." /></h2>
      <div className="kv">Current plan: <b style={{ color: 'var(--text)' }}>{f.label || b.plan}</b> {'\u00b7'} {b.status}</div>
      <div className="kv">Seats: {b.seats_used} of {b.seats} used {'\u00b7'} {b.credits} pay-as-you-go credit{b.credits === 1 ? '' : 's'}</div>
      {b.current_period_end && <div className="kv">Renews: {new Date(b.current_period_end).toLocaleDateString()}</div>}
      {!isAdmin && <div className="kv" style={{ marginTop: 10 }}>Billing is managed by your organisation admin.</div>}

      <div style={{ overflowX: 'auto', marginTop: 18 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 640, fontSize: 13.5 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '10px 12px', borderBottom: '1px solid var(--line)' }}></th>
              {PLANS.map((p) => (
                <th key={p.id} style={{ textAlign: 'left', padding: '10px 12px', borderBottom: '1px solid var(--line)', background: current === p.id ? 'rgba(108,92,231,.06)' : 'transparent', borderTopLeftRadius: 10, borderTopRightRadius: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, color: 'var(--text)' }}>{p.name}</span>
                    {p.popular && <span className="badge">Popular</span>}
                    {current === p.id && <span className="badge pub">Current</span>}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', margin: '2px 0' }}>{p.price}</div>
                  <div style={{ color: 'var(--muted)', fontWeight: 400, fontSize: 12, lineHeight: 1.4 }}>{p.blurb}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row, ri) => (
              <tr key={ri}>
                <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--line-soft, #eef0f6)', color: 'var(--text)', fontWeight: 500 }}>{row.label}</td>
                {PLANS.map((p) => (
                  <td key={p.id} style={{ padding: '9px 12px', borderBottom: '1px solid var(--line-soft, #eef0f6)', background: current === p.id ? 'rgba(108,92,231,.06)' : 'transparent' }}>{cell(row.vals[p.id])}</td>
                ))}
              </tr>
            ))}
            {isAdmin && (
              <tr>
                <td style={{ padding: '14px 12px' }}></td>
                {PLANS.map((p) => (
                  <td key={p.id} style={{ padding: '14px 12px', background: current === p.id ? 'rgba(108,92,231,.06)' : 'transparent', borderBottomLeftRadius: 10, borderBottomRightRadius: 10 }}>{planAction(p)}</td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="muted" style={{ fontSize: 12.5, marginTop: 10 }}>
        <b>Enterprise</b> {'\u2014'} 100+ seats, custom terms, SSO and onboarding support. Contact us for a quote.
      </p>

      {isAdmin && (
        <>
          <div className="row" style={{ marginTop: 8 }}>
            <button className="ghost" onClick={() => go('/billing/credits/checkout', { quantity: 10 }, 'c')} disabled={!!busy}>Buy 10 credits</button>
            <button className="ghost" onClick={() => go('/billing/portal', {}, 'p')} disabled={!!busy}>Manage subscription</button>
          </div>
          {!b.configured && <div className="msg" style={{ marginTop: 8 }}>Billing isn{'\u2019'}t fully configured yet.</div>}
          {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
        </>
      )}
    </div>
  );
}
