import './globals.css';

export const metadata = {
  title: 'Reffolio — verified, consent-shared references',
  description: 'Reffolio holds employment references in trust: verified, tamper-evident, and shared only with consent.',
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
