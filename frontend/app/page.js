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
            <span className="mk-eyebrow">● Verified references for safer recruitment</span>
            <h1>References your CQC inspector will trust.</h1>
            <p className="mk-lede">
              Reffolio lets regulated employers request employment references, collect them on a
              secure sector-specific form, and store them as verified, tamper-evident records —
              with a full audit trail and the candidate&rsquo;s consent. Inspection-ready, every time.
            </p>
            <div className="mk-hero-actions">
              <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Get started free</Link>
              <Link href="/#how" className="mk-btn mk-btn-ghost mk-btn-lg">See how it works</Link>
            </div>
            <p className="mk-hero-note">No card to start · Built for care, health, education &amp; social work · UK data protection.</p>
          </div>

          <div className="mk-card-visual">
            <div className="mk-chip mk-chip-1"><span className="ic" /> CQC-ready form</div>
            <div className="mk-refcard">
              <div className="mk-refcard-top">
                <div className="mk-refcard-org"><span className="dot" /> Barchester Council</div>
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
              <p>Every completed reference is sealed with a cryptographic hash and a permanent reference number. Any change is detectable — a record you can stand behind in an inspection.</p>
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
            <div className="mk-step"><div className="mk-num">2</div><h3>They complete the form</h3><p>The previous employer fills in a sector-specific form (CQC care, KCSIE, NMC/HCPC and more) on the link — no account needed.</p></div>
            <div className="mk-step"><div className="mk-num">3</div><h3>The candidate consents</h3><p>Before release, the candidate approves sharing the reference with you — recorded with a timestamp in the audit trail.</p></div>
            <div className="mk-step"><div className="mk-num">4</div><h3>You receive the record</h3><p>The reference lands in your account: verified, hashed, with a reference number and downloadable PDF — ready for inspection.</p></div>
          </div>
        </div>
      </section>

      <section className="mk-section" id="why">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">Why Reffolio</div>
            <h2>Built for regulated hiring</h2>
            <p>One verified record, the way your sector needs it.</p>
          </div>
          <div className="mk-split">
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Care &amp; health providers</h3>
              <ul>
                <li>References on a real CQC / NMC / HCPC-shaped form</li>
                <li>Safeguarding question answered on every reference</li>
                <li>Tamper-evident, audit-trailed records for inspection</li>
                <li>Your logo and colours on every request you send</li>
              </ul>
            </div>
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Councils &amp; schools</h3>
              <ul>
                <li>KCSIE safer-recruitment and statutory forms built in</li>
                <li>Per-member access — staff see only their own requests</li>
                <li>Admin oversight of the whole organisation&rsquo;s records</li>
                <li>Records that survive a manager moving on</li>
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
              <p>Reffolio uses AI to draft the covering email that goes to each referee — in your organisation&rsquo;s voice, with your CQC registration and contact details. The reference itself is always completed and declared by a real person, then sealed so it can&rsquo;t be quietly changed.</p>
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
            <p>Organisations pay per seat, with room to grow — from a single care home to a national agency.</p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Link href="/pricing" className="mk-btn mk-btn-primary mk-btn-lg">View plans &amp; pricing</Link>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-cta">
            <h2>Ready to trust every reference?</h2>
            <p>Start free today. Set up your organisation in minutes.</p>
            <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Get started</Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
