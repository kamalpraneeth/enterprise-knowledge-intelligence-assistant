'use client';

import { useState, useEffect } from 'react';
import { Activity, Cpu, Database, ShieldCheck, Sparkles, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';

export default function Header({ title, subtitle }: { title: string; subtitle?: string }) {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    api.health
      .check()
      .then(() => {
        if (isMounted) setApiOnline(true);
      })
      .catch(() => {
        if (isMounted) setApiOnline(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <header className="h-16 border-b border-slate-800 bg-[hsl(222,47%,7%)]/80 backdrop-blur sticky top-0 z-20 px-8 flex items-center justify-between">
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-white">{title}</h1>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Model Indicator Badge */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-700/80 text-xs">
          <Cpu className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-slate-400">LLM:</span>
          <span className="text-slate-200 font-medium">Google Gemini 1.5</span>
        </div>

        {/* Vector DB Indicator */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-700/80 text-xs">
          <Database className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-slate-400">Vector Store:</span>
          <span className="text-slate-200 font-medium">pgvector (HNSW)</span>
        </div>

        {/* API Health Status Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-700/80 text-xs">
          <div
            className={`w-2 h-2 rounded-full ${
              apiOnline === true
                ? 'bg-emerald-400 shadow-sm shadow-emerald-400'
                : apiOnline === false
                ? 'bg-rose-400'
                : 'bg-amber-400 animate-pulse'
            }`}
          />
          <span className="text-slate-300 font-medium">
            {apiOnline === true ? 'Backend Online' : apiOnline === false ? 'Mock / Standby' : 'Connecting'}
          </span>
        </div>
      </div>
    </header>
  );
}
