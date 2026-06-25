function OrgSetupPanel({ me }) {
  const [p, setP] = useState(null);
  const [orgType, setOrgType] = useState('');
  const [cqc, setCqc] = useState('');
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false);

  const TYPES = [
    ['care_provider', 'Care provider', 'Domiciliary or residential care \u2014 CQC care reference'],
    ['nhs_trust', 'NHS / Healthcare', 'NHS trust or healthcare \u2014 NMC & HCPC reference'],
    ['school', 'School', 'A single school \u2014 KCSIE safer-recruitment reference'],
    ['mat', 'Academy trust (MAT)', 'Multi-academy trust \u2014 teaching references'],
    ['local_authority', 'Council / Local authority', 'All reference types'],
    ['agency', 'Employment agency', 'Placing across sectors \u2014 all reference types'],
  ];

  const load = useCallback(async () => {
    try {
      const d = await api('/org/profile');
      setP(d);
      setOrgType(d.org_type || '');
      setCqc(d.cqc_provider_id || '');
      setContactName(d.contact_name || '');
      setContactPhone(d.contact_phone || '');
      setContactEmail(d.contact_email || '');
    } catch (e) { setErr(true); setMsg(e.message); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function save() {
    setBusy(true); setMsg(''); setErr(false);
    try {
      await api('/org/profile', { method: 'POST', body: {
        org_type: orgType || null, cqc_provider_id: cqc || null,
        contact_name: contactName || null, contact_phone: contactPhone || null,
        contact_email: contactEmail || null,
      } });
      setMsg('Saved.'); setErr(false); load();
    } catch (e) { setErr(true); setMsg(e.message); } finally { setBusy(false); }
  }

  if (!p) return <div className="card"><p className="muted">Loading{'\u2026'}</p></div>;
  const isAdmin = me.role === 'org_admin';
  if (!isAdmin) return <div className="card"><h2>Organisation</h2><p className="kv">Your organisation type is managed by your admin.</p></div>;

  return (
    <div className="card">
      <h2>Organisation setup</h2>
      <p className="muted">Tell us what kind of organisation you are. This decides which reference forms you{'\u2019'}ll use, so you only see what{'\u2019'}s relevant to you.</p>

      <label>Organisation type</label>
      <div style={{ display: 'grid', gap: 8, marginTop: 6 }}>
        {TYPES.map(([val, title, desc]) => (
          <button key={val} type="button" onClick={() => setOrgType(val)}
            style={{ textAlign: 'left', marginTop: 0, padding: '12px 14px', borderRadius: 10,
              border: orgType === val ? '2px solid var(--violet, #6C5CE7)' : '1px solid var(--line, #e7e9f2)',
              background: orgType === val ? 'rgba(108,92,231,.06)' : 'transparent', cursor: 'pointer' }}>
            <div style={{ fontWeight: 700, color: 'var(--text)' }}>{title}</div>
            <div className="kv" style={{ marginTop: 2 }}>{desc}</div>
          </button>
        ))}
      </div>

      <div style={{ height: 1, background: 'var(--line, #e7e9f2)', margin: '18px 0' }} />
      <p className="muted">These details appear on the reference requests you send, so referees know who you are.</p>
      <label>Your CQC / registration number (optional)</label>
      <input value={cqc} onChange={(e) => setCqc(e.target.value)} placeholder="e.g. 1-XXXXXXXXX" />
      <label>Contact name</label>
      <input value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder="e.g. Tendai Mugodi, Registered Manager" />
      <label>Contact phone</label>
      <input value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} placeholder="e.g. 0113 805 1632" />
      <label>Contact email</label>
      <input value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} placeholder="e.g. info@yourorg.co.uk" />

      <button onClick={save} disabled={busy || !orgType} style={{ marginTop: 14 }}>{busy ? 'Saving…' : 'Save organisation setup'}</button>
      {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
    </div>
  );
}
