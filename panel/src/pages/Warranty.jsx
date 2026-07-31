import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api, { downloadFile } from '../api/client.js'
import {
  Shield, CheckCircle, XCircle, RefreshCw, BarChart2,
  Download, Filter, Search, X, Eye, Package, User,
  DollarSign, Clock, History, Send
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'

// ── Modal wrapper ──
function Modal({ title, onClose, children, maxWidth = 'max-w-lg' }) {
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

// ── Claim Detail Modal ──
function ClaimDetailModal({ claimId, lang, onClose }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [note, setNote] = useState('')
  const [resendProduct, setResendProduct] = useState(false)
  const [showApproveForm, setShowApproveForm] = useState(false)
  const [showRejectForm, setShowRejectForm] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['warranty-detail', claimId],
    queryFn: () => api.get(`/warranty/${claimId}`).then(r => r.data),
  })

  const updateMutation = useMutation({
    mutationFn: ({ status, note, resend_product }) =>
      api.post(`/warranty/${claimId}`, { status, note, resend_product }),
    onSuccess: (res, vars) => {
      qc.invalidateQueries({ queryKey: ['warranty'] })
      if (res.data.resent_content) {
        toast(
          lang === 'fa'
            ? `گارانتی تأیید شد — محتوای جدید ارسال شد`
            : `Warranty approved — new content sent`,
          'success'
        )
      } else {
        toast(
          vars.status === 'approved'
            ? (lang === 'fa' ? 'گارانتی تأیید شد' : 'Warranty approved')
            : (lang === 'fa' ? 'گارانتی رد شد' : 'Warranty rejected'),
          vars.status === 'approved' ? 'success' : 'warning'
        )
      }
      onClose()
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  if (isLoading) return (
    <Modal title={`Warranty #${claimId}`} onClose={onClose} maxWidth="max-w-2xl">
      <div className="flex justify-center py-8">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
      </div>
    </Modal>
  )

  if (!data) return (
    <Modal title={`Warranty #${claimId}`} onClose={onClose} maxWidth="max-w-2xl">
      <p className="text-center text-gray-500 text-sm py-8">{lang === 'fa' ? 'خطا در دریافت اطلاعات' : 'Failed to load data'}</p>
    </Modal>
  )

  const { claim, user_history, available_stock } = data
  const statusColors = { pending: '#f59e0b', approved: '#10b981', rejected: '#ef4444' }
  const statusColor = statusColors[claim?.status] || '#6b7280'

  return (
    <Modal title={`${lang === 'fa' ? 'درخواست گارانتی' : 'Warranty Claim'} #${claimId}`} onClose={onClose} maxWidth="max-w-2xl">
      {/* Status */}
      <div
        className="flex items-center gap-2 rounded-xl px-4 py-2.5 mb-4"
        style={{ background: `${statusColor}10`, border: `1px solid ${statusColor}25` }}
      >
        <div className="w-2 h-2 rounded-full" style={{ background: statusColor }} />
        <span className="font-semibold text-sm" style={{ color: statusColor }}>
          {claim?.status === 'pending' ? (lang === 'fa' ? 'معلق' : 'Pending') :
           claim?.status === 'approved' ? (lang === 'fa' ? 'تأیید شده' : 'Approved') :
           (lang === 'fa' ? 'رد شده' : 'Rejected')}
        </span>
        <span className="text-gray-500 text-xs ms-auto">{claim?.created_at?.slice(0, 16)}</span>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {[
          { icon: Package, label: lang === 'fa' ? 'محصول' : 'Product', value: claim?.product_name, color: '#8b5cf6' },
          { icon: DollarSign, label: lang === 'fa' ? 'قیمت سفارش' : 'Order Price', value: `$${claim?.order_price}`, color: '#10b981' },
          { icon: User, label: lang === 'fa' ? 'کاربر' : 'User', value: `@${claim?.username || claim?.user_id}`, color: '#6366f1' },
          { icon: Package, label: lang === 'fa' ? 'موجودی برای ارسال' : 'Stock Available', value: available_stock, color: available_stock > 0 ? '#10b981' : '#ef4444' },
        ].map((s, i) => (
          <div key={i} className="rounded-xl p-3 flex items-center gap-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
            <s.icon className="w-4 h-4 flex-shrink-0" style={{ color: s.color }} />
            <div>
              <div className="text-xs text-gray-500">{s.label}</div>
              <div className="text-sm font-semibold text-white">{s.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Reason */}
      <div className="rounded-xl p-4 mb-4" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
        <div className="text-xs text-gray-500 mb-2">{lang === 'fa' ? 'دلیل درخواست' : 'Claim Reason'}</div>
        <p className="text-sm text-gray-200 whitespace-pre-wrap">{claim?.reason}</p>
      </div>

      {/* Admin note (if exists) */}
      {claim?.admin_note && (
        <div className="rounded-xl p-4 mb-4" style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)' }}>
          <div className="text-xs text-indigo-400 mb-2">{lang === 'fa' ? 'یادداشت ادمین' : 'Admin Note'}</div>
          <p className="text-sm text-gray-200">{claim.admin_note}</p>
        </div>
      )}

      {/* User warranty history */}
      {user_history?.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1">
            <History className="w-3 h-3" />
            {lang === 'fa' ? 'تاریخچه گارانتی کاربر' : 'User Warranty History'}
          </div>
          <div className="space-y-1.5">
            {user_history.map(h => (
              <div key={h.id} className="flex items-center gap-3 rounded-lg px-3 py-2 text-xs" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <span className="text-gray-400">#{h.id}</span>
                <span className="text-gray-300 flex-1 truncate">{h.product_name}</span>
                <span className={`badge-${h.status === 'approved' ? 'green' : h.status === 'rejected' ? 'red' : 'yellow'}`}>{h.status}</span>
                <span className="text-gray-500">{h.created_at?.slice(0, 10)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {claim?.status === 'pending' && (
        <div className="space-y-3">
          {!showApproveForm && !showRejectForm && (
            <div className="flex gap-2">
              <button onClick={() => setShowApproveForm(true)} className="btn-success flex-1">
                <CheckCircle className="w-4 h-4" /> {t('warr_approve', lang)}
              </button>
              <button onClick={() => setShowRejectForm(true)} className="btn-danger flex-1">
                <XCircle className="w-4 h-4" /> {t('warr_reject', lang)}
              </button>
            </div>
          )}

          {/* Approve form */}
          {showApproveForm && (
            <div className="animate-slide-up space-y-3">
              <label className="form-label">{lang === 'fa' ? 'یادداشت برای کاربر (اختیاری)' : 'Note for user (optional)'}</label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="input"
                rows={3}
                placeholder={lang === 'fa' ? 'پیام تأیید گارانتی...' : 'Warranty approval message...'}
                autoFocus
              />
              {available_stock > 0 && (
                <div className="flex items-center gap-3 rounded-xl px-4 py-3" style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
                  <input
                    type="checkbox"
                    id="resend"
                    checked={resendProduct}
                    onChange={(e) => setResendProduct(e.target.checked)}
                    className="rounded"
                  />
                  <label htmlFor="resend" className="text-sm text-green-300 cursor-pointer flex items-center gap-2">
                    <Send className="w-4 h-4" />
                    {lang === 'fa' ? `ارسال محصول جدید از موجودی (${available_stock} موجود)` : `Send new product from stock (${available_stock} available)`}
                  </label>
                </div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={() => updateMutation.mutate({ status: 'approved', note, resend_product: resendProduct })}
                  disabled={updateMutation.isPending}
                  className="btn-success flex-1"
                >
                  {updateMutation.isPending ? t('loading', lang) : (lang === 'fa' ? 'تأیید گارانتی' : 'Approve Warranty')}
                </button>
                <button onClick={() => setShowApproveForm(false)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
              </div>
            </div>
          )}

          {/* Reject form */}
          {showRejectForm && (
            <div className="animate-slide-up space-y-3">
              <label className="form-label">{lang === 'fa' ? 'دلیل رد (اختیاری)' : 'Reject Reason (optional)'}</label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="input"
                rows={3}
                placeholder={lang === 'fa' ? 'دلیل رد درخواست گارانتی...' : 'Reason for rejecting warranty...'}
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  onClick={() => updateMutation.mutate({ status: 'rejected', note, resend_product: false })}
                  disabled={updateMutation.isPending}
                  className="btn-danger flex-1"
                >
                  {updateMutation.isPending ? t('loading', lang) : (lang === 'fa' ? 'رد گارانتی' : 'Reject Warranty')}
                </button>
                <button onClick={() => setShowRejectForm(false)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

// ── Stats Modal ──
function StatsModal({ lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['warranty-stats'],
    queryFn: () => api.get('/warranty/stats').then(r => r.data),
  })

  const s = data?.summary

  return (
    <Modal title={lang === 'fa' ? 'آمار گارانتی' : 'Warranty Statistics'} onClose={onClose} maxWidth="max-w-2xl">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: lang === 'fa' ? 'کل' : 'Total', value: s?.total, color: '#6366f1' },
              { label: lang === 'fa' ? 'معلق' : 'Pending', value: s?.pending, color: '#f59e0b' },
              { label: lang === 'fa' ? 'تأیید' : 'Approved', value: s?.approved, color: '#10b981' },
              { label: lang === 'fa' ? 'رد' : 'Rejected', value: s?.rejected, color: '#ef4444' },
            ].map((c, i) => (
              <div key={i} className="rounded-xl p-3 text-center" style={{ background: `${c.color}10`, border: `1px solid ${c.color}25` }}>
                <div className="font-bold text-lg" style={{ color: c.color }}>{c.value}</div>
                <div className="text-xs text-gray-500 mt-0.5">{c.label}</div>
              </div>
            ))}
          </div>

          {/* Daily chart */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {lang === 'fa' ? 'درخواست‌های ۱۴ روز اخیر' : 'Claims — Last 14 Days'}
            </h4>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={data?.daily || []}>
                <defs>
                  <linearGradient id="warrantyGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#84cc16" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#84cc16" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v?.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px' }} />
                <Area type="monotone" dataKey="count" stroke="#84cc16" strokeWidth={2} fill="url(#warrantyGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Top products */}
          {(data?.top_products || []).length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                {lang === 'fa' ? 'پرتقاضاترین محصولات' : 'Most Claimed Products'}
              </h4>
              <div className="space-y-2">
                {(data?.top_products || []).map((p, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-xs font-bold w-5 text-center" style={{ color: i === 0 ? '#f59e0b' : '#6b7280' }}>{i + 1}</span>
                    <span className="text-sm text-gray-300 flex-1 truncate">{p.product_name}</span>
                    <span className="badge-red">{p.claim_count} {lang === 'fa' ? 'درخواست' : 'claims'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

// ── Main Warranty Page ──
export default function Warranty() {
  const { lang } = useApp()
  const { toast } = useToast()
  const [filter, setFilter] = useState('pending')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [detailClaimId, setDetailClaimId] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const [confirmModal, setConfirmModal] = useState(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['warranty', filter, search, dateFrom, dateTo],
    queryFn: () => {
      const params = new URLSearchParams({
        ...(filter && { status: filter }),
        ...(search && { search }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      })
      return api.get(`/warranty?${params}`).then(r => r.data)
    },
    refetchInterval: 30000,
  })

  const handleSearch = (e) => {
    e.preventDefault()
    setSearch(searchInput)
  }

  const handleExportCSV = () => {
    const params = new URLSearchParams({ ...(filter && { status: filter }) })
    downloadFile(`/warranty/export.csv?${params}`, 'warranty.csv')
    toast(lang === 'fa' ? 'در حال دانلود...' : 'Downloading...', 'info')
  }

  const claims = data?.claims || []

  const statusColors = { pending: '#f59e0b', approved: '#10b981', rejected: '#ef4444' }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('warr_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{claims.length} {lang === 'fa' ? 'درخواست' : 'claims'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-2 px-3">
            <BarChart2 className="w-4 h-4" />
          </button>
          <button onClick={handleExportCSV} className="btn-secondary py-2 px-3">
            <Download className="w-4 h-4" />
          </button>
          <button onClick={() => refetch()} className="btn-secondary py-2 px-3">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button onClick={() => setShowFilters(!showFilters)} className={`btn-secondary py-2 px-3 ${showFilters ? 'text-indigo-400' : ''}`}>
            <Filter className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 mb-3">
        {[
          { key: 'pending', label: lang === 'fa' ? 'معلق' : 'Pending', color: '#f59e0b' },
          { key: 'approved', label: lang === 'fa' ? 'تأیید' : 'Approved', color: '#10b981' },
          { key: 'rejected', label: lang === 'fa' ? 'رد' : 'Rejected', color: '#ef4444' },
          { key: '', label: lang === 'fa' ? 'همه' : 'All', color: '#9ca3af' },
        ].map(({ key, label, color }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className="btn py-1.5 px-3 text-sm"
            style={{
              background: filter === key ? `${color}20` : 'var(--surface-hover, rgba(255,255,255,0.04))',
              border: `1px solid ${filter === key ? color + '40' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
              color: filter === key ? color : 'rgba(156,163,175,0.8)',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-3">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={lang === 'fa' ? 'جستجو با ID کاربر، نام کاربری یا محصول...' : 'Search by user ID, username or product...'}
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
        <div className="card mb-3 animate-slide-up" style={{ borderColor: 'rgba(99,102,241,0.2)' }}>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="form-label">{lang === 'fa' ? 'از تاریخ' : 'From Date'}</label>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input" dir="ltr" />
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'تا تاریخ' : 'To Date'}</label>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input" dir="ltr" />
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {detailClaimId && <ClaimDetailModal claimId={detailClaimId} lang={lang} onClose={() => { setDetailClaimId(null); refetch() }} />}
      {showStats && <StatsModal lang={lang} onClose={() => setShowStats(false)} />}

      {/* Claims list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : claims.length === 0 ? (
        <div className="card text-center py-16">
          <Shield className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-white font-semibold">{t('warr_no_claims', lang)}</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {claims.map((c) => {
            const color = statusColors[c.status] || '#6b7280'
            return (
              <div
                key={c.id}
                className="card cursor-pointer hover:border-indigo-500/30 transition-colors"
                style={{ borderColor: `${color}20` }}
                onClick={() => setDetailClaimId(c.id)}
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: `${color}10`, border: `1px solid ${color}20` }}
                  >
                    <Shield className="w-6 h-6" style={{ color }} />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-white text-sm">{c.product_name}</span>
                      <span
                        className="badge text-xs"
                        style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}
                      >
                        {c.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-400 mb-1">
                      @{c.username || c.user_id} · ${c.order_price}
                    </div>
                    <p className="text-xs text-gray-500 truncate">{c.reason?.slice(0, 80)}</p>
                    {c.admin_note && (
                      <p className="text-xs text-indigo-400 mt-1 truncate">📝 {c.admin_note?.slice(0, 60)}</p>
                    )}
                  </div>

                  {/* Date + action */}
                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <span className="text-xs text-gray-500">{c.created_at?.slice(0, 10)}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDetailClaimId(c.id) }}
                      className="btn-secondary py-1.5 px-3 text-xs"
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
