import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Selnikel Gemini Notebook',
  description: 'Grounded AI Engineering Knowledge & Studio Workstation for Selnikel Enerji',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr" className="dark">
      <body className="min-h-screen flex flex-col bg-[#131314] text-[#e3e3e3] antialiased selection:bg-[#a8c7fa] selection:text-[#041e49]">
        {children}
      </body>
    </html>
  );
}
