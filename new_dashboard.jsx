export default function Dashboard() {
  const router = useRouter();
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [setupRole, setSetupRole] = useState(null);
  const [view, setView] = useState('home');

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
      if (!data.session) { router.push('/signin'); return; }
      loadMe();
    });
  }, [router, loadMe]);

  async function signOut() { await supabase.auth.signOut(); router.push('/'); }

  if (loading) return <div className="wrap"><p className="muted">Loading...</p></div>;

  // Not yet set up (and not staff): keep the simple onboarding screen, no shell.
  if (!me?.org_id && !me?.worker_id && !me?.is_super_admin) {
    return (
      <div className="wrap">
        <div className="topbar"><div><h1>Welcome to Reffolio</h1></div><button className="ghost" onClick={signOut}>Sign out</button></div>
        {error && <div className="msg err">{error}</div>}
        <Onboarding onDone={loadMe} role={setupRole} setRole={setSetupRole} />
      </div>
    );
  }

  const isAdmin = me?.org_id && me.role === 'org_admin';
  const isMember = me?.org_id && me.role !== 'org_admin';
  const isWorker = me?.worker_id && !me?.org_id;
  const isStaff = me?.is_super_admin && !me?.org_id && !me?.worker_id;

  // Build the nav + tiles per role.
  let nav = [];
  let tiles = [];
  if (me?.org_id) {
    nav.push({ id: 'issue', icon: 'ref', label: 'Generate reference' });
    if (isAdmin) {
      nav.push({ id: 'oversight', icon: 'shield', label: 'Oversight' });
      nav.push({ id: 'team', icon: 'team', label: 'Team & invites' });
      nav.push({ id: 'billing', icon: 'billing', label: 'Billing' });
    } else {
      nav.push({ id: 'team', icon: 'team', label: 'Team' });
      nav.push({ id: 'billing', icon: 'billing', label: 'Billing' });
    }
    tiles.push({ id: 'issue', icon: 'ref', title: 'Generate a reference', desc: 'Compose, AI-review and publish a verified reference.' });
    if (isAdmin) {
      tiles.push({ id: 'oversight', icon: 'shield', title: 'Oversight', desc: 'Team activity, records and reference controls.' });
      tiles.push({ id: 'team', icon: 'team', title: 'Team & invites', desc: 'Invite colleagues and manage members.' });
      tiles.push({ id: 'billing', icon: 'billing', title: 'Billing & subscription', desc: 'Plan, seats and payment.' });
    } else {
      tiles.push({ id: 'team', icon: 'team', title: 'Team', desc: 'See your organisation\u2019s members.' });
      tiles.push({ id: 'billing', icon: 'billing', title: 'Billing', desc: 'View plan and seats.' });
    }
  }
  if (me?.worker_id) {
    nav.push({ id: 'myrefs', icon: 'records', label: 'My references' });
    tiles.push({ id: 'myrefs', icon: 'records', title: 'My references', desc: 'Hold, request and share your verified references.' });
  }
  if (isStaff) {
    tiles.push({ id: 'console', icon: 'chart', title: 'Operator console', desc: 'Organisations, analytics, lifecycle and reports.' });
    nav.push({ id: 'console', icon: 'chart', label: 'Operator console' });
  }

  function Body() {
    if (view === 'home') {
      return (
        <>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 30, margin: '0 0 4px' }}>
            {isAdmin ? 'Management console' : isWorker ? 'Your references' : isStaff ? 'Reffolio staff' : 'Dashboard'}
          </h1>
          <p className="muted" style={{ margin: '0 0 22px' }}>Pick an action to get started.</p>
          {error && <div className="msg err">{error}</div>}
          {isStaff && (
            <div className="card" style={{ borderLeft: '3px solid var(--violet, #6C5CE7)', marginBottom: 18 }}>
              <b style={{ color: 'var(--text)' }}>You{'\u2019'}re signed in as Reffolio staff.</b>
              <div className="kv">Open the operator console to manage organisations, billing, analytics and reports.</div>
              <button style={{ marginTop: 10 }} onClick={() => router.push('/admin')}>Open admin console</button>
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
            {tiles.map((t) => (
              <Tile key={t.id} icon={t.icon} title={t.title} desc={t.desc}
                onClick={() => (t.id === 'console' ? router.push('/admin') : setView(t.id))} />
            ))}
          </div>
          {isAdmin && (
            <div style={{ marginTop: 26 }}>
              <div className="kv" style={{ textTransform: 'uppercase', fontSize: 11, letterSpacing: '0.04em', marginBottom: 10 }}>Oversight at a glance</div>
              <AdminOversightPanel me={me} />
            </div>
          )}
        </>
      );
    }
    if (view === 'issue') return <OrgPanel me={me} />;
    if (view === 'oversight') return <AdminOversightPanel me={me} />;
    if (view === 'team') return <TeamPanel me={me} />;
    if (view === 'billing') return <BillingPanel me={me} />;
    if (view === 'myrefs') return <WorkerPanel me={me} />;
    return null;
  }

  return (
    <Shell me={me} signOut={signOut} nav={nav} view={view} setView={setView}>
      {error && view !== 'home' && <div className="msg err">{error}</div>}
      <Body />
    </Shell>
  );
}
