'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../../lib/supabaseClient';

export default function ResetPassword() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [msg, setMsg] = useState(''); const [err, setErr] = useState(false);
  const [busy, setBusy] = useState(false); const [done, setDone] = useState(false);

  useEffect(() => {
    // Supabase parses the recovery token from the URL and creates a temporary session.
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY' || session) setReady(true);
    });
    supabase.auth.getSession().then(({ data }) => { if (data.session) setReady(true); });
    return () => { sub.subscription.unsubscribe(); };
  }, []);

  async function update() {
    if (password.length < 8) { setErr(true); setMsg('Use at least 8 characters.'); return; }
    if (password !== confirm) { setErr(true); setMsg('Passwords don\u2019t match.'); return; }
    setBusy(true); setMsg(''); setErr(false);
    const { error } = await supabase.auth.updateUser({ password });
    setBusy(false);
    if (error) { setErr(true); setMsg(error.message); return; }
    setDone(true);
  }

  if (done) return (
    <div className="center">
      <div className="brand">Reffolio</div>
      <div className="card" style={{ marginTop: 24, maxWidth: 420 }}>
        <h2>Password updated</h2>
        <p className="muted">You{'\u2019'}re all set and signed in.</p>
        <button onClick={() => router.push('/dashboard')}>Continue to dashboard</button>
      </div>
    </div>
  );

  return (
    <div className="center">
      <div className="brand">Reffolio</div>
      <div className="card" style={{ marginTop: 24, maxWidth: 420 }}>
        <h2>Set a new password</h2>
        {!ready && (
          <>
            <p className="muted">Open this page from the reset link in your email. If you arrived another way or the link expired, request a fresh one from sign-in.</p>
            <button className="ghost" onClick={() => router.push('/')}>Back to sign in</button>
          </>
        )}
        {ready && (
          <>
            <label>New password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            <label>Confirm password</label>
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="••••••••" />
            <button onClick={update} disabled={busy}>Update password</button>
          </>
        )}
        {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
      </div>
    </div>
  );
}
