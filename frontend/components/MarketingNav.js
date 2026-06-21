'use client';
import { useState } from 'react';
import Link from 'next/link';

export default function MarketingNav() {
  const [open, setOpen] = useState(false);
  return (
    <nav className={'mk-nav' + (open ? ' open' : '')}>
      <div className="mk-container mk-nav-in">
        <Link href="/" className="mk-brand">
          <img src="/icon.svg" alt="" />
          Reffolio
        </Link>
        <div className="mk-links">
          <Link href="/#how" onClick={() => setOpen(false)}>How it works</Link>
          <Link href="/#why" onClick={() => setOpen(false)}>Why Reffolio</Link>
          <Link href="/pricing" onClick={() => setOpen(false)}>Pricing</Link>
          <Link href="/contact" onClick={() => setOpen(false)}>Contact</Link>
        </div>
        <div className="mk-nav-cta">
          <Link href="/signin" className="mk-btn mk-btn-ghost mk-btn-sm">Sign in</Link>
          <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-sm">Get started</Link>
          <button className="mk-menu-btn" aria-label="Menu" onClick={() => setOpen(!open)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
          </button>
        </div>
      </div>
    </nav>
  );
}
