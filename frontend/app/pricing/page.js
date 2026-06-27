'use client';
import Link from 'next/link';
import '../marketing.css';
import MarketingNav from '../../components/MarketingNav';
import MarketingFooter from '../../components/MarketingFooter';

const PLANS = [
  { name: 'Starter', price: '£29', unit: '/mo', sub: 'A single team, small school or care home.', seats: '2 seats',
    features: ['2 seats', '14-day free trial', 'Request & receive references', 'Tamper-evident records', 'Consent-based release', 'Sector-specific forms'], cta: 'Start 14-day trial' },
  { name: 'Team', price: '£49', unit: '/mo', sub: 'A larger provider running references regularly.', seats: '8 seats',
    features: ['8 seats', '14-day free trial', 'Everything in Starter', 'Team management & invites', 'Admin oversight & records', 'Email support'], cta: 'Start 14-day trial' },
  { name: 'Growth', price: '£149', unit: '/mo', sub: 'For busy departments and growing agencies.', featured: true, seats: '15 seats',
    features: ['15 seats', '14-day free trial', 'Everything in Team', 'API access', 'White-label references', 'Pay-as-you-go credits', 'Priority support'], cta: 'Start 14-day trial' },
  { name: 'Business', price: '£299', unit: '/mo', sub: 'For large teams and multi-branch agencies.', seats: '25 seats',
    features: ['25 seats', '14-day free trial', 'Everything in Growth', 'Onboarding support', 'Priority support'], cta: 'Start 14-day trial' },
];

export default function Pricing() {
  return (
    <div className="mk">
      <MarketingNav />
      <section className="mk-pagehero">
        <div className="mk-container">
          <div className="mk-kicker" style={{ color: 'var(--violet)', fontWeight: 700, letterSpacing: '.08em' }}>PRICING</div>
          <h1 style={{ marginTop: 12 }}>Plans that scale with your team</h1>
          <p>Every plan starts with a 14-day free trial. Organisations pay per seat. Cancel or change anytime.</p>
        </div>
      </section>

      <section className="mk-section" style={{ paddingTop: 24 }}>
        <div className="mk-container">
          <div className="mk-price-grid">
            {PLANS.map((p) => (
              <div key={p.name} className={'mk-plan' + (p.featured ? ' featured' : '')}>
                {p.featured && <div className="mk-plan-badge">Most popular</div>}
                <h3>{p.name}</h3>
                <div className="mk-price">{p.price}<small>{p.unit}</small></div>
                <div className="mk-plan-sub">{p.sub}</div>
                <ul>{p.features.map((f, i) => <li key={i}>{f}</li>)}</ul>
                <Link href="/signin" className={'mk-btn ' + (p.featured ? 'mk-btn-primary' : 'mk-btn-ghost')}>{p.cta}</Link>
              </div>
            ))}
          </div>

          <div className="mk-enterprise">
            <div>
              <h3 style={{ fontSize: 20 }}>Enterprise</h3>
              <p style={{ marginTop: 6 }}>Unlimited seats, white-labelling, SSO, G-Cloud procurement and a dedicated contact â€” for councils and national agencies.</p>
            </div>
            <a href="mailto:support@reffolio.co.uk?subject=Enterprise%20enquiry" className="mk-btn mk-btn-primary">Talk to us</a>
          </div>

          <div className="mk-section-head" style={{ marginTop: 64 }}>
            <div className="mk-kicker">Every plan includes</div>
            <h2 style={{ fontSize: 30 }}>The things that make a reference trustworthy</h2>
          </div>
          <div className="mk-grid">
            <div className="mk-feature"><h3>Verified referee</h3><p>The previous employer completes the reference from their work email; free-mail addresses are flagged.</p></div>
            <div className="mk-feature"><h3>Tamper-evident seal</h3><p>Cryptographic hashing on every published reference, with referee confirmation.</p></div>
            <div className="mk-feature"><h3>Consent-based release</h3><p>The candidate consents before a reference is released to the requester.</p></div>
          </div>
        </div>
      </section>

      <section className="mk-section" style={{ paddingTop: 0 }}>
        <div className="mk-container">
          <div className="mk-cta">
            <h2>Start your 14-day trial</h2>
            <p>Set up your organisation in minutes. Try every feature free for 14 days.</p>
            <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Get started</Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
