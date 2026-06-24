'use client';
import Link from 'next/link';
import '../marketing.css';
import MarketingNav from '../../components/MarketingNav';
import MarketingFooter from '../../components/MarketingFooter';

const PLANS = [
  { name: 'Free', price: '£0', unit: '', sub: 'For trying Reffolio or a single team getting started.', seats: '2 seats',
    features: ['2 seats', 'Issue & verify references', 'Tamper-evident records', 'Worker sharing by consent'], cta: 'Start free' },
  { name: 'Starter', price: '£49', unit: '/mo', sub: 'For a small team running references regularly.', seats: '3 seats',
    features: ['3 seats', 'Everything in Free', 'Team management', 'Reference records archive', 'Email support'], cta: 'Choose Starter' },
  { name: 'Growth', price: '£149', unit: '/mo', sub: 'For busy departments and growing agencies.', featured: true, seats: '10 seats',
    features: ['10 seats', 'Everything in Starter', 'Admin oversight & usage', 'Pay-as-you-go credits', 'Priority support'], cta: 'Choose Growth' },
  { name: 'Business', price: '£299', unit: '/mo', sub: 'For large teams and multi-branch agencies.', seats: '25 seats',
    features: ['25 seats', 'Everything in Growth', 'API access', 'Advanced reporting', 'Onboarding help'], cta: 'Choose Business' },
];

export default function Pricing() {
  return (
    <div className="mk">
      <MarketingNav />
      <section className="mk-pagehero">
        <div className="mk-container">
          <div className="mk-kicker" style={{ color: 'var(--violet)', fontWeight: 700, letterSpacing: '.08em' }}>PRICING</div>
          <h1 style={{ marginTop: 12 }}>Plans that scale with your team</h1>
          <p>Workers use Reffolio free, forever. Organisations pay per seat — every member or pending invite uses one seat. Cancel or change anytime.</p>
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
              <p style={{ marginTop: 6 }}>Unlimited seats, white-labelling, SSO, G-Cloud procurement and a dedicated contact — for councils and national agencies.</p>
            </div>
            <a href="mailto:support@reffolio.co.uk?subject=Enterprise%20enquiry" className="mk-btn mk-btn-primary">Talk to us</a>
          </div>

          <div className="mk-section-head" style={{ marginTop: 64 }}>
            <div className="mk-kicker">Every plan includes</div>
            <h2 style={{ fontSize: 30 }}>The things that make a reference trustworthy</h2>
          </div>
          <div className="mk-grid">
            <div className="mk-feature"><h3>Verified identity</h3><p>Registration checks against the relevant professional register before issue.</p></div>
            <div className="mk-feature"><h3>Tamper-evident seal</h3><p>Cryptographic hashing on every published reference, with referee confirmation.</p></div>
            <div className="mk-feature"><h3>Consent-based sharing</h3><p>Workers hold and share their own references — no chasing, no back-channels.</p></div>
          </div>
        </div>
      </section>

      <section className="mk-section" style={{ paddingTop: 0 }}>
        <div className="mk-container">
          <div className="mk-cta">
            <h2>Start free, upgrade when you{'\u2019'}re ready</h2>
            <p>Set up your organisation in minutes — no card required to begin.</p>
            <Link href="/signin" className="mk-btn mk-btn-primary mk-btn-lg">Get started</Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
