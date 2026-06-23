'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { supabase } from '../../lib/supabaseClient';
import '../marketing.css';

export default function AppWelcome() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace('/dashboard');
      else setChecking(false);
    });
  }, [router]);

  if (checking) {
    return (
      <div className="mk" style={wrap}>
        <div style={{ color: 'var(--muted)' }}>Loading Reffolio…</div>
      </div>
    );
  }

  return (
    <div className="mk" style={wrap}>
      <div style={glow} />
      <div style={card}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <img src="/icon.svg" alt="" style={{ width: 64, height: 64, borderRadius: 18, boxShadow: '0 12px 30px -12px rgba(76,92,231,.55)' }} />
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 30, marginTop: 18, letterSpacing: '-0.02em' }}>Reffolio</div>
          <p style={{ marginTop: 10, fontSize: 16, color: 'var(--muted)', textAlign: 'center', maxWidth: 340, lineHeight: 1.5 }}>
            Verified, consent-shared references for UK regulated work.
          </p>
        </div>

        <div style={{ marginTop: 30, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg" style={{ width: '100%' }}>Sign in</Link>
          <Link href="/signin" className="mk-btn mk-btn-ghost mk-btn-lg" style={{ width: '100%' }}>Create an account</Link>
        </div>

        <div style={divider}><span style={dividerText}>Trusted by design</span></div>

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          {['Verified at source', 'Tamper-evident', 'Shared with consent'].map((t) => (
            <div key={t} style={trustItem}>
              <span style={tick}>✓</span>
              <span>{t}</span>
            </div>
          ))}
        </div>
      </div>

      <a href="https://reffolio.co.uk" target="_blank" rel="noopener noreferrer" style={{ marginTop: 22, fontSize: 13.5, color: 'var(--muted)' }}>
        Learn more at reffolio.co.uk
      </a>
    </div>
  );
}

const wrap = {
  position: 'relative', minHeight: '100vh', display: 'flex', flexDirection: 'column',
  alignItems: 'center', justifyContent: 'center', padding: '32px 20px', overflow: 'hidden',
};
const glow = {
  position: 'absolute', top: '-20%', left: '50%', transform: 'translateX(-50%)',
  width: 680, height: 680, borderRadius: '50%',
  background: 'radial-gradient(circle, rgba(108,92,231,.16), rgba(22,200,224,.06) 45%, transparent 70%)',
  pointerEvents: 'none',
};
const card = {
  position: 'relative', width: '100%', maxWidth: 420, background: '#fff',
  border: '1px solid var(--line)', borderRadius: 24, padding: 36,
  boxShadow: '0 30px 70px -30px rgba(30,42,90,.35)',
};
const divider = {
  position: 'relative', textAlign: 'center', margin: '26px 0 18px',
  borderTop: '1px solid var(--line-soft)',
};
const dividerText = {
  position: 'relative', top: -10, background: '#fff', padding: '0 12px',
  fontSize: 12, color: 'var(--muted)', fontWeight: 600, letterSpacing: '.04em', textTransform: 'uppercase',
};
const trustItem = {
  flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
  fontSize: 11.5, color: 'var(--muted)', textAlign: 'center', fontWeight: 500,
};
const tick = {
  width: 22, height: 22, borderRadius: '50%', background: 'rgba(0,184,166,.12)',
  color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center',
  fontSize: 12, fontWeight: 700,
};
