import './globals.css';

export const metadata = {
  metadataBase: new URL('https://reffolio.co.uk'),
  title: 'Reffolio — verified, consent-shared references for UK regulated work',
  description: 'Reffolio gives workers a verified, tamper-evident reference they hold and share with consent — so councils and agencies can trust what they receive. AI-assisted drafting, human integrity.',
  icons: { icon: '/icon.svg' },
  openGraph: {
    title: 'Reffolio — the reference layer for UK regulated work',
    description: 'Verified, tamper-evident, consent-shared references for social work, health and education.',
    url: 'https://reffolio.co.uk',
    siteName: 'Reffolio',
    type: 'website',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="aurora" />
        <div className="app">{children}</div>
      </body>
    </html>
  );
}
