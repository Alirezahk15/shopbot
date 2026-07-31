import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api, { downloadFile } from '../api/client.js'
import {
  Search, UserX, UserCheck, PlusCircle, ChevronLeft, ChevronRight,
  X, StickyNote, Eye, Download, Send, BarChart2, Filter,
  MinusCircle, DollarSign, ShoppingCart, Ticket, ArrowUpDown,
  MessageSquare, Clock, TrendingUp
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts'

// ── Modal wrapper ──
function Modal({ title, onClose, children, maxWidth = 'max-w-sm' }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)', animation: 'fadeIn 0.15s ease' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className={`w-full ${maxWidth} rounded-2xl p-6 max-h-[90vh] overflow-y-auto`}
        style={{
          background: 'var(--surface-strong, #1a1a2e)',
          border: '1px solid var(--primary-25, rgba(99,102,241,0.25))',
          boxShadow: 'var(--shadow-modal, 0 25px 50px rgba(0,0,0,0.5))',
          animation: 'slideUp 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white">{title}</h3>
          <button onClick={onClose} className="action-btn action-neutral">
            <X className="w-4 h-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ── User Detail Modal ──
function UserDetailModal({ uid, lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['user-detail', uid],
    queryFn: () => api.get(`/users/${uid}`).then(r => r.data),
  })

  if (isLoading) return (
    <Modal title={`User #${uid}`} onClose={onClose} maxWidth="max-w-2xl">
      <div className="flex justify-center py-8">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
      </div>
    </Modal>
  )

  if (!data) return (
    <Modal title={`User #${uid}`} onClose={onClose} maxWidth="max-w-2xl">
      <p className="text-center text-gray-500 text-sm py-8">{lang === 'fa' ? 'خطا در دریافت اطلاعات' : 'Failed to load data'}</p>
    </Modal>
  )

  const { user, stats, recent_orders, recent_transactions, recent_tickets } = data

  return (
    <Modal title={`User #${uid}`} onClose={onClose} maxWidth="max-w-2xl">
      {/* Profile header */}
      <div
        className="rounded-xl p-4 mb-4 flex items-center gap-4"
        style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)' }}
      >
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center text-xl font-bold flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
        >
          {(user.username || '?')[0].toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-white">@{user.username || 'N/A'}</div>
          <div className="text-xs text-gray-400 font-mono">{user.user_id}</div>
          <div className="flex gap-2 mt-1">
            {user.blocked
              ? <span className="badge-red">{t('blocked', lang)}</span>
              : <span className="badge-green">{t('active', lang)}</span>
            }
            <span className="badge-gray">{user.lang || '?'}</span>
          </div>
        </div>
        <div className="text-end">
          <div className="text-2xl font-bold text-white">${user.balance?.toFixed(2)}</div>
          <div className="text-xs text-gray-400">{t('balance', lang)}</div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {[
          { icon: ShoppingCart, label: lang === 'fa' ? 'سفارش‌ها' : 'Orders', value: stats?.total_orders || 0, color: '#10b981' },
          { icon: DollarSign, label: lang === 'fa' ? 'مجموع خرید' : 'Total Spent', value: `$${(stats?.total_spent || 0).toFixed(0)}`, color: '#8b5cf6' },
          { icon: TrendingUp, label: lang === 'fa' ? 'درآمد رفرال' : 'Ref Earnings', value: `$${user.ref_earnings?.toFixed(2) || '0.00'}`, color: '#f59e0b' },
        ].map((s, i) => (
          <div key={i} className="rounded-xl p-3 text-center" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
            <s.icon className="w-4 h-4 mx-auto mb-1" style={{ color: s.color }} />
            <div className="font-bold text-white text-sm">{s.value}</div>
            <div className="text-xs text-gray-500">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="grid grid-cols-2 gap-2 mb-4 text-xs">
        <div className="rounded-lg p-2.5" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
          <span className="text-gray-500">{t('joined', lang)}: </span>
          <span className="text-gray-300">{user.joined_at?.slice(0, 10)}</span>
        </div>
        <div className="rounded-lg p-2.5" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
          <span className="text-gray-500">{lang === 'fa' ? 'رفرال‌ها' : 'Referrals'}: </span>
          <span className="text-gray-300">{stats?.ref_total || 0}</span>
        </div>
        {user.note && (
          <div className="col-span-2 rounded-lg p-2.5" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.15)' }}>
            <span className="text-yellow-400 text-xs">📝 {user.note}</span>
          </div>
        )}
      </div>

      {/* Recent orders */}
      {recent_orders?.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            {lang === 'fa' ? 'آخرین سفارش‌ها' : 'Recent Orders'}
          </h4>
          <div className="space-y-1.5">
            {recent_orders.slice(0, 5).map(o => (
              <div key={o.id} className="flex items-center justify-between rounded-lg px-3 py-2 text-xs" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <span className="text-gray-300">#{o.id} {o.name}</span>
                <span className="text-green-400 font-semibold">${o.price}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent transactions */}
      {recent_transactions?.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            {lang === 'fa' ? 'آخرین واریزی‌ها' : 'Recent Deposits'}
          </h4>
          <div className="space-y-1.5">
            {recent_transactions.slice(0, 5).map(tx => (
              <div key={tx.id} className="flex items-center justify-between rounded-lg px-3 py-2 text-xs" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <span className="text-gray-400">{tx.method?.toUpperCase()} · {tx.created_at?.slice(0, 10)}</span>
                <span className="text-blue-400 font-semibold">+${tx.amount}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent tickets */}
      {recent_tickets?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            {lang === 'fa' ? 'تیکت‌های اخیر' : 'Recent Tickets'}
          </h4>
          <div className="space-y-1.5">
            {recent_tickets.map(tk => (
              <div key={tk.id} className="flex items-center justify-between rounded-lg px-3 py-2 text-xs" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <span className="text-gray-300">#{tk.id} {tk.subject?.slice(0, 30)}</span>
                <span className={`badge-${tk.status === 'open' ? 'yellow' : tk.status === 'answered' ? 'blue' : 'gray'}`}>{tk.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  )
}

// ── User Stats Modal ──
function UserStatsModal({ lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['user-stats-chart'],
    queryFn: () => api.get('/users/stats').then(r => r.data),
  })

  const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#3b82f6']

  return (
    <Modal title={lang === 'fa' ? 'آمار کاربران' : 'User Statistics'} onClose={onClose} maxWidth="max-w-2xl">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Growth chart */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {lang === 'fa' ? 'رشد کاربران (۱۴ روز اخیر)' : 'User Growth (Last 14 Days)'}
            </h4>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={data?.growth || []}>
                <defs>
                  <linearGradient id="userGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false}
                  tickFormatter={v => v?.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px' }} />
                <Area type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} fill="url(#userGrad)" dot={{ fill: '#6366f1', r: 3 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Language distribution */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                {lang === 'fa' ? 'توزیع زبان' : 'Language Distribution'}
              </h4>
              <ResponsiveContainer width="100%" height={140}>
                <PieChart>
                  <Pie data={data?.languages || []} dataKey="count" nameKey="lang" cx="50%" cy="50%" outerRadius={55} label={({ lang: l, percent }) => `${l} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={11}>
                    {(data?.languages || []).map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Top spenders */}
            <div>
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                {lang === 'fa' ? 'بیشترین خریداران' : 'Top Spenders'}
              </h4>
              <div className="space-y-2">
                {(data?.top_spenders || []).map((u, i) => (
                  <div key={u.user_id} className="flex items-center gap-2">
                    <span className="text-xs font-bold w-4" style={{ color: i === 0 ? '#f59e0b' : i === 1 ? '#9ca3af' : '#b47c3c' }}>
                      {i + 1}
                    </span>
                    <span className="text-xs text-gray-300 flex-1 truncate">@{u.username || u.user_id}</span>
                    <span className="text-xs font-semibold text-green-400">${u.total_spent?.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </Modal>
  )
}

// ── Main Users Page ──
export default function Users() {
  const { lang } = useApp()
  const { toast } = useToast()
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterLang, setFilterLang] = useState('')
  const [sortBy, setSortBy] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  // Modals
  const [detailUid, setDetailUid] = useState(null)
  const [balanceModal, setBalanceModal] = useState(null)
  const [noteModal, setNoteModal] = useState(null)
  const [messageModal, setMessageModal] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const [confirmModal, setConfirmModal] = useState(null)

  // Form states
  const [balanceAmount, setBalanceAmount] = useState('')
  const [balanceOp, setBalanceOp] = useState('add')
  const [noteText, setNoteText] = useState('')
  const [messageText, setMessageText] = useState('')

  const qc = useQueryClient()
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ['users', page, search, filterStatus, filterLang, sortBy],
    queryFn: () => {
      if (search) {
        return api.get(`/users/search/${encodeURIComponent(search)}`).then(r => ({ users: r.data.users, total: r.data.users.length }))
      }
      const params = new URLSearchParams({
        offset: page * limit,
        limit,
        ...(filterStatus && { status: filterStatus }),
        ...(filterLang && { lang: filterLang }),
        ...(sortBy && { sort: sortBy }),
      })
      return api.get(`/users?${params}`).then(r => r.data)
    },
  })

  const blockMutation = useMutation({
    mutationFn: (uid) => api.post(`/users/${uid}/block`),
    onSuccess: (res, uid) => {
      qc.invalidateQueries({ queryKey: ['users'] })
      toast(res.data.blocked
        ? (lang === 'fa' ? 'کاربر مسدود شد' : 'User blocked')
        : (lang === 'fa' ? 'مسدودیت برداشته شد' : 'User unblocked'),
        res.data.blocked ? 'warning' : 'success'
      )
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const balanceMutation = useMutation({
    mutationFn: ({ uid, amount, operation }) => api.post(`/users/${uid}/balance`, { amount, operation }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setBalanceModal(null)
      setBalanceAmount('')
      toast(
        lang === 'fa'
          ? `موجودی بروزرسانی شد — موجودی جدید: $${res.data.new_balance?.toFixed(2)}`
          : `Balance updated — New: $${res.data.new_balance?.toFixed(2)}`,
        'success'
      )
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const noteMutation = useMutation({
    mutationFn: ({ uid, note }) => api.post(`/users/${uid}/note`, { note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setNoteModal(null)
      toast(lang === 'fa' ? 'یادداشت ذخیره شد' : 'Note saved', 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const messageMutation = useMutation({
    mutationFn: ({ uid, message }) => api.post(`/users/${uid}/message`, { message }),
    onSuccess: () => {
      setMessageModal(null)
      setMessageText('')
      toast(lang === 'fa' ? 'پیام در صف ارسال قرار گرفت' : 'Message queued for delivery', 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const handleSearch = (e) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(0)
  }

  const handleExportCSV = () => {
    downloadFile('/users/export.csv', 'users.csv')
    toast(lang === 'fa' ? 'در حال دانلود...' : 'Downloading...', 'info')
  }

  const users = data?.users || []
  const total = data?.total || 0

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('users_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} {lang === 'fa' ? 'کاربر' : 'users'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'آمار' : 'Stats'}>
            <BarChart2 className="w-4 h-4" />
          </button>
          <button onClick={handleExportCSV} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'خروجی CSV' : 'Export CSV'}>
            <Download className="w-4 h-4" />
          </button>
          <button onClick={() => setShowFilters(!showFilters)} className={`btn-secondary py-2 px-3 ${showFilters ? 'text-indigo-400' : ''}`}>
            <Filter className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-3">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={t('users_search', lang)}
          className="input flex-1"
        />
        <button type="submit" className="btn-primary px-4">
          <Search className="w-4 h-4" />
        </button>
        {search && (
          <button type="button" onClick={() => { setSearch(''); setSearchInput('') }} className="btn-secondary px-3">
            <X className="w-4 h-4" />
          </button>
        )}
      </form>

      {/* Filters */}
      {showFilters && (
        <div
          className="card mb-3 animate-slide-up"
          style={{ borderColor: 'rgba(99,102,241,0.2)' }}
        >
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="form-label">{t('status', lang)}</label>
              <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(0) }} className="input">
                <option value="">{lang === 'fa' ? 'همه' : 'All'}</option>
                <option value="active">{t('active', lang)}</option>
                <option value="blocked">{t('blocked', lang)}</option>
              </select>
            </div>
            <div>
              <label className="form-label">{t('lang', lang)}</label>
              <select value={filterLang} onChange={(e) => { setFilterLang(e.target.value); setPage(0) }} className="input">
                <option value="">{lang === 'fa' ? 'همه' : 'All'}</option>
                <option value="fa">🇮🇷 فارسی</option>
                <option value="en">🇬🇧 English</option>
              </select>
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'مرتب‌سازی' : 'Sort By'}</label>
              <select value={sortBy} onChange={(e) => { setSortBy(e.target.value); setPage(0) }} className="input">
                <option value="">{lang === 'fa' ? 'تاریخ عضویت' : 'Join Date'}</option>
                <option value="balance">{t('balance', lang)}</option>
                <option value="orders">{lang === 'fa' ? 'تعداد سفارش' : 'Orders'}</option>
              </select>
            </div>
          </div>
          {(filterStatus || filterLang || sortBy) && (
            <button
              onClick={() => { setFilterStatus(''); setFilterLang(''); setSortBy(''); setPage(0) }}
              className="btn-ghost text-xs mt-2 text-gray-400"
            >
              <X className="w-3 h-3" /> {lang === 'fa' ? 'پاک کردن فیلترها' : 'Clear filters'}
            </button>
          )}
        </div>
      )}

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {detailUid && <UserDetailModal uid={detailUid} lang={lang} onClose={() => setDetailUid(null)} />}
      {showStats && <UserStatsModal lang={lang} onClose={() => setShowStats(false)} />}

      {/* Balance Modal */}
      {balanceModal && (
        <Modal title={t('users_add_bal', lang)} onClose={() => setBalanceModal(null)}>
          <p className="text-sm text-gray-400 mb-3">
            {t('users_cur_bal', lang)}: <span className="text-white font-bold">${balanceModal.balance?.toFixed(2)}</span>
          </p>
          <div className="flex gap-2 mb-3">
            {[
              { op: 'add', icon: PlusCircle, label: lang === 'fa' ? 'افزایش' : 'Add', color: '#10b981' },
              { op: 'subtract', icon: MinusCircle, label: lang === 'fa' ? 'کاهش' : 'Subtract', color: '#ef4444' },
              { op: 'set', icon: DollarSign, label: lang === 'fa' ? 'تنظیم' : 'Set', color: '#6366f1' },
            ].map(({ op, icon: Icon, label, color }) => (
              <button
                key={op}
                onClick={() => setBalanceOp(op)}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-medium transition-all"
                style={{
                  background: balanceOp === op ? `${color}20` : 'var(--surface-hover, rgba(255,255,255,0.04))',
                  border: `1px solid ${balanceOp === op ? color + '50' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
                  color: balanceOp === op ? color : 'rgba(156,163,175,0.8)',
                }}
              >
                <Icon className="w-3.5 h-3.5" /> {label}
              </button>
            ))}
          </div>
          <input
            type="number" dir="ltr" step="0.01" min="0"
            value={balanceAmount}
            onChange={(e) => setBalanceAmount(e.target.value)}
            placeholder={t('users_amount_ph', lang)}
            className="input mb-3"
            autoFocus
            dir="ltr"
          />
          <div className="flex gap-2">
            <button
              onClick={() => balanceMutation.mutate({ uid: balanceModal.user_id, amount: parseFloat(balanceAmount), operation: balanceOp })}
              disabled={!balanceAmount || balanceMutation.isPending}
              className="btn-primary flex-1"
            >
              {balanceMutation.isPending ? t('loading', lang) : t('save', lang)}
            </button>
            <button onClick={() => setBalanceModal(null)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
          </div>
        </Modal>
      )}

      {/* Note Modal */}
      {noteModal && (
        <Modal title={t('users_add_note', lang)} onClose={() => setNoteModal(null)}>
          <textarea
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder={t('users_note_ph', lang)}
            className="input mb-3"
            rows={3}
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={() => noteMutation.mutate({ uid: noteModal.user_id, note: noteText })}
              disabled={noteMutation.isPending}
              className="btn-primary flex-1"
            >
              {noteMutation.isPending ? t('loading', lang) : t('save', lang)}
            </button>
            <button onClick={() => setNoteModal(null)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
          </div>
        </Modal>
      )}

      {/* Message Modal */}
      {messageModal && (
        <Modal title={lang === 'fa' ? `ارسال پیام به @${messageModal.username || messageModal.user_id}` : `Message @${messageModal.username || messageModal.user_id}`} onClose={() => setMessageModal(null)}>
          <textarea
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder={lang === 'fa' ? 'پیام خود را بنویسید (HTML پشتیبانی می‌شود)...' : 'Write your message (HTML supported)...'}
            className="input mb-3"
            rows={4}
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={() => messageMutation.mutate({ uid: messageModal.user_id, message: messageText })}
              disabled={!messageText.trim() || messageMutation.isPending}
              className="btn-primary flex-1"
            >
              <Send className="w-4 h-4" />
              {messageMutation.isPending ? t('loading', lang) : (lang === 'fa' ? 'ارسال' : 'Send')}
            </button>
            <button onClick={() => setMessageModal(null)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
          </div>
        </Modal>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-soft, rgba(255,255,255,0.06))', background: 'var(--surface-hover, rgba(255,255,255,0.02))' }}>
                  <th className="table-header">{t('id', lang)}</th>
                  <th className="table-header">{t('username', lang)}</th>
                  <th className="table-header">{t('balance', lang)}</th>
                  <th className="table-header">{t('lang', lang)}</th>
                  <th className="table-header">{t('joined', lang)}</th>
                  <th className="table-header">{t('status', lang)}</th>
                  <th className="table-header">{t('actions', lang)}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id} className="table-row">
                    <td className="table-cell font-mono text-xs text-gray-400">{u.user_id}</td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-300">@{u.username || 'N/A'}</span>
                        {u.note && <span title={u.note} className="text-yellow-400 cursor-help">📝</span>}
                      </div>
                    </td>
                    <td className="table-cell font-semibold text-white">${(u.balance || 0).toFixed(2)}</td>
                    <td className="table-cell">
                      <span className="badge-gray">{u.lang || '?'}</span>
                    </td>
                    <td className="table-cell text-gray-500 text-xs">{u.joined_at?.slice(0, 10)}</td>
                    <td className="table-cell">
                      {u.blocked
                        ? <span className="badge-red">{t('blocked', lang)}</span>
                        : <span className="badge-green">{t('active', lang)}</span>
                      }
                    </td>
                    <td className="table-cell">
                      <div className="flex gap-1">
                        <button onClick={() => setDetailUid(u.user_id)} className="action-btn action-view" title={lang === 'fa' ? 'مشاهده پروفایل' : 'View Profile'}>
                          <Eye className="w-4 h-4" />
                        </button>
                        <button onClick={() => { setBalanceModal(u); setBalanceAmount(''); setBalanceOp('add') }} className="action-btn action-success" title={t('users_add_bal', lang)}>
                          <PlusCircle className="w-4 h-4" />
                        </button>
                        <button onClick={() => { setNoteModal(u); setNoteText(u.note || '') }} className="action-btn action-warning" title={t('users_add_note', lang)}>
                          <StickyNote className="w-4 h-4" />
                        </button>
                        <button onClick={() => { setMessageModal(u); setMessageText('') }} className="action-btn action-info" title={lang === 'fa' ? 'ارسال پیام' : 'Send Message'}>
                          <MessageSquare className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setConfirmModal({
                            title: u.blocked ? (lang === 'fa' ? 'رفع مسدودیت' : 'Unblock User') : (lang === 'fa' ? 'مسدود کردن' : 'Block User'),
                            message: u.blocked
                              ? (lang === 'fa' ? `کاربر ${u.user_id} از مسدودیت خارج شود؟` : `Unblock user ${u.user_id}?`)
                              : (lang === 'fa' ? `کاربر ${u.user_id} مسدود شود؟` : `Block user ${u.user_id}?`),
                            type: u.blocked ? 'info' : 'danger',
                            onConfirm: () => blockMutation.mutate(u.user_id),
                          })}
                          className={`action-btn ${u.blocked ? 'action-success' : 'action-danger'}`}
                          title={u.blocked ? t('users_unblock', lang) : t('users_block', lang)}
                        >
                          {u.blocked ? <UserCheck className="w-4 h-4" /> : <UserX className="w-4 h-4" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {!search && (
            <div className="flex items-center justify-between px-4 py-3" style={{ borderTop: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
              <span className="text-xs text-gray-500">
                {page * limit + 1}–{Math.min((page + 1) * limit, total)} / {total}
              </span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="btn-secondary py-1 px-2 disabled:opacity-30">
                  <ChevronLeft className="w-4 h-4 rtl-flip" />
                </button>
                <button onClick={() => setPage(p => p + 1)} disabled={(page + 1) * limit >= total} className="btn-secondary py-1 px-2 disabled:opacity-30">
                  <ChevronRight className="w-4 h-4 rtl-flip" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
