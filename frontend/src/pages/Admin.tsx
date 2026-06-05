import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { adminApi, referralApi } from '@/lib/api'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import {
  Users, MessageCircle, AlertTriangle, Crown, Shield,
  RefreshCw, Eye, Ban, Trash2, CheckCircle,
  TrendingUp, Activity, Clock, Flag, DollarSign, Download, Youtube,
  type LucideIcon,
} from 'lucide-react'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const ADMIN_EMAIL = 'ravenbishop1987@gmail.com'

type Tab = 'overview' | 'conversations' | 'users' | 'moderation' | 'revenue' | 'referral'

interface Metrics {
  users: { total: number; free: number; credits: number; premium: number; blocked: number; new_today: number; new_week: number; new_month: number }
  conversations: { total: number; today: number; this_month: number }
  revenue: { mrr: number; premium_subscribers: number }
  safety: { flags_total: number; flags_open: number; tier2_open: number; tier3_open: number }
}

function KpiCard({ icon: Icon, label, value, sub, color = 'sage' }: {
  icon: LucideIcon
  label: string
  value: string | number
  sub?: string
  color?: string
}) {
  const colorMap: Record<string, string> = {
    sage: 'bg-sage-100 text-sage-600',
    amber: 'bg-amber-100 text-amber-600',
    red: 'bg-red-100 text-red-600',
    blue: 'bg-blue-100 text-blue-600',
  }
  return (
    <div className="bg-white rounded-2xl p-5 shadow-soft">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${colorMap[color] || colorMap.sage}`}>
          <Icon size={17} />
        </div>
      </div>
      <p className="text-2xl font-bold text-charcoal-900">{value}</p>
      <p className="text-sm font-medium text-charcoal-700 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-stone-400 mt-1">{sub}</p>}
    </div>
  )
}

function TierBadge({ tier }: { tier: string }) {
  const map: Record<string, string> = {
    free: 'bg-stone-100 text-stone-600',
    credits: 'bg-sage-100 text-sage-700',
    premium: 'bg-amber-100 text-amber-700',
    blocked: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${map[tier] || 'bg-stone-100 text-stone-500'}`}>
      {tier}
    </span>
  )
}

function FlagBadge({ tier }: { tier: string | null }) {
  if (!tier) return <span className="text-xs text-stone-400">—</span>
  const map: Record<string, string> = {
    tier1: 'bg-yellow-100 text-yellow-700',
    tier2: 'bg-orange-100 text-orange-700',
    tier3: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${map[tier] || 'bg-stone-100'}`}>
      {tier.replace('tier', 'T')}
    </span>
  )
}

// ── Overview ──────────────────────────────────────────────────────────────────

function Overview({ metrics }: { metrics: Metrics | null }) {
  const [breakdown, setBreakdown] = useState<any | null>(null)

  useEffect(() => {
    adminApi.revenueBreakdown()
      .then(r => setBreakdown(r.data))
      .catch(() => {})
  }, [])

  if (!metrics) return <div className="text-stone-400 text-sm p-8">Loading metrics…</div>
  const { users, conversations, safety } = metrics

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-4">Users</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard icon={Users} label="Total Users" value={users.total} sub={`+${users.new_today} today`} />
          <KpiCard icon={Crown} label="Premium" value={users.premium} sub={`${users.new_week} new this week`} color="amber" />
          <KpiCard icon={Activity} label="New This Month" value={users.new_month} color="blue" />
          <KpiCard icon={Ban} label="Blocked" value={users.blocked} color="red" />
        </div>
      </div>

      {/* Revenue breakdown */}
      <div>
        <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-4">Revenue breakdown</h3>
        {breakdown ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Subscriptions */}
            <div className="bg-white rounded-2xl p-5 shadow-soft">
              <div className="flex items-center gap-2 mb-3">
                <Crown size={15} className="text-amber-500" />
                <span className="text-sm font-semibold text-charcoal-800">Premium subscriptions</span>
              </div>
              <p className="text-2xl font-bold text-charcoal-900">${breakdown.subscriptions.revenue.toFixed(2)}</p>
              <p className="text-xs text-stone-400 mt-1">{breakdown.subscriptions.count} subscribers × $9.99/mo</p>
              <div className="mt-3 pt-3 border-t border-stone-100">
                <p className="text-xs text-stone-500">MRR <span className="font-semibold text-sage-600">${breakdown.subscriptions.mrr.toFixed(2)}</span></p>
              </div>
            </div>

            {/* Credits */}
            <div className="bg-white rounded-2xl p-5 shadow-soft">
              <div className="flex items-center gap-2 mb-3">
                <DollarSign size={15} className="text-sage-500" />
                <span className="text-sm font-semibold text-charcoal-800">Credits purchases</span>
              </div>
              <p className="text-2xl font-bold text-charcoal-900">${breakdown.credits.revenue.toFixed(2)}</p>
              <p className="text-xs text-stone-400 mt-1">{breakdown.credits.count} credits users × $2.99</p>
              <div className="mt-3 pt-3 border-t border-stone-100">
                <p className="text-xs text-stone-500">One-time purchases</p>
              </div>
            </div>

            {/* Gifts */}
            <div className="bg-white rounded-2xl p-5 shadow-soft">
              <div className="flex items-center gap-2 mb-3">
                <Flag size={15} className="text-rose-400" />
                <span className="text-sm font-semibold text-charcoal-800">Gifts</span>
              </div>
              <p className="text-2xl font-bold text-charcoal-900">${breakdown.gifts.total_revenue.toFixed(2)}</p>
              <p className="text-xs text-stone-400 mt-1">{breakdown.gifts.total_count} gift{breakdown.gifts.total_count !== 1 ? 's' : ''} sent</p>
              {breakdown.gifts.breakdown.length > 0 && (
                <div className="mt-3 pt-3 border-t border-stone-100 space-y-1">
                  {breakdown.gifts.breakdown.map((g: any) => (
                    <div key={g.label} className="flex justify-between text-xs text-stone-500">
                      <span>{g.label} ×{g.count}</span>
                      <span className="font-medium">${g.revenue.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-stone-400 text-sm">Loading breakdown…</div>
        )}

        {breakdown && (
          <div className="mt-4 bg-charcoal-900 rounded-2xl p-5 flex items-center justify-between">
            <div>
              <p className="text-stone-400 text-xs mb-1">Estimated total revenue</p>
              <p className="text-white text-xs">Subscriptions + Credits + Gifts</p>
            </div>
            <p className="text-2xl font-bold text-sage-400">${breakdown.total_estimated_revenue.toFixed(2)}</p>
          </div>
        )}
      </div>

      {/* User tier bar */}
      <div className="bg-white rounded-2xl p-5 shadow-soft">
        <p className="text-xs text-stone-400 mb-3">User tier breakdown</p>
        <div className="space-y-2">
          {[
            { label: 'Free', count: users.free, color: 'bg-stone-300' },
            { label: 'Credits', count: users.credits, color: 'bg-sage-400' },
            { label: 'Premium', count: users.premium, color: 'bg-amber-400' },
          ].map(({ label, count, color }) => (
            <div key={label} className="flex items-center gap-3">
              <span className="text-xs text-stone-500 w-14">{label}</span>
              <div className="flex-1 bg-stone-100 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full rounded-full ${color}`}
                  style={{ width: `${users.total ? Math.round((count / users.total) * 100) : 0}%` }}
                />
              </div>
              <span className="text-xs text-stone-500 w-6 text-right">{count}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-4">Conversations</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <KpiCard icon={MessageCircle} label="Total" value={conversations.total} />
          <KpiCard icon={Clock} label="Today" value={conversations.today} />
          <KpiCard icon={Activity} label="This Month" value={conversations.this_month} />
        </div>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-4">Safety</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard icon={Flag} label="All-Time Flags" value={safety.flags_total} />
          <KpiCard icon={AlertTriangle} label="Open Flags" value={safety.flags_open} color={safety.flags_open > 0 ? 'red' : 'sage'} />
          <KpiCard icon={Shield} label="Tier 2 Open" value={safety.tier2_open} color={safety.tier2_open > 0 ? 'amber' : 'sage'} />
          <KpiCard icon={AlertTriangle} label="Tier 3 Open" value={safety.tier3_open} color={safety.tier3_open > 0 ? 'red' : 'sage'} />
        </div>
        {safety.tier3_open > 0 && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-3">
            <AlertTriangle size={18} className="text-red-500 shrink-0" />
            <p className="text-sm text-red-700 font-medium">
              {safety.tier3_open} Tier 3 (imminent risk) flag{safety.tier3_open > 1 ? 's' : ''} require immediate review.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Conversations ─────────────────────────────────────────────────────────────

function ConversationsTab() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [flaggedOnly, setFlaggedOnly] = useState(false)
  const [detail, setDetail] = useState<any | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await adminApi.listConversations({ limit: 100, flagged_only: flaggedOnly })
      setRows(data)
    } catch { toast.error('Failed to load conversations') }
    finally { setLoading(false) }
  }, [flaggedOnly])

  useEffect(() => { load() }, [load])

  const openDetail = async (id: string) => {
    try {
      const { data } = await adminApi.getConversation(id)
      setDetail(data)
    } catch { toast.error('Failed to load conversation') }
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-5">
        <label className="flex items-center gap-2 text-sm text-stone-600 cursor-pointer">
          <input type="checkbox" checked={flaggedOnly} onChange={e => setFlaggedOnly(e.target.checked)} className="rounded" />
          Show flagged only
        </label>
        <button onClick={load} className="ml-auto btn-ghost text-sm flex items-center gap-1">
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {loading ? (
        <p className="text-stone-400 text-sm">Loading…</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-stone-200">
          <table className="w-full text-sm">
            <thead className="bg-stone-50 text-stone-500 text-xs uppercase tracking-wide">
              <tr>
                {['User', 'Tier', 'Title', 'Date', 'Msgs', 'Flag', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {rows.map(r => (
                <tr key={r.conversation_id} className="hover:bg-stone-50">
                  <td className="px-4 py-3 text-charcoal-800 font-medium">{r.user_email}</td>
                  <td className="px-4 py-3"><TierBadge tier={r.user_tier} /></td>
                  <td className="px-4 py-3 text-stone-500 max-w-[200px] truncate">{r.title || '—'}</td>
                  <td className="px-4 py-3 text-stone-400 whitespace-nowrap">
                    {r.date_started ? format(new Date(r.date_started), 'MMM d, h:mm a') : '—'}
                  </td>
                  <td className="px-4 py-3 text-stone-600">{r.message_count}</td>
                  <td className="px-4 py-3"><FlagBadge tier={r.flag_tier} /></td>
                  <td className="px-4 py-3">
                    <button onClick={() => openDetail(r.conversation_id)} className="text-sage-600 hover:text-sage-800">
                      <Eye size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && <p className="text-center text-stone-400 text-sm py-8">No conversations found.</p>}
        </div>
      )}

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center p-6 overflow-y-auto" onClick={() => setDetail(null)}>
          <div className="bg-white rounded-3xl shadow-xl max-w-2xl w-full p-6 mt-10" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-charcoal-800">{detail.title || 'Conversation'}</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={async () => {
                    try {
                      const { data } = await adminApi.exportConversation(detail.conversation_id)
                      downloadBlob(data, `Conversation_${detail.conversation_id.slice(0,8)}.pdf`)
                    } catch { toast.error('Export failed') }
                  }}
                  className="btn-ghost text-xs flex items-center gap-1"
                >
                  <Download size={12} /> PDF
                </button>
                <button onClick={() => setDetail(null)} className="text-stone-400 hover:text-stone-600 text-lg">×</button>
              </div>
            </div>
            <p className="text-xs text-stone-400 mb-4">{detail.user_email} · {detail.user_tier}</p>
            {detail.safety_flags?.length > 0 && (
              <div className="mb-4 bg-red-50 rounded-xl p-3 text-sm text-red-700">
                ⚠️ {detail.safety_flags.length} safety flag{detail.safety_flags.length > 1 ? 's' : ''} on this conversation
              </div>
            )}
            <div className="space-y-3 max-h-[60vh] overflow-y-auto">
              {(detail.messages || []).map((m: any, i: number) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`rounded-2xl px-4 py-2 text-sm max-w-[80%] ${m.role === 'user' ? 'bg-charcoal-800 text-white' : 'bg-stone-100 text-charcoal-800'}`}>
                    <p className="whitespace-pre-wrap">{m.content}</p>
                    <p className="text-[10px] opacity-50 mt-1">{m.timestamp ? format(new Date(m.timestamp), 'h:mm a') : ''}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Users ─────────────────────────────────────────────────────────────────────

function UsersTab() {
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [tierFilter, setTierFilter] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await adminApi.listUsers({ limit: 100, tier: tierFilter || undefined })
      setUsers(data)
    } catch { toast.error('Failed to load users') }
    finally { setLoading(false) }
  }, [tierFilter])

  useEffect(() => { load() }, [load])

  const handleBlock = async (userId: string, currentTier: string) => {
    try {
      if (currentTier === 'blocked') {
        await adminApi.unblockUser(userId)
        toast.success('User unblocked')
      } else {
        await adminApi.blockUser(userId)
        toast.success('User blocked')
      }
      load()
    } catch { toast.error('Action failed') }
  }

  const handleDelete = async (userId: string, email: string) => {
    if (!confirm(`Permanently delete all data for ${email}? This cannot be undone.`)) return
    try {
      await adminApi.deleteUser(userId)
      toast.success('User deleted')
      load()
    } catch { toast.error('Delete failed') }
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <select
          value={tierFilter}
          onChange={e => setTierFilter(e.target.value)}
          className="text-sm border border-stone-200 rounded-xl px-3 py-1.5 bg-white text-charcoal-800"
        >
          <option value="">All tiers</option>
          <option value="free">Free</option>
          <option value="credits">Credits</option>
          <option value="premium">Premium</option>
          <option value="blocked">Blocked</option>
        </select>
        <button onClick={load} className="ml-auto btn-ghost text-sm flex items-center gap-1">
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {loading ? <p className="text-stone-400 text-sm">Loading…</p> : (
        <div className="overflow-x-auto rounded-2xl border border-stone-200">
          <table className="w-full text-sm">
            <thead className="bg-stone-50 text-stone-500 text-xs uppercase tracking-wide">
              <tr>
                {['Email', 'Tier', 'Joined', 'Convos', 'Flags', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {users.map(u => (
                <tr key={u.user_id} className="hover:bg-stone-50">
                  <td className="px-4 py-3 font-medium text-charcoal-800">{u.email}</td>
                  <td className="px-4 py-3"><TierBadge tier={u.tier} /></td>
                  <td className="px-4 py-3 text-stone-400 whitespace-nowrap">
                    {u.created_at ? format(new Date(u.created_at), 'MMM d, yyyy') : '—'}
                  </td>
                  <td className="px-4 py-3 text-stone-600">{u.conversation_count}</td>
                  <td className="px-4 py-3">
                    {u.flag_count > 0 ? (
                      <span className="text-xs font-semibold text-red-600">{u.flag_count}</span>
                    ) : (
                      <span className="text-stone-300">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleBlock(u.user_id, u.tier)}
                        className={`p-1.5 rounded-lg transition-colors ${u.tier === 'blocked' ? 'bg-stone-100 text-stone-500 hover:bg-stone-200' : 'bg-red-50 text-red-500 hover:bg-red-100'}`}
                        title={u.tier === 'blocked' ? 'Unblock' : 'Block'}
                      >
                        <Ban size={13} />
                      </button>
                      <button
                        onClick={() => handleDelete(u.user_id, u.email)}
                        className="p-1.5 rounded-lg bg-red-50 text-red-500 hover:bg-red-100 transition-colors"
                        title="Delete user data"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && <p className="text-center text-stone-400 text-sm py-8">No users found.</p>}
        </div>
      )}
    </div>
  )
}

// ── Moderation ────────────────────────────────────────────────────────────────

function ModerationTab() {
  const [flags, setFlags] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showResolved, setShowResolved] = useState(false)
  const [detail, setDetail] = useState<any | null>(null)
  const [exporting, setExporting] = useState(false)

  const exportReport = async () => {
    setExporting(true)
    try {
      const { data } = await adminApi.exportModerationReport(30)
      downloadBlob(data, `Sophie_Moderation_${new Date().toISOString().slice(0, 10)}.pdf`)
    } catch { toast.error('Export failed') }
    finally { setExporting(false) }
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await adminApi.getFlags({ limit: 100, resolved: showResolved ? undefined : false })
      setFlags(data)
    } catch { toast.error('Failed to load flags') }
    finally { setLoading(false) }
  }, [showResolved])

  useEffect(() => { load() }, [load])

  const resolveFlag = async (flagId: string) => {
    try {
      await adminApi.resolveFlag(flagId, 'reviewed')
      toast.success('Flag resolved')
      load()
    } catch { toast.error('Failed to resolve') }
  }

  const openConversation = async (convoId: string) => {
    if (!convoId) return
    try {
      const { data } = await adminApi.getConversation(convoId)
      setDetail(data)
    } catch { toast.error('Failed to load conversation') }
  }

  const tierColor: Record<string, string> = {
    tier1: 'border-l-yellow-400 bg-yellow-50',
    tier2: 'border-l-orange-400 bg-orange-50',
    tier3: 'border-l-red-500 bg-red-50',
  }
  const tierLabel: Record<string, string> = {
    tier1: 'Tier 1 — Ideation',
    tier2: 'Tier 2 — Active Harm',
    tier3: 'Tier 3 — IMMINENT RISK',
  }

  return (
    <div>
      {/* Crisis reminder */}
      <div className="bg-sage-50 border border-sage-200 rounded-2xl p-4 mb-6 text-sm text-sage-800">
        <p className="font-semibold mb-1">Moderation policy</p>
        <p>Tier 1: Log + crisis resources shown. Tier 2: Conversation paused + mandatory resources. Tier 3: Conversation blocked immediately. All flags require your manual review.</p>
      </div>

      <div className="flex items-center gap-4 mb-5 flex-wrap">
        <label className="flex items-center gap-2 text-sm text-stone-600 cursor-pointer">
          <input type="checkbox" checked={showResolved} onChange={e => setShowResolved(e.target.checked)} className="rounded" />
          Show resolved
        </label>
        <button onClick={load} className="btn-ghost text-sm flex items-center gap-1">
          <RefreshCw size={13} /> Refresh
        </button>
        <button onClick={exportReport} disabled={exporting} className="ml-auto btn-ghost text-sm flex items-center gap-1">
          <Download size={13} /> {exporting ? 'Exporting…' : 'Export PDF (30 days)'}
        </button>
      </div>

      {loading ? <p className="text-stone-400 text-sm">Loading…</p> : (
        <div className="space-y-3">
          {flags.map(f => (
            <div key={f.flag_id} className={`rounded-2xl border-l-4 p-4 ${tierColor[f.risk_level] || 'bg-stone-50 border-l-stone-300'} ${f.resolved ? 'opacity-50' : ''}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs font-bold uppercase tracking-wide text-stone-700">
                      {tierLabel[f.risk_level] || f.risk_level}
                    </span>
                    {f.resolved && <span className="text-xs text-green-600 font-medium">✓ Resolved</span>}
                  </div>
                  <p className="text-sm text-stone-700 mb-1">
                    <span className="font-medium">{f.user_email}</span> · {f.created_at ? format(new Date(f.created_at), 'MMM d, h:mm a') : '—'}
                  </p>
                  {f.trigger_text && (
                    <p className="text-xs text-stone-500 italic mb-1">Trigger: "{f.trigger_text}"</p>
                  )}
                  {f.conversation_snippet && (
                    <p className="text-xs text-stone-500 truncate">"{f.conversation_snippet}"</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {f.conversation_id && (
                    <button
                      onClick={() => openConversation(f.conversation_id)}
                      className="p-1.5 rounded-lg bg-white border border-stone-200 text-stone-500 hover:text-sage-600 transition-colors"
                      title="View conversation"
                    >
                      <Eye size={13} />
                    </button>
                  )}
                  {!f.resolved && (
                    <button
                      onClick={() => resolveFlag(f.flag_id)}
                      className="p-1.5 rounded-lg bg-white border border-stone-200 text-stone-500 hover:text-green-600 transition-colors"
                      title="Mark resolved"
                    >
                      <CheckCircle size={13} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
          {flags.length === 0 && (
            <div className="text-center py-12">
              <Shield size={32} className="text-sage-300 mx-auto mb-3" />
              <p className="text-stone-400 text-sm">No open flags. Stay vigilant.</p>
            </div>
          )}
        </div>
      )}

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center p-6 overflow-y-auto" onClick={() => setDetail(null)}>
          <div className="bg-white rounded-3xl shadow-xl max-w-2xl w-full p-6 mt-10" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-charcoal-800">{detail.title || 'Conversation'}</h3>
              <button onClick={() => setDetail(null)} className="text-stone-400 hover:text-stone-600 text-lg">×</button>
            </div>
            <p className="text-xs text-stone-400 mb-4">{detail.user_email}</p>
            <div className="space-y-3 max-h-[60vh] overflow-y-auto">
              {(detail.messages || []).map((m: any, i: number) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`rounded-2xl px-4 py-2 text-sm max-w-[80%] ${m.role === 'user' ? 'bg-charcoal-800 text-white' : 'bg-stone-100 text-charcoal-800'}`}>
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Revenue ───────────────────────────────────────────────────────────────────

function RevenueTab() {
  const [data, setData] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data: r } = await adminApi.revenue()
      setData(r)
    } catch { toast.error('Failed to load revenue data') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <p className="text-stone-400 text-sm">Loading Stripe data…</p>

  if (data?.error) {
    return (
      <div className="bg-red-50 rounded-2xl p-4 text-sm text-red-700">
        Stripe error: {data.error}
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard icon={TrendingUp} label="MRR" value={`$${(data?.mrr ?? 0).toFixed(2)}`} sub="active subscriptions" color="amber" />
        <KpiCard icon={DollarSign} label="Revenue Today" value={`$${(data?.revenue_today ?? 0).toFixed(2)}`} />
        <KpiCard icon={DollarSign} label="Revenue This Month" value={`$${(data?.revenue_month ?? 0).toFixed(2)}`} color="sage" />
        <KpiCard icon={Crown} label="Active Subscribers" value={data?.premium_subscribers ?? 0} color="amber" />
      </div>

      <div className="bg-white rounded-2xl p-5 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-charcoal-800">All-time revenue</h3>
          <span className="text-2xl font-bold text-sage-600">${(data?.revenue_alltime ?? 0).toFixed(2)}</span>
        </div>
        <p className="text-xs text-stone-400">Based on last 100 charges from Stripe. For full history, check your Stripe dashboard.</p>
      </div>

      {data?.recent_transactions?.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-4">Recent Transactions (this month)</h3>
          <div className="overflow-x-auto rounded-2xl border border-stone-200">
            <table className="w-full text-sm">
              <thead className="bg-stone-50 text-stone-500 text-xs uppercase tracking-wide">
                <tr>
                  {['Date', 'Amount', 'Customer', 'Description'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {data.recent_transactions.map((t: any) => (
                  <tr key={t.id} className="hover:bg-stone-50">
                    <td className="px-4 py-3 text-stone-400 whitespace-nowrap">
                      {t.date ? format(new Date(t.date), 'MMM d, h:mm a') : '—'}
                    </td>
                    <td className="px-4 py-3 font-semibold text-sage-700">${t.amount.toFixed(2)}</td>
                    <td className="px-4 py-3 text-charcoal-700">{t.customer_email || '—'}</td>
                    <td className="px-4 py-3 text-stone-500 max-w-[200px] truncate">{t.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Referral ──────────────────────────────────────────────────────────────────

function slugify(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 60)
}

function ReferralTab() {
  const [stats, setStats] = useState<any | null>(null)
  const [videos, setVideos] = useState<any[]>([])
  const [trends, setTrends] = useState<any[]>([])
  const [slugs, setSlugs] = useState<{ slug: string; title: string; created_at: string }[]>([])
  const [loading, setLoading] = useState(true)

  // Add video form state
  const [newTitle, setNewTitle] = useState('')
  const [newSlug, setNewSlug] = useState('')
  const [slugLocked, setSlugLocked] = useState(false)
  const [adding, setAdding] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [sRes, vRes, tRes, slRes] = await Promise.all([
        referralApi.adminStats(),
        referralApi.adminVideos(),
        referralApi.adminTrends(30),
        referralApi.listSlugs(),
      ])
      setStats(sRes.data)
      setVideos(vRes.data)
      setTrends(tRes.data)
      setSlugs(slRes.data)
    } catch { toast.error('Failed to load referral data') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleTitleChange = (val: string) => {
    setNewTitle(val)
    if (!slugLocked) setNewSlug(slugify(val))
  }

  const handleAddVideo = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setAdding(true)
    try {
      await referralApi.addSlug(newTitle.trim(), newSlug.trim() || undefined)
      toast.success('Video added!')
      setNewTitle('')
      setNewSlug('')
      setSlugLocked(false)
      await load()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to add video')
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (slug: string) => {
    if (!confirm(`Remove /yt/${slug}? This won't delete click history.`)) return
    try {
      await referralApi.deleteSlug(slug)
      toast.success('Removed')
      setSlugs(prev => prev.filter(s => s.slug !== slug))
    } catch { toast.error('Failed to remove') }
  }

  const copyUrl = (slug: string) => {
    navigator.clipboard.writeText(`sophieparker.online/yt/${slug}`)
    setCopied(slug)
    setTimeout(() => setCopied(null), 2000)
  }

  if (loading) return <p className="text-stone-400 text-sm">Loading referral data…</p>

  const topDay = trends.reduce((best, d) => d.clicks > (best?.clicks ?? 0) ? d : best, null)

  return (
    <div className="space-y-8">
      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard icon={Youtube} label="Total Clicks" value={stats?.total_clicks ?? 0} color="red" />
        <KpiCard icon={Users} label="YT Signups" value={stats?.total_signups ?? 0} sub={`+${stats?.new_signups_this_week ?? 0} this week`} />
        <KpiCard icon={Crown} label="YT Premium" value={stats?.total_premium_from_yt ?? 0} color="amber" />
        <KpiCard icon={TrendingUp} label="Conv. Rate" value={`${stats?.conversion_rate ?? 0}%`} sub="signups → premium" color="sage" />
        <KpiCard icon={DollarSign} label="MRR from YT" value={`$${stats?.mrr_from_yt ?? 0}`} color="sage" />
        <KpiCard icon={Activity} label="Best Day" value={topDay ? topDay.clicks : '—'} sub={topDay?.date} />
      </div>

      {/* ── Video management ── */}
      <div className="bg-white rounded-2xl p-6 shadow-soft">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-charcoal-800">YouTube Videos</h3>
          <button onClick={load} className="btn-ghost text-sm flex items-center gap-1"><RefreshCw size={12} /> Refresh</button>
        </div>

        {/* Add form */}
        <form onSubmit={handleAddVideo} className="flex flex-col sm:flex-row gap-3 mb-6 pb-6 border-b border-stone-100">
          <div className="flex-1 space-y-2">
            <input
              type="text"
              value={newTitle}
              onChange={e => handleTitleChange(e.target.value)}
              placeholder="Video title (e.g. Sleep With Sophie Ep 1)"
              className="input-base text-sm w-full"
              required
            />
            <div className="flex items-center gap-2">
              <span className="text-xs text-stone-400 shrink-0">sophieparker.online/yt/</span>
              <input
                type="text"
                value={newSlug}
                onChange={e => { setNewSlug(e.target.value); setSlugLocked(true) }}
                placeholder="auto-generated"
                className="input-base text-xs flex-1 font-mono"
              />
              {slugLocked && (
                <button type="button" onClick={() => { setNewSlug(slugify(newTitle)); setSlugLocked(false) }}
                  className="text-xs text-stone-400 hover:text-stone-600 shrink-0">reset</button>
              )}
            </div>
          </div>
          <button type="submit" disabled={adding || !newTitle.trim()} className="btn-primary text-sm shrink-0 h-fit self-end">
            {adding ? 'Adding…' : '+ Add video'}
          </button>
        </form>

        {/* Video list */}
        <div className="space-y-2">
          {slugs.map(s => (
            <div key={s.slug} className="flex items-center gap-3 py-2.5 px-3 rounded-xl hover:bg-stone-50 group">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-charcoal-800 truncate">{s.title}</p>
                <p className="text-xs text-stone-400 font-mono">/yt/{s.slug}</p>
              </div>
              <button
                onClick={() => copyUrl(s.slug)}
                className="text-xs px-3 py-1.5 rounded-lg border border-stone-200 bg-white text-stone-500 hover:text-sage-600 hover:border-sage-300 transition-colors shrink-0"
                title="Copy pinned comment URL"
              >
                {copied === s.slug ? '✓ Copied' : 'Copy URL'}
              </button>
              <button
                onClick={() => handleDelete(s.slug)}
                className="p-1.5 rounded-lg text-stone-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                title="Remove"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {slugs.length === 0 && <p className="text-stone-400 text-sm text-center py-4">No videos yet.</p>}
        </div>
      </div>

      {/* Per-video analytics table */}
      {videos.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-4">Performance by video</h3>
          <div className="overflow-x-auto rounded-2xl border border-stone-200">
            <table className="w-full text-sm">
              <thead className="bg-stone-50 text-stone-500 text-xs uppercase tracking-wide">
                <tr>
                  {['Video', 'Clicks', 'Signups', 'Click→Signup', 'Premium', 'Conv%', 'MRR'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {videos.map((v: any) => (
                  <tr key={v.video_slug} className="hover:bg-stone-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-charcoal-800 max-w-[220px] truncate">{v.video_title}</p>
                      <p className="text-[11px] text-stone-400 font-mono">/yt/{v.video_slug}</p>
                    </td>
                    <td className="px-4 py-3 text-stone-600">{v.clicks}</td>
                    <td className="px-4 py-3 text-stone-600">{v.signups}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${v.click_to_signup_rate >= 20 ? 'bg-sage-100 text-sage-700' : 'bg-stone-100 text-stone-600'}`}>
                        {v.click_to_signup_rate}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-stone-600">{v.premium_subs}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${v.conversion_rate >= 30 ? 'bg-amber-100 text-amber-700' : 'bg-stone-100 text-stone-600'}`}>
                        {v.conversion_rate}%
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold text-sage-700">${v.mrr}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 30-day chart */}
      {trends.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-4">Last 30 days — clicks &amp; signups</h3>
          <div className="bg-white rounded-2xl p-5 shadow-soft overflow-x-auto">
            <div className="flex items-end gap-1 h-24 min-w-[600px]">
              {trends.map((d: any) => {
                const maxClicks = Math.max(...trends.map((t: any) => t.clicks), 1)
                const heightPct = Math.round((d.clicks / maxClicks) * 100)
                return (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-0.5 group relative">
                    <div
                      className="w-full bg-red-200 hover:bg-red-400 transition-colors rounded-sm cursor-default"
                      style={{ height: `${Math.max(heightPct, 2)}%` }}
                      title={`${d.date}: ${d.clicks} clicks, ${d.signups} signups`}
                    />
                    {d.signups > 0 && (
                      <div className="absolute -top-4 w-full flex justify-center">
                        <span className="text-[9px] font-bold text-sage-600">+{d.signups}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
            <div className="flex justify-between mt-2 text-[10px] text-stone-400">
              <span>{trends[0]?.date}</span>
              <span>Red = clicks · Green = signups</span>
              <span>{trends[trends.length - 1]?.date}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Admin Page ───────────────────────────────────────────────────────────

export default function Admin() {
  const { user, isLoading } = useAuthStore()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('overview')
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [metricsLoading, setMetricsLoading] = useState(true)

  useEffect(() => {
    if (isLoading) return
    if (!user) { navigate('/login'); return }
    if (user.email !== ADMIN_EMAIL) { navigate('/'); return }
  }, [user, isLoading, navigate])

  useEffect(() => {
    if (!user || user.email !== ADMIN_EMAIL) return
    setMetricsLoading(true)
    adminApi.metrics()
      .then(r => setMetrics(r.data))
      .catch(() => toast.error('Failed to load metrics'))
      .finally(() => setMetricsLoading(false))
  }, [user])

  if (isLoading) return (
    <div className="min-h-screen bg-cream-100 flex items-center justify-center">
      <div className="typing-dots"><span /><span /><span /></div>
    </div>
  )
  if (!user || user.email !== ADMIN_EMAIL) return null

  const tabs: { id: Tab; label: string; icon: LucideIcon }[] = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'revenue', label: 'Revenue', icon: DollarSign },
    { id: 'referral', label: 'Referral', icon: Youtube },
    { id: 'conversations', label: 'Conversations', icon: MessageCircle },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'moderation', label: 'Moderation', icon: Shield },
  ]

  const openFlagCount = metrics?.safety.flags_open ?? 0

  return (
    <div className="min-h-screen bg-cream-100">
      {/* Header */}
      <div className="bg-white border-b border-stone-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="font-serif text-xl text-charcoal-900">Sophie Parker Admin</h1>
            <p className="text-xs text-stone-400">Internal dashboard · {user.email}</p>
          </div>
          <button onClick={() => navigate('/chat')} className="btn-ghost text-sm">Back to chat</button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-1 bg-white rounded-2xl p-1 shadow-soft mb-8 w-fit">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors relative ${
                tab === id
                  ? 'bg-charcoal-900 text-white'
                  : 'text-stone-500 hover:text-charcoal-800'
              }`}
            >
              <Icon size={14} />
              {label}
              {id === 'moderation' && openFlagCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {openFlagCount > 9 ? '9+' : openFlagCount}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === 'overview' && <Overview metrics={metrics} />}
        {tab === 'revenue' && <RevenueTab />}
        {tab === 'referral' && <ReferralTab />}
        {tab === 'conversations' && <ConversationsTab />}
        {tab === 'users' && <UsersTab />}
        {tab === 'moderation' && <ModerationTab />}
      </div>
    </div>
  )
}
