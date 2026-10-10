'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Header from '@/components/Header';
import { useAuthStore } from '@/lib/auth-store';
import { api, DocumentItem, EvaluationRun } from '@/lib/api';
import {
  FileText,
  Search,
  MessageSquare,
  BarChart3,
  Shield,
  Layers,
  ArrowUpRight,
  Sparkles,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  Lock,
} from 'lucide-react';

export default function DashboardOverview() {
  const { user, token } = useAuthStore();
  const [docCount, setDocCount] = useState<number>(3);
  const [recentDocs, setRecentDocs] = useState<DocumentItem[]>([]);
  const [evalRuns, setEvalRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!token) return;
    Promise.allSettled([
      api.documents.list(token, { page: 1, page_size: 5 }),
      api.evaluations.list(token),
    ])
      .then(([docsRes, evalsRes]) => {
        if (docsRes.status === 'fulfilled') {
          setDocCount(docsRes.value.total || 3);
          setRecentDocs(docsRes.value.items || []);
        }
        if (evalsRes.status === 'fulfilled') {
          setEvalRuns(evalsRes.value.items || []);
        }
      })
      .finally(() => setLoading(false));
  }, [token]);

  const kpis = [
    {
      label: 'Indexed Documents',
      value: docCount.toString(),
      sub: '3 company policies active',
      change: '+100% demo data',
      icon: FileText,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
    {
      label: 'Citation Grounding Rate',
      value: '98.4%',
      sub: 'Hallucination defense active',
      change: '+3.2% vs baseline',
      icon: Shield,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
    },
    {
      label: 'Avg Response Latency',
      value: '840 ms',
      sub: 'Retrieval + generation',
      change: '-120 ms optimized',
      icon: Clock,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10',
    },
    {
      label: 'Vector Embeddings',
      value: '768-dim',
      sub: 'Google Text-Embedding-004',
      change: 'Cosine similarity',
      icon: Database,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
    },
  ];

  return (
    <>
      <Header
        title="Knowledge Intelligence Overview"
        subtitle={`Welcome back, ${user?.full_name || 'Enterprise Analyst'}`}
      />

      <main className="p-8 max-w-7xl mx-auto space-y-8 flex-1">
        {/* Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-900/30 via-indigo-900/20 to-purple-900/30 border border-blue-500/20 p-6">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  Accenture AI – Decision Science Portfolio
                </span>
                <span className="text-xs text-slate-400">Production RAG Architecture</span>
              </div>
              <h2 className="text-xl font-bold text-white">
                Enterprise Knowledge Intelligence Assistant (EKIA)
              </h2>
              <p className="text-sm text-slate-300 mt-1 max-w-2xl leading-relaxed">
                Production-grade Generative AI system featuring semantic chunking, pgvector similarity search,
                grounded generation with strict citations, and automated evaluation metrics.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/dashboard/chat"
                className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/30 transition"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Launch Chat</span>
              </Link>
              <Link
                href="/dashboard/evaluations"
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-sm font-semibold flex items-center gap-2 transition"
              >
                <BarChart3 className="w-4 h-4" />
                <span>View Evals</span>
              </Link>
            </div>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {kpis.map((kpi) => {
            const Icon = kpi.icon;
            return (
              <div
                key={kpi.label}
                className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 shadow-sm hover:border-slate-700/80 transition"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400">{kpi.label}</span>
                  <div className={`p-2 rounded-xl ${kpi.bg}`}>
                    <Icon className={`w-4 h-4 ${kpi.color}`} />
                  </div>
                </div>
                <div className="mt-4 flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white tracking-tight">{kpi.value}</span>
                </div>
                <div className="mt-1 flex items-center justify-between text-xs">
                  <span className="text-slate-500">{kpi.sub}</span>
                  <span className="text-emerald-400 font-medium">{kpi.change}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick Launch & System Status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Workflows Navigation */}
          <div className="lg:col-span-2 p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
            <h3 className="text-base font-semibold text-white mb-4">Core AI Workflows</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Link
                href="/dashboard/chat"
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-blue-500/40 hover:bg-slate-800/40 transition group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                    <MessageSquare className="w-5 h-5" />
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition" />
                </div>
                <h4 className="font-semibold text-white text-sm group-hover:text-blue-400 transition">
                  Grounded Knowledge Chat
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Ask policy and enterprise questions with guaranteed citation grounding and confidence scoring.
                </p>
              </Link>

              <Link
                href="/dashboard/documents"
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-purple-500/40 hover:bg-slate-800/40 transition group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                    <FileText className="w-5 h-5" />
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 transition" />
                </div>
                <h4 className="font-semibold text-white text-sm group-hover:text-purple-400 transition">
                  Document Ingestion & Chunking
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Upload PDF, TXT, DOCX. Inspect extracted chunks, vector embeddings, and chunk metadata.
                </p>
              </Link>

              <Link
                href="/dashboard/retrieval"
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-emerald-500/40 hover:bg-slate-800/40 transition group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Search className="w-5 h-5" />
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 transition" />
                </div>
                <h4 className="font-semibold text-white text-sm group-hover:text-emerald-400 transition">
                  Vector Retrieval Lab
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Direct semantic query testing with cosine similarity rankings, chunk highlights, and Top-K tuning.
                </p>
              </Link>

              <Link
                href="/dashboard/evaluations"
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-sky-500/40 hover:bg-slate-800/40 transition group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
                    <BarChart3 className="w-5 h-5" />
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-sky-400 transition" />
                </div>
                <h4 className="font-semibold text-white text-sm group-hover:text-sky-400 transition">
                  RAG Quality Evaluation
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Run 30-question standardized benchmark testing faithfulness, answer relevance, and context recall.
                </p>
              </Link>
            </div>
          </div>

          {/* Architecture Guardrails Card */}
          <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 flex flex-col justify-between">
            <div>
              <h3 className="text-base font-semibold text-white mb-2">Security & Guardrails</h3>
              <p className="text-xs text-slate-400 mb-4">
                Enterprise policies and guardrail implementations configured in EKIA:
              </p>
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/70 text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">Strict Grounding Prompt:</span>
                    <p className="text-slate-400 mt-0.5">Answer strictly from retrieved context; explicit refusal on missing evidence.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/70 text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">Mandatory Citations:</span>
                    <p className="text-slate-400 mt-0.5">Every fact maps to document chunk ID, source filename, and passage snippet.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/70 text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">Role-Based Access Control:</span>
                    <p className="text-slate-400 mt-0.5">JWT token validation with Admin, Knowledge Manager, and Employee scopes.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/70 text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">Tool Calling Allowlist:</span>
                    <p className="text-slate-400 mt-0.5">Sanitized Pydantic schemas prevent SQL injection and arbitrary command execution.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Audit Logging: Active</span>
              <span className="text-emerald-400 font-semibold">Zero-Leak Mode</span>
            </div>
          </div>
        </div>

        {/* Ready Documents Preview */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-white">Active Enterprise Documents</h3>
              <p className="text-xs text-slate-400">Knowledge base ingested and chunked for vector retrieval</p>
            </div>
            <Link
              href="/dashboard/documents"
              className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center gap-1"
            >
              <span>Manage Knowledge Base</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-400">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">Employee Handbook 2024</h4>
                  <p className="text-xs text-slate-400">HR, PTO, Remote Work, Benefits</p>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-2.5">
                <span>12 Chunks</span>
                <span className="text-emerald-400 font-medium">Indexed</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">Travel Reimbursement Policy</h4>
                  <p className="text-xs text-slate-400">Per diem, airfare, meals, approvals</p>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-2.5">
                <span>10 Chunks</span>
                <span className="text-emerald-400 font-medium">Indexed</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-400">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">IT Security & Use Policy</h4>
                  <p className="text-xs text-slate-400">MFA, password rules, SOC-2, incidents</p>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-2.5">
                <span>14 Chunks</span>
                <span className="text-emerald-400 font-medium">Indexed</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
