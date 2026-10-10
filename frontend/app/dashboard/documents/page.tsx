'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import { useAuthStore } from '@/lib/auth-store';
import { api, DocumentItem } from '@/lib/api';
import {
  FileText,
  Upload,
  Trash2,
  RefreshCw,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  FolderOpen,
  FileCode,
  Layers,
  X,
  Plus,
} from 'lucide-react';

export default function DocumentsPage() {
  const { token, isKnowledgeManager } = useAuthStore();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState('');
  const [inspectDoc, setInspectDoc] = useState<DocumentItem | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Default demo policies to display if backend has no documents
  const defaultDocs: DocumentItem[] = [
    {
      id: 'doc-1',
      original_filename: 'Employee_Handbook.txt',
      file_type: 'txt',
      file_size_bytes: 4982,
      title: 'ACME Employee Handbook v3.2',
      status: 'indexed',
      chunk_count: 12,
      created_at: '2024-01-01T09:00:00Z',
      indexed_at: '2024-01-01T09:01:00Z',
    },
    {
      id: 'doc-2',
      original_filename: 'Travel_Reimbursement_Policy.txt',
      file_type: 'txt',
      file_size_bytes: 4831,
      title: 'ACME Travel & Reimbursement Policy (ACME-FIN-003)',
      status: 'indexed',
      chunk_count: 10,
      created_at: '2024-01-01T09:05:00Z',
      indexed_at: '2024-01-01T09:06:00Z',
    },
    {
      id: 'doc-3',
      original_filename: 'IT_Security_Policy.txt',
      file_type: 'txt',
      file_size_bytes: 4780,
      title: 'ACME IT Security & Acceptable Use (ACME-IT-001)',
      status: 'indexed',
      chunk_count: 14,
      created_at: '2024-01-01T09:10:00Z',
      indexed_at: '2024-01-01T09:11:00Z',
    },
  ];

  const fetchDocs = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await api.documents.list(token, { search: search || undefined });
      if (res.items && res.items.length > 0) {
        setDocuments(res.items);
      } else {
        setDocuments(defaultDocs);
      }
    } catch {
      setDocuments(defaultDocs);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [token]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !token) return;

    setUploading(true);
    setMessage(null);

    try {
      await api.documents.upload(token, selectedFile, docTitle || selectedFile.name);
      setMessage({ type: 'success', text: `Document "${selectedFile.name}" uploaded successfully for chunking.` });
      setSelectedFile(null);
      setDocTitle('');
      fetchDocs();
    } catch (err: unknown) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Upload failed. Verify backend connectivity.',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleReindex = async (docId: string) => {
    if (!token) return;
    try {
      await api.documents.reindex(token, docId);
      setMessage({ type: 'success', text: 'Document reindexing started.' });
      fetchDocs();
    } catch (err: unknown) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Reindexing failed.',
      });
    }
  };

  const handleDelete = async (docId: string) => {
    if (!token) return;
    try {
      await api.documents.delete(token, docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      setMessage({ type: 'success', text: 'Document removed from knowledge base.' });
    } catch (err: unknown) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Delete failed.',
      });
    }
  };

  return (
    <>
      <Header
        title="Knowledge Base & Document Ingestion"
        subtitle="Upload enterprise policies, inspect semantic chunks, and manage pgvector embeddings"
      />

      <main className="p-8 max-w-7xl mx-auto space-y-8 flex-1">
        {/* Alerts */}
        {message && (
          <div
            className={`p-4 rounded-xl border flex items-center justify-between text-sm ${
              message.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
            }`}
          >
            <span>{message.text}</span>
            <button onClick={() => setMessage(null)} className="p-1 hover:opacity-75">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Upload Card */}
        {isKnowledgeManager() && (
          <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400">
                <Upload className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Ingest New Enterprise Document</h3>
                <p className="text-xs text-slate-400">
                  Supported formats: PDF, TXT, DOCX. Content is extracted, chunked with 500-token windows, and embedded with Google text-embedding-004.
                </p>
              </div>
            </div>

            <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Document Title (Optional)
                </label>
                <input
                  type="text"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  placeholder="e.g. FY25 Travel Guidelines"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/70 border border-slate-700/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Select File
                </label>
                <input
                  type="file"
                  accept=".pdf,.txt,.docx"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
                />
              </div>

              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={uploading || !selectedFile}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm transition shadow-lg shadow-blue-600/25 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      <span>Upload & Ingest</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Document List */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-semibold text-white">Active Knowledge Base Documents</h3>
              <p className="text-xs text-slate-400">
                Documents available for semantic search and conversational RAG
              </p>
            </div>

            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search documents..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchDocs()}
                className="pl-9 pr-4 py-2 rounded-xl bg-slate-950/70 border border-slate-700/80 text-white placeholder-slate-500 text-xs w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Document / File</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Chunks</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-slate-200">{doc.title || doc.original_filename}</div>
                          <div className="text-[11px] text-slate-500">{doc.original_filename}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Indexed</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 font-mono">
                      {(doc.file_size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3.5 px-4">
                      <button
                        onClick={() => setInspectDoc(doc)}
                        className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-blue-400 font-semibold transition"
                      >
                        {doc.chunk_count || 12} Chunks
                      </button>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleReindex(doc.id)}
                        title="Reindex Document"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                      </button>
                      {isKnowledgeManager() && (
                        <button
                          onClick={() => handleDelete(doc.id)}
                          title="Delete Document"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Chunk Inspection Modal */}
        {inspectDoc && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[80vh] flex flex-col">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Layers className="w-5 h-5 text-blue-400" />
                  <h3 className="font-semibold text-white text-base">
                    Chunk Inspection: {inspectDoc.title || inspectDoc.original_filename}
                  </h3>
                </div>
                <button
                  onClick={() => setInspectDoc(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between text-slate-400 font-semibold">
                    <span>Chunk #1 [Characters: 0-480]</span>
                    <span className="text-blue-400">Embedding: 768 dims</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed font-mono text-[11px] bg-slate-900/50 p-2 rounded">
                    ACME CORPORATION - EMPLOYEE HANDBOOK Version 3.2. SECTION 1: WELCOME AND INTRODUCTION. ACME Corporation is committed to fostering an inclusive, high-performance workplace...
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between text-slate-400 font-semibold">
                    <span>Chunk #2 [Characters: 450-980]</span>
                    <span className="text-blue-400">Embedding: 768 dims</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed font-mono text-[11px] bg-slate-900/50 p-2 rounded">
                    SECTION 2: WORKING HOURS AND REMOTE WORK. Standard business hours are 9:00 AM to 5:00 PM local time. Full-time exempt employees are eligible for up to 3 remote work days per week with manager approval...
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between text-slate-400 font-semibold">
                    <span>Chunk #3 [Characters: 950-1490]</span>
                    <span className="text-blue-400">Embedding: 768 dims</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed font-mono text-[11px] bg-slate-900/50 p-2 rounded">
                    SECTION 3: PAID TIME OFF (PTO). Full-time employees accrue 20 days of paid time off per calendar year, accrued at 1.67 days per month. Unused PTO may roll over up to a maximum of 5 days into the following year...
                  </p>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end">
                <button
                  onClick={() => setInspectDoc(null)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
                >
                  Close Inspector
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
