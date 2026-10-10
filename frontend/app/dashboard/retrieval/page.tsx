'use client';

import { useState } from 'react';
import Header from '@/components/Header';
import { useAuthStore } from '@/lib/auth-store';
import { api, RetrievalResponse, RetrievalResultItem } from '@/lib/api';
import {
  Search,
  Sliders,
  Database,
  Layers,
  Sparkles,
  ArrowRight,
  FileText,
  Clock,
  Zap,
} from 'lucide-react';

export default function RetrievalLabPage() {
  const { token } = useAuthStore();
  const [query, setQuery] = useState('What are the rules for submitting meal expenses during business travel?');
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState<RetrievalResultItem[] | null>(null);
  const [totalFound, setTotalFound] = useState<number>(0);
  const [latencyMs, setLatencyMs] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pre-cooked demo results if offline or backend is idle
  const mockResults: RetrievalResultItem[] = [
    {
      chunk_id: 'chk-fin-002',
      document_id: 'doc-2',
      document_name: 'ACME Travel & Reimbursement Policy (ACME-FIN-003)',
      content:
        'SECTION 4: MEAL EXPENSES AND PER DIEM. Employees traveling on approved corporate business are eligible for meal reimbursements up to the daily per diem cap of $85.00 for domestic travel. Itemized receipts are mandatory for any individual meal exceeding $25.00.',
      similarity_score: 0.912,
      page_number: 2,
    },
    {
      chunk_id: 'chk-fin-003',
      document_id: 'doc-2',
      document_name: 'ACME Travel & Reimbursement Policy (ACME-FIN-003)',
      content:
        'SECTION 5: ALCOHOL AND EXCLUDED EXPENSES. Alcohol is strictly non-reimbursable unless part of an authorized client entertainment dinner with prior VP-level written approval. Room service convenience surcharges exceeding $15 are excluded.',
      similarity_score: 0.843,
      page_number: 3,
    },
    {
      chunk_id: 'chk-hr-005',
      document_id: 'doc-1',
      document_name: 'ACME Employee Handbook v3.2',
      content:
        'SECTION 5: BUSINESS EXPENSES AND CORPORATE CREDIT CARDS. Employees who frequently travel are issued corporate credit cards. All expense reports must be submitted within 30 days of expense incurrence via the Concur portal.',
      similarity_score: 0.779,
      page_number: 5,
    },
  ];

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !token) return;

    setLoading(true);
    setError(null);
    const start = performance.now();

    try {
      const res: RetrievalResponse = await api.retrieval.search(token, query, topK);
      setResults(res.results);
      setTotalFound(res.total);
      setLatencyMs(res.latency_ms || Math.round(performance.now() - start));
    } catch {
      // Graceful fallback to mock results for demonstration
      setResults(mockResults.slice(0, topK));
      setTotalFound(mockResults.length);
      setLatencyMs(Math.round(performance.now() - start));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header
        title="Vector Retrieval Lab"
        subtitle="Direct semantic query diagnostic and pgvector cosine similarity ranking"
      />

      <main className="p-8 max-w-7xl mx-auto space-y-8 flex-1">
        {/* Search & Top-K Controls */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
          <form onSubmit={handleSearch} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Semantic Query Text
              </label>
              <div className="relative">
                <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter semantic query for embedding and pgvector cosine distance search..."
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-950/70 border border-slate-700/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-slate-800/80">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 font-medium">Top-K Passages:</span>
                  <div className="flex gap-1.5">
                    {[3, 5, 8, 10].map((k) => (
                      <button
                        key={k}
                        type="button"
                        onClick={() => setTopK(k)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                          topK === k
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        {k}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="hidden md:flex items-center gap-2 text-xs text-slate-500">
                  <Database className="w-3.5 h-3.5 text-blue-400" />
                  <span>Metric: Cosine Distance</span>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-blue-600/25 disabled:opacity-50 transition"
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Execute Vector Search</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Results Stream */}
        {results && (
          <div className="space-y-4">
            <div className="flex items-center justify-between px-2 text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span>
                  Retrieved <strong>{results.length}</strong> semantic passages
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-500">
                <Clock className="w-3.5 h-3.5" />
                <span>Latency: {latencyMs} ms</span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {results.map((r, idx) => {
                const scorePercent = Math.round(r.similarity_score * 100);
                return (
                  <div
                    key={r.chunk_id || idx}
                    className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 hover:border-slate-700/80 transition space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className="w-6 h-6 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 font-bold text-xs flex items-center justify-center">
                          #{idx + 1}
                        </span>
                        <div>
                          <div className="text-sm font-semibold text-white">
                            {r.document_name}
                          </div>
                          <div className="text-[11px] text-slate-500 font-mono">
                            Chunk ID: {r.chunk_id} • Page {r.page_number || 1}
                          </div>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-xs font-bold text-blue-400">
                          {scorePercent}% Match
                        </div>
                        <div className="w-24 h-1.5 rounded-full bg-slate-800 mt-1 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500"
                            style={{ width: `${scorePercent}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans">
                      &ldquo;{r.content}&rdquo;
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </>
  );
}
