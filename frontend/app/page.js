'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../lib/supabaseClient';

export default function Home() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('org'); // chosen at sign-up
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
    if (error) { setErr(true); setMsg(error.message); return; }
    // try to sign in straight away (works when email confirmation is off)
    const { error: e2 } = await supabase.auth.signInWithPassword({ email, password });
    if (e2) { setMsg('Account created. Confirm via the email we sent, then sign in.'); }
    else { router.push(`/dashboard?setup=${role}`); }
  }
  async function signIn() {
    setBusy(true); setMsg(''); setErr(false);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setBusy(false);
    if (error) { setErr(true); setMsg(error.message); }
    else router.push('/dashboard');
  }

  const roleBtn = (val, label) => (
    <button
      type="button"
      onClick={() => setRole(val)}
      className={role === val ? '' : 'ghost'}
      style={{ flex: 1, marginTop: 0 }}
    >{label}</button>
  );

  return (
    <div className="center">
      <div className="brand">Reffolio</div>
      <p className="muted" style={{ marginTop: 6 }}>References held in trust — verified, tamper-evident, shared only with consent.</p>
      <div className="card" style={{ marginTop: 24 }}>
        <label>I'm joining as</label>
        <div className="row" style={{ gap: 8 }}>
          {roleBtn('org', 'An organisation')}
          {roleBtn('worker', 'A worker')}
        </div>
        <div className="kv" style={{ marginTop: 6 }}>
          {role === 'org'
            ? 'You issue and manage references (councils, agencies, employers).'
            : 'You collect and share references about yourself.'}
        </div>
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        <div className="row">
          <button onClick={signUp} disabled={busy}>Create account</button>
          <button className="ghost" onClick={signIn} disabled={busy}>Sign in</button>
        </div>
        {msg && <div className={'msg' + (err ? ' err' : '')}>{msg}</div>}
      </div>
    </div>
  );
}
