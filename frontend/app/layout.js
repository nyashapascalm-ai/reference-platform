import './globals.css';

export const metadata = {
  title: 'Refera — verified, consent-shared references',
  description: 'Refera holds employment references in trust: verified, tamper-evident, and shared only with consent.',
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
