'use client';
import Link from 'next/link';

export default function MarketingFooter() {
  return (
    <footer className="mk-footer">
      <div className="mk-container">
        <div className="mk-footer-grid">
          <div>
            <div className="mk-brand" style={{ marginBottom: 12 }}>
              <img src="/icon.svg" alt="" style={{ width: 28, height: 28 }} />
              Reffolio
            </div>
            <p style={{ maxWidth: 280 }}>Verified, consent-shared employment references for UK regulated sectors. Tamper-evident, portable, and trusted.</p>
          </div>
          <div>
            <h4>Product</h4>
            <Link href="/#how">How it works</Link>
            <Link href="/#why">Why Reffolio</Link>
            <Link href="/pricing">Pricing</Link>
            <Link href="/download">Desktop app</Link>
          </div>
          <div>
            <h4>Company</h4>
            <Link href="/contact">Contact</Link>
            <a href="mailto:support@reffolio.co.uk">Support</a>
            <Link href="/signin">Sign in</Link>
          </div>
          <div>
            <h4>Get in touch</h4>
            <a href="mailto:support@reffolio.co.uk">support@reffolio.co.uk</a>
            <p>United Kingdom</p>
          </div>
        </div>
        <div className="mk-footer-bottom">
          <span>© {new Date().getFullYear()} Reffolio. All rights reserved.</span>
          <span>Built for UK regulated sectors · GDPR-aware by design</span>
        </div>
      </div>
    </footer>
  );
}
