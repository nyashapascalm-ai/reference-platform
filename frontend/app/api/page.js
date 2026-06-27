'use client';
import Link from 'next/link';
import '../marketing.css';
import MarketingNav from '../../components/MarketingNav';
import MarketingFooter from '../../components/MarketingFooter';

export default function ApiMarketing() {
  return (
    <div className="mk">
      <MarketingNav />

      <section className="mk-pagehero">
        <div className="mk-container">
          <div className="mk-kicker" style={{ color: 'var(--violet)', fontWeight: 700, letterSpacing: '.08em' }}>API</div>
          <h1 style={{ marginTop: 12 }}>Build verified references into your own system.</h1>
          <p>The Reffolio API lets your product or internal tools request employment references, track them to consent, and pull back a verified, tamper-evident record — while Reffolio handles the referee emails, the candidate consent, and the sector-specific forms. Available on the Growth and Business plans.</p>
          <div className="mk-hero-actions" style={{ marginTop: 20 }}>
            <Link href="/developers" className="mk-btn mk-btn-primary mk-btn-lg">Read the API docs</Link>
            <Link href="/contact" className="mk-btn mk-btn-ghost mk-btn-lg">Talk to us about integration</Link>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">Who it's for</div>
            <h2>Two ways teams build on Reffolio</h2>
          </div>
          <div className="mk-split">
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Software vendors</h3>
              <p style={{ marginBottom: 12 }}>Embed compliant reference-checking inside your ATS, HR or recruitment product — without building the verification, consent and tamper-evidence layer yourself.</p>
              <ul>
                <li>Offer references as a feature your customers already trust</li>
                <li>White-label the candidate and referee experience</li>
                <li>One integration covers care, healthcare, education and social work</li>
              </ul>
            </div>
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> In-house teams</h3>
              <p style={{ marginBottom: 12 }}>Connect Reffolio to the systems your agency, trust or authority already runs on — so references flow without anyone re-keying data.</p>
              <ul>
                <li>Trigger references straight from your own workflow</li>
                <li>No double-entry, no copy-paste between systems</li>
                <li>Pull verified records into your compliance store automatically</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section alt">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">Capabilities</div>
            <h2>What the API enables</h2>
            <p>Everything the dashboard does, available to your code.</p>
          </div>
          <div className="mk-grid">
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg></div>
              <h3>Request from your system</h3>
              <p>Create a reference request with one call. Reffolio emails the previous employer a branded, secure link automatically.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 11l-3 3-2-2"/></svg></div>
              <h3>Consent handled for you</h3>
              <p>The candidate is asked to consent before release — recorded with a timestamp. You never have to build the consent flow.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z"/></svg></div>
              <h3>Real-time webhooks</h3>
              <p>Get a signed POST the moment a referee completes, consent is granted, or a reference is received. Polling is always available as a fallback.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg></div>
              <h3>Verified, tamper-evident records</h3>
              <p>Every reference comes back with a cryptographic hash and a permanent reference number — an inspection-ready record you can store.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z"/></svg></div>
              <h3>Secure &amp; org-scoped</h3>
              <p>Bearer-token keys scoped to one organisation, signed webhook deliveries, and access only ever to your own data.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M4 7h16M4 12h16M4 17h10"/></svg></div>
              <h3>Sector-aware forms</h3>
              <p>Care, healthcare, education and social work each have the right safeguarding questions — the API picks the correct form for you.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">How it fits</div>
            <h2>Your system calls us. We handle the humans. You get the record.</h2>
          </div>
          <div className="mk-steps">
            <div className="mk-step"><div className="mk-num">1</div><h3>You request</h3><p><code>POST /v1/requests</code> from your system with the candidate and previous employer.</p></div>
            <div className="mk-step"><div className="mk-num">2</div><h3>We collect</h3><p>Reffolio emails the referee, they complete the sector form, the candidate consents — all handled for you.</p></div>
            <div className="mk-step"><div className="mk-num">3</div><h3>We notify</h3><p>A signed webhook fires at each step, or you poll <code>GET /v1/requests/{'{id}'}</code> for status.</p></div>
            <div className="mk-step"><div className="mk-num">4</div><h3>You receive</h3><p><code>GET /v1/references/{'{id}'}</code> returns the verified record, ready to store in your system.</p></div>
          </div>
        </div>
      </section>

      <section className="mk-section alt">
        <div className="mk-container">
          <div className="mk-ai">
            <div>
              <div className="mk-kicker" style={{ color: 'var(--cyan)' }}>Why not build it yourself</div>
              <h2>The hard parts are already done.</h2>
              <p>Reference-checking looks simple until you build it. Verifying that a referee is really the previous employer, capturing lawful candidate consent, sealing each record so it can&rsquo;t be quietly changed, and shaping forms to CQC, NMC, HCPC, KCSIE and Social Work England — that&rsquo;s the work. Reffolio has done it, so your team can ship an integration in days, not quarters.</p>
            </div>
            <div className="mk-ai-list">
              <div className="mk-ai-item"><b>Referee verification</b><span>Work-email checks and free-mail flagging on every request.</span></div>
              <div className="mk-ai-item"><b>Consent &amp; audit trail</b><span>Lawful basis recorded, every event timestamped.</span></div>
              <div className="mk-ai-item"><b>Tamper-evidence</b><span>Cryptographic hashing and permanent reference numbers.</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-cta">
            <h2>Start building</h2>
            <p>Generate a key in the dashboard and read the docs, or talk to us about a deeper integration.</p>
            <div className="mk-hero-actions" style={{ justifyContent: 'center' }}>
              <Link href="/developers" className="mk-btn mk-btn-primary mk-btn-lg">Read the API docs</Link>
              <Link href="/contact" className="mk-btn mk-btn-ghost mk-btn-lg">Talk to us</Link>
            </div>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
