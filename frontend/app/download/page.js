'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import '../marketing.css';
import MarketingNav from '../../components/MarketingNav';
import MarketingFooter from '../../components/MarketingFooter';

const WIN_URL = 'https://github.com/nyashapascalm-ai/reffolio-desktop/releases/download/v1.0.2/Reffolio_1.0.1_x64-setup.exe';
const MAC_URL = 'https://github.com/nyashapascalm-ai/reffolio-desktop/releases/download/v1.0.2/Reffolio_1.0.1_universal.dmg';
const RELEASES_URL = 'https://github.com/nyashapascalm-ai/reffolio-desktop/releases';

export default function Download() {
  const [os, setOs] = useState(null); // 'win' | 'mac' | null

  useEffect(() => {
    const ua = (navigator.userAgent || '').toLowerCase();
    if (ua.includes('win')) setOs('win');
    else if (ua.includes('mac')) setOs('mac');
  }, []);

  return (
    <div className="mk">
      <MarketingNav />

      <section className="mk-pagehero">
        <div className="mk-container">
          <div className="mk-kicker" style={{ color: 'var(--violet)', fontWeight: 700, letterSpacing: '.08em' }}>DOWNLOAD</div>
          <h1 style={{ marginTop: 12 }}>Reffolio on your desktop</h1>
          <p>The desktop app gives your team quick access to Reffolio in its own window. It always reflects the latest version &mdash; nothing to update.</p>
        </div>
      </section>

      <section className="mk-section" style={{ paddingTop: 16 }}>
        <div className="mk-container">
          <div className="mk-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)', maxWidth: 760, margin: '0 auto' }}>

            <div className="mk-feature" style={{ textAlign: 'center', border: os === 'win' ? '2px solid var(--violet)' : undefined }}>
              <div className="mk-ic" style={{ margin: '0 auto 16px' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="#fff"><path d="M3 5.5L10.5 4.4v7.1H3V5.5zM3 12.5h7.5v7.1L3 18.5v-6zM11.5 4.2L21 3v8.5h-9.5V4.2zM11.5 12.5H21V21l-9.5-1.3v-7.2z"/></svg>
              </div>
              <h3>Windows</h3>
              <p style={{ marginTop: 8, marginBottom: 20 }}>Windows 10 &amp; 11 &middot; 64-bit</p>
              {os === 'win' && <div style={{ fontSize: 12.5, color: 'var(--violet)', fontWeight: 600, marginBottom: 10 }}>Recommended for your device</div>}
              <a href={WIN_URL} className="mk-btn mk-btn-primary" style={{ width: '100%' }}>Download for Windows</a>
              <p style={{ fontSize: 12, marginTop: 12 }}>.exe installer &middot; ~1.8 MB</p>
            </div>

            <div className="mk-feature" style={{ textAlign: 'center', border: os === 'mac' ? '2px solid var(--violet)' : undefined }}>
              <div className="mk-ic" style={{ margin: '0 auto 16px' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="#fff"><path d="M16.4 12.6c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.1-2.8.9-3.5.9-.7 0-1.8-.8-3-.8-1.5 0-3 .9-3.8 2.3-1.6 2.8-.4 7 1.2 9.3.8 1.1 1.7 2.4 2.9 2.3 1.2-.1 1.6-.8 3-.8 1.4 0 1.8.8 3 .7 1.2 0 2-1.1 2.8-2.2.9-1.3 1.2-2.5 1.3-2.6-.1 0-2.5-.9-2.5-3.7zM14.2 5.8c.6-.8 1.1-1.9 1-3-.9 0-2.1.6-2.8 1.4-.6.7-1.1 1.8-1 2.9 1 .1 2.1-.5 2.8-1.3z"/></svg>
              </div>
              <h3>macOS</h3>
              <p style={{ marginTop: 8, marginBottom: 20 }}>Apple Silicon &amp; Intel &middot; universal</p>
              {os === 'mac' && <div style={{ fontSize: 12.5, color: 'var(--violet)', fontWeight: 600, marginBottom: 10 }}>Recommended for your device</div>}
              <a href={MAC_URL} className="mk-btn mk-btn-primary" style={{ width: '100%' }}>Download for Mac</a>
              <p style={{ fontSize: 12, marginTop: 12 }}>.dmg &middot; ~5.5 MB</p>
            </div>
          </div>

          <div style={{ maxWidth: 760, margin: '28px auto 0' }}>
            <div className="mk-info-card">
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 17, marginBottom: 10 }}>Installing &amp; first launch</h3>
              <p style={{ fontSize: 14, lineHeight: 1.6 }}>
                The app is new, so your computer may show a caution screen the first time.
                On <b>Windows</b>, if you see &ldquo;Windows protected your PC&rdquo;, click <b>More info &rarr; Run anyway</b>.
                On <b>Mac</b>, right-click the app and choose <b>Open</b>, then <b>Open</b> again. You only do this once.
              </p>
              <p style={{ fontSize: 13, marginTop: 14 }}>
                Prefer to browse all versions and checksums? <a href={RELEASES_URL} target="_blank" rel="noopener noreferrer">View all releases on GitHub</a>.
              </p>
            </div>
          </div>

          <div style={{ textAlign: 'center', marginTop: 32 }}>
            <p style={{ fontSize: 14 }}>No download needed &mdash; you can always use Reffolio in your browser.</p>
            <Link href="/signin" className="mk-btn mk-btn-ghost" style={{ marginTop: 12 }}>Open Reffolio in browser</Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
