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
            <span className="mk-eyebrow">● Verified references, held in trust</span>
            <h1>The reference layer for UK regulated work.</h1>
            <p className="mk-lede">
              Reffolio gives workers a verified, tamper-evident reference they hold and share with consent —
              so councils and agencies can trust what they receive, instantly. AI-assisted drafting, human integrity.
            </p>
            <div className="mk-hero-actions">
              <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Get started free</Link>
              <Link href="/#how" className="mk-btn mk-btn-ghost mk-btn-lg">See how it works</Link>
            </div>
            <p className="mk-hero-note">No card to start · Workers free, always · Built for social work, health &amp; education.</p>
          </div>

          <div className="mk-card-visual">
            <div className="mk-chip mk-chip-1"><span className="ic" /> SWE register checked</div>
            <div className="mk-refcard">
              <div className="mk-refcard-top">
                <div className="mk-refcard-org"><span className="dot" /> Barchester Council</div>
                <span className="mk-verified">✓ Verified</span>
              </div>
              <div className="mk-refcard-body">
                <div className="mk-line w90" /><div className="mk-line w80" /><div className="mk-line w70" /><div className="mk-line w50" />
              </div>
              <div className="mk-refcard-foot">
                <span className="mk-hash">sha256 · 4f9a…e21c</span>
                <span className="mk-verified" style={{ background: 'rgba(108,92,231,.1)', color: 'var(--violet)' }}>Referee confirmed</span>
              </div>
            </div>
            <div className="mk-chip mk-chip-2"><span className="ic" /> Shared with consent</div>
          </div>
        </div>
      </header>

      <div className="mk-container">
        <div className="mk-trust">
          <span>Local authorities</span><span>·</span><span>Recruitment agencies</span><span>·</span>
          <span>NHS trusts</span><span>·</span><span>Schools &amp; MATs</span><span>·</span><span>Care providers</span>
        </div>
      </div>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">What it is</div>
            <h2>Three guarantees on every reference</h2>
            <p>A reference is only useful if you can trust where it came from, that it hasn&rsquo;t changed, and that it was shared willingly. Reffolio guarantees all three.</p>
          </div>
          <div className="mk-grid">
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z"/><path d="M9 12l2 2 4-4"/></svg></div>
              <h3>Verified at source</h3>
              <p>Worker identity and professional registration (e.g. Social Work England) are checked before a reference is issued — so you know who you&rsquo;re reading about.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg></div>
              <h3>Tamper-evident</h3>
              <p>Every published reference is sealed with a cryptographic hash. Any change is detectable, giving you a record you can stand behind in audits and hearings.</p>
            </div>
            <div className="mk-feature">
              <div className="mk-ic"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 11l-3 3-2-2"/></svg></div>
              <h3>Shared with consent</h3>
              <p>The worker holds their reference and shares it by secure link. No back-channels, no chasing — just a verified record passed on willingly.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section alt" id="how">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">How it works</div>
            <h2>From request to verified, in four steps</h2>
            <p>Reffolio fits the way regulated hiring already works — it just removes the doubt.</p>
          </div>
          <div className="mk-steps">
            <div className="mk-step"><div className="mk-num">1</div><h3>Verify the worker</h3><p>The worker confirms their identity and registration. Reffolio checks it against the relevant register.</p></div>
            <div className="mk-step"><div className="mk-num">2</div><h3>Draft with AI</h3><p>The issuing organisation drafts a structured reference, with AI mapping it to professional standards and flagging gaps.</p></div>
            <div className="mk-step"><div className="mk-num">3</div><h3>Seal &amp; confirm</h3><p>On publish, the reference is hashed and the named referee confirms authorship — locking in integrity.</p></div>
            <div className="mk-step"><div className="mk-num">4</div><h3>Share with consent</h3><p>The worker shares a secure link with their next employer, who sees a verified, unaltered record.</p></div>
          </div>
        </div>
      </section>

      <section className="mk-section" id="why">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">Why Reffolio</div>
            <h2>Built for everyone in the chain</h2>
            <p>One verified record, three sides of value.</p>
          </div>
          <div className="mk-split">
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Councils &amp; employers</h3>
              <ul>
                <li>Trust references on sight — no phone-tag or forged PDFs</li>
                <li>Full audit trail and tamper-evident records for hearings</li>
                <li>Oversight of your whole team&rsquo;s reference activity</li>
                <li>Faster, safer onboarding of regulated staff</li>
              </ul>
            </div>
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Recruitment agencies</h3>
              <ul>
                <li>Place candidates faster with references that pre-clear</li>
                <li>Centralised billing, seats for every consultant</li>
                <li>Reusable, portable credentials reduce re-checks</li>
                <li>Compliance you can demonstrate to clients</li>
              </ul>
            </div>
            <div className="mk-aud">
              <h3><span style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--grad)', display: 'inline-block' }} /> Workers</h3>
              <ul>
                <li>Own your references — carry them between roles</li>
                <li>Free, forever — you never pay to hold or share</li>
                <li>Share only with consent, only with who you choose</li>
                <li>A verified reputation that travels with you</li>
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
              <h2>Intelligent drafting. Human accountability.</h2>
              <p>Reffolio uses AI to do the heavy lifting on language and structure — never to invent facts. Every reference stays authored and confirmed by real people, then sealed so it can&rsquo;t be quietly changed.</p>
            </div>
            <div className="mk-ai-list">
              <div className="mk-ai-item"><b>Standards mapping</b><span>Drafts mapped to professional frameworks (PCF/KSS, KCSIE and more).</span></div>
              <div className="mk-ai-item"><b>Risk &amp; fairness checks</b><span>Surfaces gaps, ambiguity and bias before a reference goes out.</span></div>
              <div className="mk-ai-item"><b>Structured summaries</b><span>Clear, comparable references — not free-text guesswork.</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className="mk-section">
        <div className="mk-container">
          <div className="mk-section-head">
            <div className="mk-kicker">Pricing</div>
            <h2>Simple, per-seat plans</h2>
            <p>Workers are always free. Organisations pay per seat, with room to grow — from a single team to a national agency.</p>
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
