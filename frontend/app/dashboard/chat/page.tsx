'use client';

import { useState, useRef, useEffect } from 'react';
import Header from '@/components/Header';
import { useAuthStore } from '@/lib/auth-store';
import { api, ChatResponse, Citation } from '@/lib/api';
import {
  Brain,
  Send,
  User,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  ShieldAlert,
  Clock,
  BookOpen,
  Info,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Sliders,
  ExternalLink,
} from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  has_sufficient_evidence?: boolean;
  retrieval_latency_ms?: number;
  generation_latency_ms?: number;
  total_latency_ms?: number;
  rating?: number;
}

const SAMPLE_QUESTIONS = [
  'What is the annual PTO accrual rate for full-time employees?',
  'What is the maximum allowed reimbursement for dinner on domestic travel?',
  'What are the password complexity and MFA requirements?',
  'Who is the CEO of Acme Corporation and what was 2023 revenue?',
];

export default function ChatPage() {
  const { token, user } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Hello! I am your Enterprise Knowledge Intelligence Assistant (EKIA). I can answer questions grounded in our verified corporate policies (Employee Handbook, Travel Reimbursement, IT Security). Every answer is backed by exact citations with chunk traceability.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [showConfig, setShowConfig] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const toggleCitation = (msgId: string) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleSend = async (questionText?: string) => {
    const q = questionText || input;
    if (!q.trim() || loading || !token) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: q.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!questionText) setInput('');
    setLoading(true);

    try {
      const res: ChatResponse = await api.chat.send(token, q.trim(), conversationId);
      setConversationId(res.conversation_id);

      const assistantMessage: Message = {
        id: res.message.id || `asst-${Date.now()}`,
        role: 'assistant',
        content: res.message.content,
        citations: res.message.citations,
        has_sufficient_evidence: res.message.has_sufficient_evidence,
        retrieval_latency_ms: res.message.retrieval_latency_ms,
        generation_latency_ms: res.message.generation_latency_ms,
        total_latency_ms: res.message.total_latency_ms,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      const errorMessage: Message = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content:
          err instanceof Error
            ? `⚠️ Request failed: ${err.message}`
            : '⚠️ An error occurred while communicating with the AI service.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (messageId: string, rating: number) => {
    if (!token) return;
    try {
      await api.chat.feedback(token, messageId, rating);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, rating } : m))
      );
    } catch (e) {
      console.error('Feedback submission failed', e);
    }
  };

  const handleReset = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          'Conversation reset. Ask any question grounded in our enterprise policies.',
      },
    ]);
    setConversationId(undefined);
  };

  return (
    <>
      <Header
        title="Enterprise Knowledge Chat"
        subtitle="Retrieval-Augmented Generation with strict citation verification"
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Main Chat Flow */}
        <div className="flex-1 flex flex-col h-[calc(100vh-4rem)]">
          {/* Top Actions Bar */}
          <div className="px-6 py-2.5 border-b border-slate-800 bg-slate-900/40 flex items-center justify-between">
            <div className="flex items-center gap-2 overflow-x-auto py-1 scrollbar-none">
              <span className="text-xs text-slate-500 font-medium whitespace-nowrap">
                Sample Queries:
              </span>
              {SAMPLE_QUESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(q)}
                  disabled={loading}
                  className="px-2.5 py-1 rounded-lg text-xs bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition disabled:opacity-50"
                >
                  {q.slice(0, 38)}...
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 pl-4">
              <button
                onClick={handleReset}
                title="Reset Conversation"
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowConfig(!showConfig)}
                title="Toggle RAG Configuration"
                className={`p-1.5 rounded-lg transition ${
                  showConfig
                    ? 'text-blue-400 bg-blue-500/10'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <Sliders className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              const hasCitations = msg.citations && msg.citations.length > 0;
              const isExpanded = expandedCitations[msg.id];

              return (
                <div
                  key={msg.id}
                  className={`flex gap-4 max-w-4xl ${
                    isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      isUser
                        ? 'bg-blue-600 text-white'
                        : 'bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-md shadow-indigo-600/20'
                    }`}
                  >
                    {isUser ? (
                      <User className="w-4 h-4" />
                    ) : (
                      <Brain className="w-4 h-4" />
                    )}
                  </div>

                  {/* Bubble Content */}
                  <div
                    className={`space-y-3 max-w-[85%] ${
                      isUser
                        ? 'bg-blue-600 text-white px-5 py-3.5 rounded-2xl rounded-tr-sm shadow-md'
                        : 'bg-slate-900/90 border border-slate-800 text-slate-100 p-5 rounded-2xl rounded-tl-sm shadow-xl'
                    }`}
                  >
                    {/* Insufficient Evidence Warning Banner */}
                    {!isUser && msg.has_sufficient_evidence === false && (
                      <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5 text-xs text-amber-300">
                        <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold">Ungrounded Query Alert:</span>
                          <p className="mt-0.5 text-amber-300/80">
                            The enterprise knowledge base lacks conclusive evidence for this question. Guardrails prevented extrapolation or hallucinations.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Text content */}
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </div>

                    {/* Citations Preview & Toggle */}
                    {!isUser && hasCitations && (
                      <div className="mt-3 pt-3 border-t border-slate-800">
                        <div className="flex items-center justify-between">
                          <button
                            onClick={() => toggleCitation(msg.id)}
                            className="flex items-center gap-1.5 text-xs font-semibold text-blue-400 hover:text-blue-300 transition"
                          >
                            <BookOpen className="w-3.5 h-3.5" />
                            <span>
                              {msg.citations!.length} Source Citation
                              {msg.citations!.length > 1 ? 's' : ''}
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </button>

                          {/* Latency Chips */}
                          {msg.total_latency_ms && (
                            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                              <Clock className="w-3 h-3" />
                              <span>{msg.total_latency_ms} ms</span>
                              {msg.retrieval_latency_ms && (
                                <span className="text-slate-600">
                                  (ret: {msg.retrieval_latency_ms}ms)
                                </span>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Collapsible Citations Drawer */}
                        {isExpanded && (
                          <div className="mt-3 space-y-2.5 animate-in">
                            {msg.citations!.map((cit, cIdx) => (
                              <div
                                key={cIdx}
                                className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-xs space-y-1.5"
                              >
                                <div className="flex items-center justify-between text-slate-400">
                                  <div className="flex items-center gap-2">
                                    <span className="font-semibold text-blue-400">
                                      [{cit.rank || cIdx + 1}]
                                    </span>
                                    <span className="text-slate-200 font-medium truncate max-w-[200px]">
                                      {cit.document_name || 'Enterprise Policy'}
                                    </span>
                                  </div>
                                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                                    Sim: {((cit.similarity_score ?? 0.85) * 100).toFixed(1)}%
                                  </span>
                                </div>
                                <p className="text-slate-300 italic text-[11px] leading-relaxed bg-slate-900/40 p-2 rounded border border-slate-800/60">
                                  &ldquo;{cit.passage || ''}&rdquo;
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Bottom Metadata & Feedback */}
                    {!isUser && msg.id !== 'welcome' && (
                      <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
                        <div className="text-[11px] text-slate-500">
                          Grounded by Gemini 1.5 + pgvector
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleFeedback(msg.id, 1)}
                            className={`p-1 rounded hover:bg-slate-800 transition ${
                              msg.rating === 1 ? 'text-emerald-400' : 'text-slate-500'
                            }`}
                            title="Helpful"
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleFeedback(msg.id, -1)}
                            className={`p-1 rounded hover:bg-slate-800 transition ${
                              msg.rating === -1 ? 'text-rose-400' : 'text-slate-500'
                            }`}
                            title="Unhelpful"
                          >
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex gap-4 max-w-4xl mr-auto">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center flex-shrink-0 animate-pulse">
                  <Brain className="w-4 h-4" />
                </div>
                <div className="bg-slate-900/90 border border-slate-800 text-slate-400 px-5 py-4 rounded-2xl rounded-tl-sm flex items-center gap-3 text-sm">
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" />
                    <span
                      className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce"
                      style={{ animationDelay: '0.15s' }}
                    />
                    <span
                      className="w-2 h-2 rounded-full bg-purple-500 animate-bounce"
                      style={{ animationDelay: '0.3s' }}
                    />
                  </div>
                  <span>Searching pgvector knowledge base & generating citation...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="p-4 border-t border-slate-800 bg-slate-900/60 backdrop-blur">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="max-w-4xl mx-auto flex items-center gap-3"
            >
              <div className="relative flex-1">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question about employee policies, travel reimbursement, or IT security..."
                  disabled={loading}
                  className="w-full px-4 py-3 rounded-xl bg-slate-950/80 border border-slate-700/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition disabled:opacity-50"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm transition shadow-lg shadow-blue-600/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <span>Ask</span>
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>

        {/* Right Drawer: RAG Pipeline Configuration */}
        {showConfig && (
          <aside className="w-80 border-l border-slate-800 bg-[hsl(222,47%,7%)] p-6 space-y-6 overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <Sliders className="w-4 h-4 text-blue-400" />
                <span>RAG Pipeline Specs</span>
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">
                Active
              </span>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <span className="text-slate-400 uppercase tracking-wider font-semibold">
                  Generative Model
                </span>
                <p className="mt-1 font-mono text-slate-200 bg-slate-900 p-2 rounded-lg border border-slate-800">
                  google/gemini-1.5-pro
                </p>
              </div>

              <div>
                <span className="text-slate-400 uppercase tracking-wider font-semibold">
                  Vector Database
                </span>
                <p className="mt-1 font-mono text-slate-200 bg-slate-900 p-2 rounded-lg border border-slate-800">
                  PostgreSQL 16 + pgvector (HNSW)
                </p>
              </div>

              <div>
                <span className="text-slate-400 uppercase tracking-wider font-semibold">
                  Embedding Model
                </span>
                <p className="mt-1 font-mono text-slate-200 bg-slate-900 p-2 rounded-lg border border-slate-800">
                  text-embedding-004 (768 dims)
                </p>
              </div>

              <div>
                <span className="text-slate-400 uppercase tracking-wider font-semibold">
                  Chunking Strategy
                </span>
                <p className="mt-1 text-slate-300 bg-slate-900 p-2 rounded-lg border border-slate-800">
                  Recursive character splitter (chunk_size: 500 tokens, overlap: 50)
                </p>
              </div>

              <div>
                <span className="text-slate-400 uppercase tracking-wider font-semibold">
                  Guardrails & Hallucination Defense
                </span>
                <p className="mt-1 text-slate-300 bg-slate-900 p-2 rounded-lg border border-slate-800 leading-relaxed">
                  Strict instruction: Answer exclusively from retrieved passages. If missing evidence, emit standard disclaimer.
                </p>
              </div>
            </div>
          </aside>
        )}
      </div>
    </>
  );
}
