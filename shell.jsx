// ---- Reffolio dashboard shell: sidebar + home tiles -----------------------
function Icon({ name }) {
  const p = {
    home: <path d="M3 11l9-8 9 8M5 9v11h5v-6h4v6h5V9" />,
    ref: <><path d="M7 3h7l5 5v13H7z" /><path d="M14 3v5h5" /><path d="M9.5 13l1.8 1.8L15 11" /></>,
    team: <><circle cx="9" cy="8" r="3.2" /><path d="M3 20a6 6 0 0 1 12 0" /><path d="M17 8a3 3 0 0 1 0 6" /><path d="M21 20a5 5 0 0 0-4-4.9" /></>,
    billing: <><rect x="2.5" y="5" width="19" height="14" rx="2.5" /><path d="M2.5 9.5h19" /></>,
    shield: <><path d="M12 3l8 3v6c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V6z" /><path d="M9 12l2 2 4-4" /></>,
    records: <><path d="M5 4h14v16H5z" /><path d="M8 8h8M8 12h8M8 16h5" /></>,
    request: <><circle cx="12" cy="12" r="9" /><path d="M12 8v5l3 2" /></>,
    share: <><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" /><path d="M8.2 10.8l7.6-3.6M8.2 13.2l7.6 3.6" /></>,
    chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
    user: <><circle cx="12" cy="8" r="3.5" /><path d="M5 20a7 7 0 0 1 14 0" /></>,
  }[name] || null;
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{p}</svg>
  );
}

function Tile({ icon, title, desc, onClick }) {
  return (
    <button onClick={onClick} style={{
      textAlign: 'left', background: '#fff', border: '1px solid var(--line)', borderRadius: 16,
      padding: 20, margin: 0, cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 10,
      boxShadow: 'none', color: 'var(--text)', transition: 'transform .12s ease, box-shadow .2s ease',
    }}
      onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = '0 16px 34px -20px rgba(30,42,90,.4)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}>
      <span style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--grad, #6C5CE7)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={icon} /></span>
      <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17 }}>{title}</span>
      <span style={{ color: 'var(--muted)', fontSize: 13.5, lineHeight: 1.5 }}>{desc}</span>
    </button>
  );
}

function Shell({ me, signOut, nav, view, setView, children }) {
  const NavItem = ({ id, icon, label }) => (
    <button onClick={() => setView(id)} style={{
      display: 'flex', alignItems: 'center', gap: 11, width: '100%', textAlign: 'left',
      background: view === id ? 'rgba(108,92,231,.10)' : 'transparent',
      color: view === id ? 'var(--violet, #6C5CE7)' : 'var(--text)',
      border: 'none', borderRadius: 10, padding: '10px 12px', margin: '2px 0', cursor: 'pointer',
      fontSize: 14, fontWeight: 600, boxShadow: 'none',
    }}>
      <Icon name={icon} /> {label}
    </button>
  );
  const roleLabel = me?.is_super_admin ? 'Reffolio staff'
    : me?.role === 'org_admin' ? 'admin'
    : me?.worker_id && !me?.org_id ? 'worker'
    : (me?.role || '').replace('_', ' ') || 'member';
  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'stretch' }}>
      <aside style={{ width: 248, flexShrink: 0, borderRight: '1px solid var(--line-soft, #e7e9f2)', padding: '20px 14px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '4px 8px 16px', fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 19 }}>
          <img src="/icon.svg" alt="" style={{ width: 26, height: 26, borderRadius: 7 }} /> Reffolio
        </div>
        <NavItem id="home" icon="home" label="Home" />
        {nav.map((n) => <NavItem key={n.id} id={n.id} icon={n.icon} label={n.label} />)}
        <div style={{ marginTop: 'auto', padding: '12px 8px 4px', borderTop: '1px solid var(--line-soft, #e7e9f2)' }}>
          <div style={{ fontSize: 12.5, color: 'var(--muted)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis' }}>{me?.email}</div>
          <div style={{ fontSize: 11.5, color: 'var(--muted)', textTransform: 'capitalize', marginBottom: 8 }}>{roleLabel}</div>
          <button className="ghost" style={{ marginTop: 0, width: '100%' }} onClick={signOut}>Sign out</button>
        </div>
      </aside>
      <main style={{ flex: 1, minWidth: 0, padding: '28px 32px', maxWidth: 1080 }}>
        {view !== 'home' && (
          <button className="ghost" style={{ marginTop: 0, marginBottom: 14 }} onClick={() => setView('home')}>&larr; Home</button>
        )}
        {children}
      </main>
    </div>
  );
}
