'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../lib/supabaseClient';

export default function Home() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.push('/dashboard');
    });
  }, [router]);

  async function signUp() {
    setBusy(true); setMsg(''); setErr(false);
    const { error } = await supabase.auth.signUp({ email, password });
    setBusy(false);
    if (error) { setErr(true); setMsg(error.message); }
    else setMsg('Account created. If email confirmation is enabled, confirm via the email; otherwise sign in below.');
  }
  async function signIn() {
    setBusy(true); setMsg(''); setErr(false);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setBusy(false);
    if (error) { setErr(true); setMsg(error.message); }
    else router.push('/dashboard');
  }

  return (
    <div className="center">
      <h1>Reference Custody</h1>
      <p className="muted">Verified, consent-shared employment references.</p>
      <div className="card" style={{ marginTop: 24 }}>
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        <div className="row">
          <button onClick={signIn} disabled={busy}>Sign in</button>
          <button className="ghost" onClick={signUp} disabled={busy}>Create account</button>
        </div>
        {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
      </div>
    </div>
  );
}
