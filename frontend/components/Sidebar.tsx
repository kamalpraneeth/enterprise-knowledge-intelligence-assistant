'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Brain,
  MessageSquare,
  FileText,
  Search,
  Wrench,
  BarChart2,
  Users,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth, isAdmin } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    router.push('/auth/login');
  };

  const navItems = [
    {
      name: 'Overview',
      href: '/dashboard',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      name: 'Knowledge Chat',
      href: '/dashboard/chat',
      icon: MessageSquare,
      badge: 'RAG',
    },
    {
      name: 'Document Ingestion',
      href: '/dashboard/documents',
      icon: FileText,
      badge: null,
    },
    {
      name: 'Vector Search Lab',
      href: '/dashboard/retrieval',
      icon: Search,
      badge: null,
    },
    {
      name: 'Agentic Tools',
      href: '/dashboard/tools',
      icon: Wrench,
      badge: 'Agent',
    },
    {
      name: 'RAG Evaluation',
      href: '/dashboard/evaluations',
      icon: BarChart2,
      badge: 'Metrics',
    },
    ...(isAdmin()
      ? [
          {
            name: 'User Management',
            href: '/dashboard/users',
            icon: Users,
            badge: 'Admin',
          },
        ]
      : []),
  ];

  const getRoleColor = (role?: string) => {
    switch (role) {
      case 'admin':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'knowledge_manager':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      default:
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    }
  };

  return (
    <aside className="w-64 bg-[hsl(222,47%,7%)] border-r border-slate-800 flex flex-col h-screen fixed left-0 top-0 z-30 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800/80">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-md shadow-blue-600/30">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-base tracking-tight text-white">EKIA</span>
            <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
              v2.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400 truncate max-w-[130px]">Enterprise Intelligence</p>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Core Workflows
        </div>
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                isActive
                  ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon
                  className={`w-4 h-4 transition-colors ${
                    isActive ? 'text-blue-400' : 'text-slate-400 group-hover:text-slate-200'
                  }`}
                />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-md font-semibold ${
                    isActive
                      ? 'bg-blue-500/20 text-blue-300'
                      : 'bg-slate-800 text-slate-400 group-hover:text-slate-300'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </div>

      {/* Architecture Tag */}
      <div className="p-3 mx-3 my-2 rounded-xl bg-slate-900/60 border border-slate-800/80">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-300 mb-1">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>Enterprise AI Portfolio</span>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          Full-Stack Generative AI & Decision Science System
        </p>
      </div>

      {/* User Footer Profile */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-900/50 border border-slate-800/60">
          <div className="min-w-0 flex-1 mr-2">
            <div className="text-xs font-semibold text-white truncate">
              {user?.full_name || 'Enterprise User'}
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span
                className={`text-[9px] uppercase px-1.5 py-0.5 rounded border font-bold ${getRoleColor(
                  user?.role
                )}`}
              >
                {user?.role?.replace('_', ' ') || 'employee'}
              </span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
