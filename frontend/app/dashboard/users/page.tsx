'use client';

import { useState } from 'react';
import Header from '@/components/Header';
import { useAuthStore } from '@/lib/auth-store';
import { api, UserItem } from '@/lib/api';
import {
  Users,
  UserPlus,
  ShieldCheck,
  ShieldAlert,
  UserCheck,
  CheckCircle2,
  XCircle,
  MoreVertical,
  Plus,
  X,
  Lock,
} from 'lucide-react';

export default function UserManagementPage() {
  const { token, isAdmin } = useAuthStore();
  const [users, setUsers] = useState<UserItem[]>([
    {
      id: 'usr-1',
      email: 'admin@ekia.local',
      full_name: 'Enterprise Admin',
      role: 'admin',
      is_active: true,
      created_at: '2024-01-01T08:00:00Z',
    },
    {
      id: 'usr-2',
      email: 'km@ekia.local',
      full_name: 'Knowledge Lead',
      role: 'knowledge_manager',
      is_active: true,
      created_at: '2024-01-02T09:30:00Z',
    },
    {
      id: 'usr-3',
      email: 'employee@ekia.local',
      full_name: 'Decision Science Analyst',
      role: 'employee',
      is_active: true,
      created_at: '2024-01-03T11:15:00Z',
    },
  ]);

  const [showAddModal, setShowAddModal] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState('employee');
  const [newPassword, setNewPassword] = useState('TempPass123!');

  const handleAddUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail || !newName) return;

    const newUser: UserItem = {
      id: `usr-${Date.now()}`,
      email: newEmail,
      full_name: newName,
      role: newRole,
      is_active: true,
      created_at: new Date().toISOString(),
    };

    setUsers((prev) => [...prev, newUser]);
    setShowAddModal(false);
    setNewEmail('');
    setNewName('');
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <ShieldCheck className="w-3 h-3" />
            <span>Admin</span>
          </span>
        );
      case 'knowledge_manager':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <ShieldCheck className="w-3 h-3" />
            <span>Knowledge Manager</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <UserCheck className="w-3 h-3" />
            <span>Employee</span>
          </span>
        );
    }
  };

  return (
    <>
      <Header
        title="Identity & Access Governance"
        subtitle="Role-Based Access Control (RBAC) and user administration"
      />

      <main className="p-8 max-w-7xl mx-auto space-y-8 flex-1">
        {/* Top Action Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-white">Enterprise Directory</h2>
            <p className="text-xs text-slate-400">
              Manage team members, assign security scopes, and monitor access credentials
            </p>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/25 transition"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Enterprise User</span>
          </button>
        </div>

        {/* Users Table */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Name / Identity</th>
                  <th className="py-3 px-4">Corporate Email</th>
                  <th className="py-3 px-4">Assigned Role</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4 font-semibold text-slate-200">
                      {u.full_name}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">{u.email}</td>
                    <td className="py-3.5 px-4">{getRoleBadge(u.role)}</td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Active</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button className="text-xs text-blue-400 hover:underline">
                        Edit Role
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* RBAC Permission Matrix */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-4">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-white">RBAC Permission Matrix</h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border border-slate-800 rounded-xl overflow-hidden">
              <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Capability</th>
                  <th className="py-3 px-4 text-center">Employee</th>
                  <th className="py-3 px-4 text-center">Knowledge Manager</th>
                  <th className="py-3 px-4 text-center">Admin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                <tr>
                  <td className="py-3 px-4 font-medium">Ask RAG Knowledge Chat</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-medium">Vector Search Diagnostic Lab</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-medium">Execute Allowlisted Agent Tools</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-medium">Upload & Reindex Documents</td>
                  <td className="py-3 px-4 text-center text-slate-600">✗</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-medium">Trigger RAG Evaluation Suite</td>
                  <td className="py-3 px-4 text-center text-slate-600">✗</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-medium">Manage Users & Security Grants</td>
                  <td className="py-3 px-4 text-center text-slate-600">✗</td>
                  <td className="py-3 px-4 text-center text-slate-600">✗</td>
                  <td className="py-3 px-4 text-center text-emerald-400">✓</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Add User Modal */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h3 className="font-semibold text-white text-sm">Add New Enterprise User</h3>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleAddUser} className="space-y-4 text-xs">
                <div>
                  <label className="block uppercase tracking-wider font-semibold text-slate-400 mb-1">
                    Full Name
                  </label>
                  <input
                    type="text"
                    required
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. Alex Rivera"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block uppercase tracking-wider font-semibold text-slate-400 mb-1">
                    Corporate Email
                  </label>
                  <input
                    type="email"
                    required
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="alex.rivera@company.com"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block uppercase tracking-wider font-semibold text-slate-400 mb-1">
                    Role Assignment
                  </label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="employee">Employee (Chat & Tools)</option>
                    <option value="knowledge_manager">Knowledge Manager (Docs & Evals)</option>
                    <option value="admin">Admin (Full Control)</option>
                  </select>
                </div>

                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 font-semibold hover:bg-slate-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-500 shadow-md shadow-blue-600/25"
                  >
                    Create User
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
