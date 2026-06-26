function GetAppPanel() {
  const WIN_URL = 'https://github.com/nyashapascalm-ai/reffolio-desktop/releases/download/v1.0.2/Reffolio_1.0.2_x64-setup.exe';
  const MAC_URL = 'https://github.com/nyashapascalm-ai/reffolio-desktop/releases/download/v1.0.2/Reffolio_1.0.2_universal.dmg';

  const [os, setOs] = useState('other');
  useEffect(() => {
    try {
      const p = (navigator.userAgent + ' ' + (navigator.platform || '')).toLowerCase();
      if (p.includes('win')) setOs('win');
      else if (p.includes('mac') || p.includes('darwin')) setOs('mac');
    } catch (e) {}
  }, []);

  const Card = ({ id, title, sub, url, filename }) => {
    const primary = os === id;
    return (
      <div style={{
        flex: '1 1 240px', border: primary ? '2px solid var(--violet, #6C5CE7)' : '1px solid var(--line, #e7e9f2)',
        borderRadius: 14, padding: 20, background: primary ? 'rgba(108,92,231,.05)' : 'transparent',
      }}>
        <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text)' }}>{title}</div>
        <div className="kv" style={{ marginTop: 2 }}>{sub}</div>
        {primary && <div className="kv" style={{ color: 'var(--violet, #6C5CE7)', marginTop: 6 }}>Recommended for your device</div>}
        <a href={url} download style={{ display: 'inline-block', marginTop: 14, background: 'var(--violet, #6C5CE7)',
          color: '#fff', textDecoration: 'none', padding: '10px 18px', borderRadius: 9, fontWeight: 600 }}>
          Download
        </a>
        <div className="kv" style={{ marginTop: 8, fontSize: 11, wordBreak: 'break-all' }}>{filename}</div>
      </div>
    );
  };

  return (
    <div className="card">
      <h2>Get the Reffolio desktop app</h2>
      <p className="muted">Install Reffolio on your computer for quick access. The desktop app opens in its own window and keeps you signed in.</p>

      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 16 }}>
        <Card id="win" title="Windows" sub="Windows 10 / 11 \u00b7 64-bit installer"
          url={WIN_URL} filename="Reffolio_1.0.2_x64-setup.exe" />
        <Card id="mac" title="macOS" sub="Universal \u00b7 Apple Silicon & Intel"
          url={MAC_URL} filename="Reffolio_1.0.2_universal.dmg" />
      </div>

      <div style={{ marginTop: 18 }}>
        <p className="muted" style={{ fontSize: 13 }}>
          After downloading: on Windows, run the setup file and follow the prompts.
          On macOS, open the .dmg and drag Reffolio to Applications. You may need to allow
          the app in System Settings the first time you open it.
        </p>
        <p className="kv" style={{ marginTop: 6 }}>Current version: 1.0.2</p>
      </div>
    </div>
  );
}
