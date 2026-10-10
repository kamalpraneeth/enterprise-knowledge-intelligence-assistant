import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'EKIA — Enterprise Knowledge Intelligence Assistant',
  description:
    'AI-powered enterprise knowledge management with RAG, vector search, and secure document retrieval. Built on Google Gemini, FastAPI, and pgvector.',
  keywords: ['enterprise AI', 'RAG', 'knowledge base', 'document search', 'Gemini'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
