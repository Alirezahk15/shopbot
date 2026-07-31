import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api, { downloadFile } from '../api/client.js'
import {
  CheckCircle, XCircle, RefreshCw, CreditCard, BarChart2,
  Download, Filter, Search, X, Eye, ChevronLeft, ChevronRight,
  ImageOff, User, DollarSign, Calendar, Clock, ZoomIn
} from 'lucide-react'

import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
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

// ── Receipt Image Component ──
function ReceiptImage({ fileId, lang }) {
  const [imgSrc, setImgSrc] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [zoomed, setZoomed] = useState(false)

  useEffect(() => {
    // Fetch image via API client (which attaches JWT token)
    let objectUrl = null
    let cancelled = false
    api.get(`/tg-file/${fileId}`, { responseType: 'blob' })
      .then(res => {
        objectUrl = URL.createObjectURL(res.data)
        if (cancelled) return
        setImgSrc(objectUrl)
        setLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setError(true)
        setLoading(false)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [fileId])

  return (
    <div className="mb-4">
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
        {lang === 'fa' ? 'تصویر رسید' : 'Receipt Image'}
      </div>
      <div
        className="rounded-xl overflow-hidden"
        style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.08))', minHeight: '120px' }}
      >
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
          </div>
        )}
        {error && (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
            <ImageOff className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-xs">{lang === 'fa' ? 'خطا در بارگذاری تصویر' : 'Failed to load image'}</p>
          </div>
        )}
        {imgSrc && !error && (
          <>
            <div className="relative cursor-pointer" onClick={() => setZoomed(!zoomed)}>
              <img
                src={imgSrc}
                alt="Receipt"
                className="w-full object-contain rounded-xl transition-all"
                style={{ maxHeight: zoomed ? '600px' : '200px' }}
              />
              <div className="absolute top-2 end-2 bg-black/50 rounded-lg p-1">
                <ZoomIn className="w-4 h-4 text-white" />
              </div>
            </div>
            <p className="text-xs text-gray-500 text-center py-1">
              {lang === 'fa' ? 'کلیک برای بزرگ‌نمایی' : 'Click to zoom'}
            </p>
          </>
        )}
      </div>
    </div>
  )
}

// ── Payment Detail Modal ──
function PaymentDetailModal({ payId, lang, onClose, onApprove, onReject }) {
  const { data, isLoading } = useQuery({
    queryKey: ['payment-detail', payId],
    queryFn: () => api.get(`/payments/${payId}`).then(r => r.data),
  })

  const [showRejectForm, setShowRejectForm] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  if (isLoading) return (
    <Modal title={`Payment #${payId}`} onClose={onClose}>
      <div className="flex justify-center py-8">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
      </div>
    </Modal>
  )

  const { payment, user } = data
  const statusColors = { pending: '#f59e0b', approved: '#10b981', rejected: '#ef4444' }
  const statusColor = statusColors[payment?.status] || '#6b7280'

  return (
    <Modal title={`${lang === 'fa' ? 'پرداخت' : 'Payment'} #${payId}`} onClose={onClose} maxWidth="max-w-xl">
      {/* Status badge */}
      <div
        className="flex items-center gap-2 rounded-xl px-4 py-2.5 mb-4"
        style={{ background: `${statusColor}10`, border: `1px solid ${statusColor}25` }}
      >
        <div className="w-2 h-2 rounded-full" style={{ background: statusColor }} />
        <span className="font-semibold text-sm" style={{ color: statusColor }}>
          {payment?.status === 'pending' ? (lang === 'fa' ? 'معلق' : 'Pending') :
           payment?.status === 'approved' ? (lang === 'fa' ? 'تأیید شده' : 'Approved') :
           (lang === 'fa' ? 'رد شده' : 'Rejected')}
        </span>
        <span className="text-gray-500 text-xs ms-auto">{payment?.created_at?.slice(0, 16)}</span>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {[
          { icon: DollarSign, label: lang === 'fa' ? 'مبلغ' : 'Amount', value: `$${payment?.amount}`, color: '#10b981' },
          { icon: User, label: lang === 'fa' ? 'کاربر' : 'User', value: `@${user?.username || payment?.user_id}`, color: '#6366f1' },
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

      {/* Reject reason */}
      {payment?.status === 'rejected' && payment?.reject_reason && (
        <div className="rounded-xl px-4 py-3 mb-4" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <div className="text-xs text-red-400 mb-1">{lang === 'fa' ? 'دلیل رد' : 'Reject Reason'}</div>
          <p className="text-sm text-gray-300">{payment.reject_reason}</p>
        </div>
      )}

      {/* Receipt image */}
      {payment?.receipt_file_id && (
        <ReceiptImage fileId={payment.receipt_file_id} lang={lang} />
      )}

      {/* Actions */}
      {payment?.status === 'pending' && (
        <div className="space-y-3">
          {!showRejectForm ? (
            <div className="flex gap-2">
              <button onClick={() => { onApprove(payId); onClose() }} className="btn-success flex-1">
                <CheckCircle className="w-4 h-4" /> {t('pay_approve', lang)}
              </button>
              <button onClick={() => setShowRejectForm(true)} className="btn-danger flex-1">
                <XCircle className="w-4 h-4" /> {t('pay_reject', lang)}
              </button>
            </div>
          ) : (
            <div className="animate-slide-up">
              <label className="form-label">{lang === 'fa' ? 'دلیل رد (اختیاری)' : 'Reject Reason (optional)'}</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="input mb-2"
                rows={3}
                placeholder={lang === 'fa' ? 'دلیل رد پرداخت...' : 'Reason for rejection...'}
                autoFocus
              />
              <div className="flex gap-2">
                <button onClick={() => { onReject(payId, rejectReason); onClose() }} className="btn-danger flex-1">
                  <XCircle className="w-4 h-4" /> {lang === 'fa' ? 'رد کن' : 'Reject'}
                </button>
                <button onClick={() => setShowRejectForm(false)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Re-approve if rejected */}
      {payment?.status === 'rejected' && (
        <button onClick={() => { onApprove(payId); onClose() }} className="btn-success w-full">
          <CheckCircle className="w-4 h-4" /> {lang === 'fa' ? 'تأیید مجدد' : 'Re-approve'}
        </button>
      )}
    </Modal>
  )
}

// ── Stats Modal ──
function StatsModal({ lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['payment-stats'],
    queryFn: () => api.get('/payments/stats').then(r => r.data),
  })

  const s = data?.summary

  return (
    <Modal title={lang === 'fa' ? 'آمار پرداخت‌ها' : 'Payment Statistics'} onClose={onClose} maxWidth="max-w-2xl">
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
              { label: lang === 'fa' ? 'تأیید شده' : 'Approved', value: s?.approved, color: '#10b981' },
              { label: lang === 'fa' ? 'رد شده' : 'Rejected', value: s?.rejected, color: '#ef4444' },
              { label: lang === 'fa' ? 'معلق' : 'Pending', value: s?.pending, color: '#f59e0b' },
            ].map((c, i) => (
              <div key={i} className="rounded-xl p-3 text-center" style={{ background: `${c.color}10`, border: `1px solid ${c.color}25` }}>
                <div className="font-bold text-lg" style={{ color: c.color }}>{c.value}</div>
                <div className="text-xs text-gray-500 mt-0.5">{c.label}</div>
              </div>
            ))}
          </div>

          {/* Financial summary */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl p-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'مجموع تأیید شده' : 'Total Approved'}</div>
              <div className="font-bold text-white">${s?.total_approved_amount?.toFixed(2)}</div>
            </div>
            <div className="rounded-xl p-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'میانگین مبلغ' : 'Avg Amount'}</div>
              <div className="font-bold text-white">${s?.avg_amount?.toFixed(2)}</div>
            </div>
            <div className="rounded-xl p-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'امروز' : 'Today'}</div>
              <div className="font-bold text-white">{s?.today_total} {lang === 'fa' ? 'پرداخت' : 'payments'}</div>
              <div className="text-sm text-green-400">${s?.today_amount?.toFixed(2)}</div>
            </div>
            <div className="rounded-xl p-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'نرخ تأیید' : 'Approval Rate'}</div>
              <div className="font-bold text-white">
                {s?.total > 0 ? Math.round((s?.approved / s?.total) * 100) : 0}%
              </div>
            </div>
          </div>

          {/* Daily chart */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {lang === 'fa' ? 'پرداخت‌های ۱۴ روز اخیر' : 'Payments — Last 14 Days'}
            </h4>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={data?.daily || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => v?.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px' }} />
                <Bar dataKey="approved" fill="#10b981" radius={[3, 3, 0, 0]} name="Approved" />
                <Bar dataKey="total" fill="rgba(99,102,241,0.3)" radius={[3, 3, 0, 0]} name="Total" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </Modal>
  )
}

// ── Main Payments Page ──
export default function Payments() {
  const { lang } = useApp()
  const { toast } = useToast()
  const qc = useQueryClient()

  // View mode: "pending" | "all"
  const [viewMode, setViewMode] = useState('pending')
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  // Selection for bulk actions
  const [selected, setSelected] = useState(new Set())

  // Modals
  const [detailPayId, setDetailPayId] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const [confirmModal, setConfirmModal] = useState(null)
  const [rejectModal, setRejectModal] = useState(null)
  const [rejectReason, setRejectReason] = useState('')

  const limit = 20

  // Pending payments query
  const { data: pendingData, isLoading: pendingLoading, refetch: refetchPending } = useQuery({
    queryKey: ['payments-pending'],
    queryFn: () => api.get('/payments/pending').then(r => r.data),
    refetchInterval: 30000,
    enabled: viewMode === 'pending',
  })

  // All payments query
  const { data: allData, isLoading: allLoading, refetch: refetchAll } = useQuery({
    queryKey: ['payments-all', page, search, filterStatus, dateFrom, dateTo],
    queryFn: () => {
      const params = new URLSearchParams({
        offset: page * limit,
        limit,
        ...(search && { search }),
        ...(filterStatus && { status: filterStatus }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      })
      return api.get(`/payments/all?${params}`).then(r => r.data)
    },
    enabled: viewMode === 'all',
  })

  const approveMutation = useMutation({
    mutationFn: (id) => api.post(`/payments/${id}/approve`),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['payments-pending'] })
      qc.invalidateQueries({ queryKey: ['payments-all'] })
      toast(lang === 'fa' ? `پرداخت تأیید شد — $${res.data.amount}` : `Payment approved — $${res.data.amount}`, 'success')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }) => api.post(`/payments/${id}/reject`, { reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['payments-pending'] })
      qc.invalidateQueries({ queryKey: ['payments-all'] })
      setRejectModal(null)
      setRejectReason('')
      toast(lang === 'fa' ? 'پرداخت رد شد' : 'Payment rejected', 'warning')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const bulkMutation = useMutation({
    mutationFn: ({ ids, action, reason }) => api.post('/payments/bulk-action', { payment_ids: ids, action, reason }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['payments-pending'] })
      qc.invalidateQueries({ queryKey: ['payments-all'] })
      setSelected(new Set())
      toast(
        lang === 'fa'
          ? `${res.data.count} پرداخت پردازش شد`
          : `${res.data.count} payments processed`,
        'success'
      )
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const handleExportCSV = () => {
    const params = new URLSearchParams({
      ...(filterStatus && { status: filterStatus }),
      ...(dateFrom && { date_from: dateFrom }),
      ...(dateTo && { date_to: dateTo }),
    })
    downloadFile(`/payments/export.csv?${params}`, 'payments.csv')
    toast(lang === 'fa' ? 'در حال دانلود...' : 'Downloading...', 'info')
  }

  const handleSearch = (e) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(0)
  }

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const payments = viewMode === 'pending' ? (pendingData?.payments || []) : (allData?.payments || [])
  const total = viewMode === 'all' ? (allData?.total || 0) : payments.length
  const isLoading = viewMode === 'pending' ? pendingLoading : allLoading

  const statusBadge = (status) => {
    if (status === 'approved') return <span className="badge-green">{lang === 'fa' ? 'تأیید' : 'Approved'}</span>
    if (status === 'rejected') return <span className="badge-red">{lang === 'fa' ? 'رد' : 'Rejected'}</span>
    return <span className="badge-yellow">{lang === 'fa' ? 'معلق' : 'Pending'}</span>
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('pay_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} {lang === 'fa' ? 'پرداخت' : 'payments'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-2 px-3">
            <BarChart2 className="w-4 h-4" />
          </button>
          <button onClick={handleExportCSV} className="btn-secondary py-2 px-3">
            <Download className="w-4 h-4" />
          </button>
          <button onClick={() => { viewMode === 'pending' ? refetchPending() : refetchAll() }} className="btn-secondary py-2 px-3">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* View mode tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => { setViewMode('pending'); setSelected(new Set()) }}
          className={`btn py-2 px-4 text-sm ${viewMode === 'pending' ? 'bg-yellow-600 text-white' : 'btn-secondary'}`}
        >
          <Clock className="w-4 h-4" />
          {lang === 'fa' ? 'معلق' : 'Pending'}
          {pendingData?.payments?.length > 0 && (
            <span className="ms-1 bg-yellow-500 text-white text-xs rounded-full px-1.5 py-0.5">
              {pendingData.payments.length}
            </span>
          )}
        </button>
        <button
          onClick={() => { setViewMode('all'); setSelected(new Set()) }}
          className={`btn py-2 px-4 text-sm ${viewMode === 'all' ? 'bg-indigo-600 text-white' : 'btn-secondary'}`}
        >
          {lang === 'fa' ? 'همه پرداخت‌ها' : 'All Payments'}
        </button>
        {viewMode === 'all' && (
          <button onClick={() => setShowFilters(!showFilters)} className={`btn-secondary py-2 px-3 ${showFilters ? 'text-indigo-400' : ''}`}>
            <Filter className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Search (all mode) */}
      {viewMode === 'all' && (
        <form onSubmit={handleSearch} className="flex gap-2 mb-3">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={lang === 'fa' ? 'جستجو با ID یا نام کاربری...' : 'Search by user ID or username...'}
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
      )}

      {/* Filters (all mode) */}
      {viewMode === 'all' && showFilters && (
        <div className="card mb-3 animate-slide-up" style={{ borderColor: 'rgba(99,102,241,0.2)' }}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="form-label">{t('status', lang)}</label>
              <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(0) }} className="input">
                <option value="">{lang === 'fa' ? 'همه' : 'All'}</option>
                <option value="pending">{lang === 'fa' ? 'معلق' : 'Pending'}</option>
                <option value="approved">{lang === 'fa' ? 'تأیید شده' : 'Approved'}</option>
                <option value="rejected">{lang === 'fa' ? 'رد شده' : 'Rejected'}</option>
              </select>
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'از تاریخ' : 'From Date'}</label>
              <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(0) }} className="input" dir="ltr" />
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'تا تاریخ' : 'To Date'}</label>
              <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(0) }} className="input" dir="ltr" />
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {showStats && <StatsModal lang={lang} onClose={() => setShowStats(false)} />}
      {detailPayId && (
        <PaymentDetailModal
          payId={detailPayId}
          lang={lang}
          onClose={() => setDetailPayId(null)}
          onApprove={(id) => approveMutation.mutate(id)}
          onReject={(id, reason) => rejectMutation.mutate({ id, reason })}
        />
      )}

      {/* Reject reason modal */}
      {rejectModal && (
        <Modal title={lang === 'fa' ? 'رد پرداخت' : 'Reject Payment'} onClose={() => setRejectModal(null)}>
          <p className="text-sm text-gray-400 mb-3">
            {lang === 'fa' ? `پرداخت #${rejectModal} رد شود؟` : `Reject payment #${rejectModal}?`}
          </p>
          <label className="form-label">{lang === 'fa' ? 'دلیل رد (اختیاری)' : 'Reject Reason (optional)'}</label>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            className="input mb-3"
            rows={3}
            placeholder={lang === 'fa' ? 'دلیل رد پرداخت...' : 'Reason for rejection...'}
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={() => rejectMutation.mutate({ id: rejectModal, reason: rejectReason })}
              disabled={rejectMutation.isPending}
              className="btn-danger flex-1"
            >
              {rejectMutation.isPending ? t('loading', lang) : (lang === 'fa' ? 'رد کن' : 'Reject')}
            </button>
            <button onClick={() => setRejectModal(null)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
          </div>
        </Modal>
      )}

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div
          className="flex items-center justify-between px-4 py-3 rounded-xl mb-3 animate-slide-up"
          style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)' }}
        >
          <span className="text-sm text-indigo-300">
            {selected.size} {lang === 'fa' ? 'پرداخت انتخاب شده' : 'payments selected'}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setConfirmModal({
                title: lang === 'fa' ? 'تأیید گروهی' : 'Bulk Approve',
                message: lang === 'fa' ? `${selected.size} پرداخت تأیید شود؟` : `Approve ${selected.size} payments?`,
                type: 'info',
                confirmText: lang === 'fa' ? 'بله، تأیید کن' : 'Yes, approve all',
                onConfirm: () => bulkMutation.mutate({ ids: [...selected], action: 'approve' }),
              })}
              className="btn-success py-1.5 px-3 text-sm"
            >
              <CheckCircle className="w-3.5 h-3.5" /> {lang === 'fa' ? 'تأیید همه' : 'Approve All'}
            </button>
            <button
              onClick={() => setConfirmModal({
                title: lang === 'fa' ? 'رد گروهی' : 'Bulk Reject',
                message: lang === 'fa' ? `${selected.size} پرداخت رد شود؟` : `Reject ${selected.size} payments?`,
                type: 'danger',
                confirmText: lang === 'fa' ? 'بله، رد کن' : 'Yes, reject all',
                onConfirm: () => bulkMutation.mutate({ ids: [...selected], action: 'reject' }),
              })}
              className="btn-danger py-1.5 px-3 text-sm"
            >
              <XCircle className="w-3.5 h-3.5" /> {lang === 'fa' ? 'رد همه' : 'Reject All'}
            </button>
            <button onClick={() => setSelected(new Set())} className="btn-secondary py-1.5 px-3 text-sm">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Payments list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : payments.length === 0 ? (
        <div className="card text-center py-16">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-white font-semibold">
            {viewMode === 'pending' ? t('pay_no_pending', lang) : t('no_data', lang)}
          </p>
        </div>
      ) : viewMode === 'pending' ? (
        /* Pending payments — card view */
        <div className="grid gap-4">
          {payments.map((p) => (
            <div
              key={p.id}
              className="card flex items-center gap-4 animate-slide-up"
              style={{ borderColor: 'rgba(245,158,11,0.2)' }}
            >
              <input
                type="checkbox"
                checked={selected.has(p.id)}
                onChange={() => toggleSelect(p.id)}
                className="rounded flex-shrink-0"
              />
              <div
                className="w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}
              >
                <CreditCard className="w-6 h-6" style={{ color: '#f59e0b' }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl font-bold text-white">${p.amount}</span>
                  <span className="badge-yellow">{lang === 'fa' ? 'معلق' : 'Pending'}</span>
                </div>
                <div className="text-sm text-gray-400">
                  <span className="font-mono text-xs">{p.user_id}</span>
                  {p.username && <span className="ms-1 text-gray-500">@{p.username}</span>}
                </div>
                <div className="text-xs text-gray-600 mt-0.5">{p.created_at?.slice(0, 16)}</div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button onClick={() => setDetailPayId(p.id)} className="btn-secondary py-2 px-3">
                  <Eye className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setConfirmModal({
                    title: lang === 'fa' ? 'تأیید پرداخت' : 'Approve Payment',
                    message: lang === 'fa' ? `پرداخت $${p.amount} تأیید شود؟` : `Approve $${p.amount} payment?`,
                    type: 'info',
                    confirmText: lang === 'fa' ? 'بله، تأیید کن' : 'Yes, approve',
                    onConfirm: () => approveMutation.mutate(p.id),
                  })}
                  className="btn-success py-2 px-3"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span className="hidden sm:inline">{t('pay_approve', lang)}</span>
                </button>
                <button
                  onClick={() => { setRejectModal(p.id); setRejectReason('') }}
                  className="btn-danger py-2 px-3"
                >
                  <XCircle className="w-4 h-4" />
                  <span className="hidden sm:inline">{t('pay_reject', lang)}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* All payments — table view */
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-soft, rgba(255,255,255,0.06))', background: 'var(--surface-hover, rgba(255,255,255,0.02))' }}>
                  <th className="table-header w-8">
                    <input
                      type="checkbox"
                      checked={selected.size === payments.filter(p => p.status === 'pending').length && payments.filter(p => p.status === 'pending').length > 0}
                      onChange={() => {
                        const pendingIds = payments.filter(p => p.status === 'pending').map(p => p.id)
                        if (selected.size === pendingIds.length) setSelected(new Set())
                        else setSelected(new Set(pendingIds))
                      }}
                      className="rounded"
                    />
                  </th>
                  <th className="table-header">#</th>
                  <th className="table-header">{t('user', lang)}</th>
                  <th className="table-header">{t('amount', lang)}</th>
                  <th className="table-header">{t('status', lang)}</th>
                  <th className="table-header">{t('date', lang)}</th>
                  <th className="table-header">{t('actions', lang)}</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => (
                  <tr key={p.id} className={`table-row ${selected.has(p.id) ? 'bg-indigo-900/10' : ''}`}>
                    <td className="table-cell">
                      <input
                        type="checkbox"
                        checked={selected.has(p.id)}
                        onChange={() => p.status === 'pending' && toggleSelect(p.id)}
                        disabled={p.status !== 'pending'}
                        className="rounded"
                        style={{ opacity: p.status !== 'pending' ? 0.2 : 1, cursor: p.status !== 'pending' ? 'not-allowed' : 'pointer' }}
                        title={p.status !== 'pending' ? (p.status === 'approved' ? 'Already approved' : 'Already rejected') : 'Select for bulk action'}
                      />
                    </td>
                    <td className="table-cell font-mono text-xs text-gray-400">{p.id}</td>
                    <td className="table-cell">
                      <div className="text-gray-300 text-sm">@{p.username || 'N/A'}</div>
                      <div className="text-xs text-gray-500 font-mono">{p.user_id}</div>
                    </td>
                    <td className="table-cell font-semibold text-white">${p.amount}</td>
                    <td className="table-cell">{statusBadge(p.status)}</td>
                    <td className="table-cell text-gray-500 text-xs">{p.created_at?.slice(0, 10)}</td>
                    <td className="table-cell">
                      <div className="flex gap-1">
                        <button onClick={() => setDetailPayId(p.id)} className="action-btn action-view">
                          <Eye className="w-4 h-4" />
                        </button>
                        {p.status === 'pending' && (
                          <>
                            <button
                              onClick={() => setConfirmModal({
                                title: lang === 'fa' ? 'تأیید پرداخت' : 'Approve',
                                message: lang === 'fa' ? `پرداخت $${p.amount} تأیید شود؟` : `Approve $${p.amount}?`,
                                type: 'info',
                                onConfirm: () => approveMutation.mutate(p.id),
                              })}
                              className="action-btn action-success"
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => { setRejectModal(p.id); setRejectReason('') }}
                              className="action-btn action-danger"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        {p.status === 'rejected' && (
                          <button
                            onClick={() => setConfirmModal({
                              title: lang === 'fa' ? 'تأیید مجدد' : 'Re-approve',
                              message: lang === 'fa' ? `پرداخت رد شده #${p.id} تأیید شود؟` : `Re-approve rejected payment #${p.id}?`,
                              type: 'info',
                              onConfirm: () => approveMutation.mutate(p.id),
                            })}
                            className="action-btn action-success"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {viewMode === 'all' && (
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
