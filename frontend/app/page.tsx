'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useAuthStore } from '@/lib/auth-store';
import {
  Brain,
  Shield,
  Search,
  FileText,
  BarChart3,
  ArrowRight,
  Database,
  Zap,
  Lock,
  CheckCircle2,
} from 'lucide-react';

const features = [
  {
    icon: Brain,
    title: 'Generative AI Answers',
    description: 'Google Gemini generates grounded answers from your enterprise documents with full source citations.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
  },
  {
    icon: Search,
    title: 'Vector Search (RAG)',
    description: 'pgvector-powered semantic retrieval finds the most relevant passages from your knowledge base.',
    color: 'text-violet-400',
    bg: 'bg-violet-500/10',
  },
  {
    icon: Shield,
    title: 'Role-Based Access',
    description: 'Admin, Knowledge Manager, and Employee roles with JWT authentication and audit logging.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
  },
  {
    icon: FileText,
    title: 'Document Ingestion',
    description: 'Upload PDF, TXT, and DOCX files. Automatic extraction, chunking, and embedding generation.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
  },
  {
    icon: BarChart3,
    title: 'AI Evaluation',
    description: 'Measure retrieval precision, answer correctness, citation accuracy, and latency distribution.',
    color: 'text-sky-400',
    bg: 'bg-sky-500/10',
  },
  {
    icon: Zap,
    title: 'Agentic Tool Calling',
    description: 'Controlled tool execution with search, policy lookup, and support request creation.',
    color: 'text-pink-400',
    bg: 'bg-pink-500/10',
  },
];

const techStack = [
  'Google Gemini API', 'FastAPI', 'PostgreSQL + pgvector',
  'LangChain', 'Next.js', 'Docker', 'JWT Auth', 'Alembic'
];

export default function LandingPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (token) router.push('/dashboard');
  }, [token, router]);

  return (
    <div className="min-h-screen bg-[hsl(222,47%,8%)] text-slate-100">
      {/* Nav */}
      <nav className="border-b border-slate-800 bg-[hsl(222,47%,7%)]/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">EKIA</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-slate-400">
            <span>Features</span>
            <span>Architecture</span>
            <span>Pricing</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/auth/login"
              className="text-sm text-slate-300 hover:text-white transition-colors px-4 py-2"
            >
              Sign In
            </Link>
            <Link
              href="/auth/register"
              className="text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-4 py-2 transition-colors font-medium"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 text-blue-400 text-sm mb-8">
          <Zap className="w-3.5 h-3.5" />
          Enterprise AI · Hi-Tech · Decision Science
        </div>
        <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6 leading-tight">
          Turn Your Documents
          <br />
          <span className="gradient-text">Into Intelligence</span>
        </h1>
        <p className="text-slate-400 text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
          Enterprise Knowledge Intelligence Assistant — find answers, get insights, 
          and automate knowledge workflows with Generative AI and RAG.
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <Link
            href="/auth/register"
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-6 py-3 font-semibold transition-colors"
          >
            Get Started
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/auth/login"
            className="flex items-center gap-2 border border-slate-700 hover:border-slate-500 text-slate-300 rounded-xl px-6 py-3 font-semibold transition-colors"
          >
            Watch Demo
          </Link>
        </div>
        <div className="flex items-center justify-center gap-8 mt-12 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4" />
            Secure & Private
          </div>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Source Citations
          </div>
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Role-Based Access
          </div>
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            Enterprise Ready
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Everything You Need</h2>
          <p className="text-slate-400 text-lg">
            A complete production-grade RAG system built for enterprise requirements.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="bg-[hsl(222,47%,11%)] border border-slate-800 rounded-2xl p-6 card-hover"
            >
              <div className={`w-12 h-12 rounded-xl ${feature.bg} flex items-center justify-center mb-4`}>
                <feature.icon className={`w-6 h-6 ${feature.color}`} />
              </div>
              <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section className="max-w-7xl mx-auto px-6 py-16 border-t border-slate-800">
        <p className="text-center text-slate-500 text-sm mb-8">Built with enterprise-grade technology</p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {techStack.map((tech) => (
            <span
              key={tech}
              className="bg-slate-800/60 border border-slate-700 text-slate-300 rounded-lg px-4 py-2 text-sm"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="bg-gradient-to-r from-blue-600/20 to-violet-600/20 border border-blue-500/20 rounded-3xl p-12 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
          <p className="text-slate-400 mb-8">
            Create a free account and upload your first document in minutes.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/auth/register"
              className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-8 py-3 font-semibold transition-colors"
            >
              Create Account
            </Link>
            <Link
              href="/auth/login"
              className="border border-slate-600 hover:border-slate-400 text-slate-300 rounded-xl px-8 py-3 font-semibold transition-colors"
            >
              Sign In
            </Link>
          </div>
          <p className="text-slate-600 text-xs mt-6">
            Portfolio demonstration — not a certified enterprise security product.
            See README for setup instructions.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 text-center text-slate-600 text-sm">
        <p>© 2024 EKIA Portfolio Project · Built with FastAPI, Next.js, Google Gemini & pgvector</p>
      </footer>
    </div>
  );
}
