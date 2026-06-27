'use client';
import Link from 'next/link';
import './marketing.css';
import MarketingNav from '../components/MarketingNav';
import MarketingFooter from '../components/MarketingFooter';

export default function Landing() {
  return (
    <div className="mk">
      <MarketingNav />

      <header className="mk-hero">
        <div className="mk-container mk-hero-grid">
          <div>
            <span className="mk-eyebrow">● Verified references for regulated hiring</span>
            <h1>Verified references for regulated hiring.</h1>
            <p className="mk-lede">
              Request, collect and store employment references as verified, tamper-evident,
              consent-based records on forms aligned with CQC, NMC, HCPC, KCSIE —
              and Social Work England. Inspection-ready, every time.
            </p>
            <div className="mk-hero-actions">
              <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Start 14-day trial</Link>
              <Link href="/#how" className="mk-btn mk-btn-ghost mk-btn-lg">See how it works</Link>
            </div>
            <p className="mk-hero-note">No card to start · Built for care, healthcare, education &amp; social work · UK data protection.</p>
          </div>

          <div className="mk-card-visual">
            <div className="mk-chip mk-chip-1"><span className="ic" /> Sector-specific form</div>
            <div className="mk-refcard">
              <div className="mk-refcard-top">
                <div className="mk-refcard-org"><span className="dot" /> Verified employer</div>
                <span className="mk-verified">✓ Received</span>
              </div>
              <div className="mk-refcard-body">
                <div className="mk-line w90" /><div className="mk-line w80" /><div className="mk-line w70" /><div className="mk-line w50" />
              </div>
              <div className="mk-refcard-foot">
                <span className="mk-hash">sha256 · 4f9a…e21c</span>
                <span className="mk-verified" style={{ background: 'rgba(108,92,231,.1)', color: 'var(--violet)' }}>Consent granted</span>
              </div>
            </div>
            <div className="mk-chip mk-chip-2"><span className="ic" /> Full audit trail</div>
          </div>
        </div>
      </header>

      <div className="mk-container">
        <div className="mk-trust">
          <span>Care providers</span><span>·</span><span>NHS trusts</span><span>·</span>
          <span>Schools &amp; MATs</span><span>·</span><span>Local authorities</span><span>·</span><span>Recruitment agencies</span>
        </div>
      </div>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">What it is</div>
            <h2>Three things on every reference you receive</h2>
            <p>A reference is only useful if you know where it came from, that it hasn&rsquo;t changed, and that it was shared with consent. Reffolio gives you all three on every record.</p>
          </div>
          <div className="mk-grid">
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z"/><path d="M9 12l2 2 4-4"/></svg></div>
              <h3>Verified referee</h3>
              <p>The previous employer completes the reference from their work email on a secure link. Free-mail addresses are flagged, so you can see who you&rsquo;re reading.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg></div>
              <h3>Tamper-evident</h3>
              <p>Every completed reference is sealed with a cryptographic hash and a permanent reference number. Any change is detectable — a record you can stand behind in an audit or inspection.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 11l-3 3-2-2"/></svg></div>
              <h3>Released with consent</h3>
              <p>The candidate is asked to consent before the reference is released to you — a clear, recorded basis for processing, held under UK data protection.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section alt" id="how">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">How it works</div>
            <h2>From request to inspection-ready, in four steps</h2>
            <p>Reffolio fits the way safer recruitment already works — it just removes the chasing and the doubt.</p>
          </div>
          <div className="mk-steps">
            <div className="mk-step"><div className="mk-num">1</div><h3>Request a reference</h3><p>Enter the candidate and their previous employer. Reffolio emails the referee a secure link with your logo and an AI-drafted covering note.</p></div>
            <div className="mk-step"><div className="mk-num">2</div><h3>They complete the form</h3><p>The previous employer fills in a form built for your sector — care, healthcare, education or social work — on the link, no account needed.</p></div>
            <div className="mk-step"><div className="mk-num">3</div><h3>The candidate consents</h3><p>Before release, the candidate approves sharing the reference with you — recorded with a timestamp in the audit trail.</p></div>
            <div className="mk-step"><div className="mk-num">4</div><h3>You receive the record</h3><p>The reference lands in your account: verified, hashed, with a reference number and downloadable PDF — ready for inspection.</p></div>
          </div>
        </div>
      </section>

      <section className="mk-section" id="why">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">Who it's for</div>
            <h2>One platform, every regulated sector</h2>
            <p>The same verified, consented, audit-trailed record — on the form your sector expects.</p>
          </div>
          <div className="mk-split">
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Care &amp; healthcare</h3>
              <ul>
                <li>Forms shaped for CQC, NMC and HCPC expectations</li>
                <li>Safeguarding question on every reference</li>
                <li>Tamper-evident, audit-trailed records for inspection</li>
                <li>Suitable-to-work-with confirmation built in</li>
              </ul>
            </div>
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Education &amp; social work</h3>
              <ul>
                <li>KCSIE safer-recruitment and Social Work England aligned</li>
                <li>Schools, MATs, local authorities and trusts</li>
                <li>Per-member access — staff see only their own requests</li>
                <li>Admin oversight of the whole organisation&rsquo;s records</li>
              </ul>
            </div>
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Recruitment agencies</h3>
              <ul>
                <li>Request across every sector from one place</li>
                <li>Attach a job description; receive documents back</li>
                <li>Centralised billing, seats for every consultant</li>
                <li>Compliance you can demonstrate to clients</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section alt">
        <div className="mk-container">
          <div className="mk-ai">
            <div>
              <div className="mk-kicker" style={{ color: 'var(--cyan)' }}>AI, with integrity</div>
              <h2>Less admin. Same accountability.</h2>
              <p>Reffolio uses AI to draft the covering email that goes to each referee — in your organisation&rsquo;s voice, with your registration and contact details. The reference itself is always completed and declared by a real person, then sealed so it can&rsquo;t be quietly changed.</p>
            </div>
            <div className="mk-ai-list">
              <div className="mk-ai-item"><b>Sector-specific forms</b><span>Care, healthcare, education and social work — each with the right safeguarding questions.</span></div>
              <div className="mk-ai-item"><b>On-brand requests</b><span>Your logo, colour and signature on every email and the page referees complete.</span></div>
              <div className="mk-ai-item"><b>Inspection-ready records</b><span>Verified, hashed, audit-trailed and downloadable as a PDF.</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">Pricing</div>
            <h2>Simple, per-seat plans</h2>
            <p>Every plan starts with a 14-day free trial. Pay per seat, with room to grow — from a single team to a national agency.</p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Link href="/pricing" className="mk-btn mk-btn-primary mk-btn-lg">View plans &amp; pricing</Link>
          </div>
        </div>
      </section>

      <section className="mk-section alt">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">For developers</div>
            <h2>Connect Reffolio to your stack</h2>
            <p>Request references from your own ATS, HR or recruitment system, get notified by webhook, and pull back verified records &mdash; while Reffolio handles the referee emails, consent and sector forms.</p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Link href="/api" className="mk-btn mk-btn-primary mk-btn-lg">Explore the API</Link>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-cta">
            <h2>Ready to trust every reference?</h2>
            <p>Start your 14-day free trial. Set up your organisation in minutes.</p>
            <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Get started</Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
