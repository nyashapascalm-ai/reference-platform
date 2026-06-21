'use client';
import { useState } from 'react';
import '../marketing.css';
import MarketingNav from '../../components/MarketingNav';
import MarketingFooter from '../../components/MarketingFooter';

export default function Contact() {
  const [f, setF] = useState({ name: '', email: '', org: '', message: '' });

  function send() {
    const subject = encodeURIComponent(`Reffolio enquiry from ${f.name || 'website'}`);
    const body = encodeURIComponent(
      `Name: ${f.name}\nEmail: ${f.email}\nOrganisation: ${f.org}\n\n${f.message}`
    );
    window.location.href = `mailto:support@reffolio.co.uk?subject=${subject}&body=${body}`;
  }

  return (
    <div className="mk">
      <MarketingNav />
      <section className="mk-pagehero">
        <div className="mk-container">
          <div className="mk-kicker" style={{ color: 'var(--violet)', fontWeight: 700, letterSpacing: '.08em' }}>CONTACT</div>
          <h1 style={{ marginTop: 12 }}>Talk to the Reffolio team</h1>
          <p>Questions about verification, procurement, or Enterprise? We&rsquo;re happy to help.</p>
        </div>
      </section>

      <section className="mk-section" style={{ paddingTop: 16 }}>
        <div className="mk-container">
          <div className="mk-contact-grid">
            <div className="mk-info-card">
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 20 }}>Get in touch</h3>
              <p style={{ marginTop: 8 }}>The fastest way to reach us is by email — we aim to reply within one business day.</p>

              <div className="mk-info-row">
                <div className="mk-ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--violet)" strokeWidth="2"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg></div>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text)' }}>Support &amp; sales</div>
                  <a href="mailto:support@reffolio.co.uk">support@reffolio.co.uk</a>
                </div>
              </div>

              <div className="mk-info-row">
                <div className="mk-ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--violet)" strokeWidth="2"><path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z"/></svg></div>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text)' }}>Enterprise &amp; procurement</div>
                  <span style={{ color: 'var(--muted)', fontSize: 14 }}>G-Cloud, SSO, white-labelling — mention &ldquo;Enterprise&rdquo; in your email.</span>
                </div>
              </div>

              <div className="mk-info-row">
                <div className="mk-ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--violet)" strokeWidth="2"><circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5 8 12 8 12s8-7 8-12a8 8 0 0 0-8-8z"/></svg></div>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text)' }}>Location</div>
                  <span style={{ color: 'var(--muted)', fontSize: 14 }}>United Kingdom</span>
                </div>
              </div>
            </div>

            <div className="mk-info-card">
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 20, marginBottom: 16 }}>Send us a message</h3>
              <div className="mk-field"><label>Your name</label><input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Jane Smith" /></div>
              <div className="mk-field"><label>Email</label><input value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} placeholder="jane@yourcouncil.gov.uk" /></div>
              <div className="mk-field"><label>Organisation</label><input value={f.org} onChange={(e) => setF({ ...f, org: e.target.value })} placeholder="Barchester Council" /></div>
              <div className="mk-field"><label>Message</label><textarea rows={4} value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} placeholder="How can we help?" /></div>
              <button className="mk-btn mk-btn-primary" style={{ width: '100%' }} onClick={send}>Send message</button>
              <p style={{ fontSize: 12.5, marginTop: 10 }}>This opens your email app addressed to support@reffolio.co.uk.</p>
            </div>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
