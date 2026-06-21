'use client';
import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { supabase } from '../../../lib/supabaseClient';
import { api } from '../../../lib/api';

export default function InvitePage() {
  const { token } = useParams();
  const router = useRouter();
  const [session, setSession] = useState(undefined);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session || null);
      if (data.session) {
        api(`/invite/${token}`).then(setInfo).catch((e) => setError(e.message));
      }
    });
  }, [token]);

  async function accept() {
    setBusy(true); setError('');
    try { await api(`/invite/${token}/accept`, { method: 'POST' }); router.push('/dashboard'); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  if (session === undefined) return <div className="wrap"><p className="muted">Loading…</p></div>;

  if (!session) return (
    <div className="wrap">
      <h1>You’ve been invited</h1>
      <div className="card">
        <p className="muted">Please sign in (or create an account) with the email this invite was sent to, then reopen this link to accept.</p>
        <button onClick={() => router.push('/signin')}>Go to sign in</button>
      </div>
    </div>
  );

  if (error) return (
    <div className="wrap"><h1>Invite unavailable</h1><p className="msg err">{error}</p></div>
  );
  if (!info) return <div className="wrap"><p className="muted">Loading invite…</p></div>;

  if (info.already_accepted) return (
    <div className="wrap"><h1>Invite already accepted</h1>
      <p className="muted">You’re a member of {info.org_name}.</p>
      <button onClick={() => router.push('/dashboard')}>Go to dashboard</button></div>
  );

  return (
    <div className="wrap">
      <h1>Join {info.org_name}</h1>
      <div className="card">
        <div className="kv">Role: {(info.role || '').replace('_', ' ')}</div>
        <div className="kv">Invited address: {info.invited_email}</div>
        {info.expired && <div className="msg err">This invite has expired — ask your admin to resend it.</div>}
        {!info.email_matches && !info.expired && (
          <div className="msg err">You’re signed in as a different email. Sign in with {info.invited_email} to accept.</div>
        )}
        {info.email_matches && !info.expired && (
          <button onClick={accept} disabled={busy}>Accept &amp; join {info.org_name}</button>
        )}
        {error && <div className="msg err">{error}</div>}
      </div>
    </div>
  );
}
