import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import api, { downloadFile } from '../api/client.js'
import {
  ChevronLeft, ChevronRight, Eye, Download, BarChart2,
  Search, Filter, X, Send, User, Package, DollarSign,
  ShoppingCart, TrendingUp, Calendar, RefreshCw
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

// ── Order Detail Modal ──
function OrderDetailModal({ oid, lang, onClose }) {
  const { toast } = useToast()
  const [resendMsg, setResendMsg] = useState('')
  const [showResend, setShowResend] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['order-detail', oid],
    queryFn: () => api.get(`/orders/${oid}`).then(r => r.data),
  })

  const resendMutation = useMutation({
    mutationFn: (message) => api.post(`/orders/${oid}/resend`, { message }),
    onSuccess: () => {
      toast(lang === 'fa' ? 'محتوا در صف ارسال مجدد قرار گرفت' : 'Resend queued', 'success')
      setShowResend(false)
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  if (isLoading) return (
    <Modal title={`Order #${oid}`} onClose={onClose} maxWidth="max-w-2xl">
      <div className="flex justify-center py-8">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
      </div>
    </Modal>
  )

  const { order, user } = data

  return (
    <Modal title={`${lang === 'fa' ? 'سفارش' : 'Order'} #${oid}`} onClose={onClose} maxWidth="max-w-2xl">
      {/* Order info */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {[
          { icon: Package, label: lang === 'fa' ? 'محصول' : 'Product', value: order.product_name || order.name, color: '#8b5cf6' },
          { icon: DollarSign, label: lang === 'fa' ? 'قیمت' : 'Price', value: `$${order.price}`, color: '#10b981' },
          { icon: ShoppingCart, label: lang === 'fa' ? 'تعداد' : 'Qty', value: order.quantity || 1, color: '#6366f1' },
          { icon: Calendar, label: lang === 'fa' ? 'تاریخ' : 'Date', value: order.created_at?.slice(0, 10), color: '#f59e0b' },
        ].map((s, i) => (
          <div key={i} className="rounded-xl p-3 flex items-center gap-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
            <s.icon className="w-4 h-4 flex-shrink-0" style={{ color: s.color }} />
            <div>
              <div className="text-xs text-gray-500">{s.label}</div>
              <div className="text-sm font-semibold text-white">{s.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* User info */}
      {user && (
        <div className="rounded-xl p-3 mb-4 flex items-center gap-3" style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)' }}>
          <User className="w-4 h-4 text-indigo-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-sm text-white">@{user.username || 'N/A'}</div>
            <div className="text-xs text-gray-400 font-mono">{user.user_id}</div>
          </div>
          <div className="text-end">
            <div className="text-sm font-bold text-white">${user.balance?.toFixed(2)}</div>
            <div className="text-xs text-gray-500">{lang === 'fa' ? 'موجودی' : 'Balance'}</div>
          </div>
        </div>
      )}

      {/* Warranty */}
      {order.warranty && (
        <div className="rounded-xl px-3 py-2 mb-4 text-xs" style={{ background: 'rgba(132,204,22,0.1)', border: '1px solid rgba(132,204,22,0.2)', color: '#a3e635' }}>
          🛡 {lang === 'fa' ? 'گارانتی فعال' : 'Warranty Active'}
        </div>
      )}

      {/* Delivered content */}
      {order.delivered_content && (
        <div className="mb-4">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            {lang === 'fa' ? 'محتوای تحویل داده شده' : 'Delivered Content'}
          </div>
          <pre
            className="rounded-xl p-4 text-xs overflow-x-auto whitespace-pre-wrap font-mono"
            style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.08))', color: '#a5b4fc', maxHeight: '200px', overflowY: 'auto' }}
          >
            {order.delivered_content}
          </pre>
        </div>
      )}

      {/* Resend */}
      <div>
        {!showResend ? (
          <button onClick={() => setShowResend(true)} className="btn-secondary w-full">
            <Send className="w-4 h-4" /> {lang === 'fa' ? 'ارسال مجدد محتوا' : 'Resend Content'}
          </button>
        ) : (
          <div className="animate-slide-up">
            <label className="form-label">{lang === 'fa' ? 'پیام سفارشی (اختیاری)' : 'Custom message (optional)'}</label>
            <textarea
              value={resendMsg}
              onChange={(e) => setResendMsg(e.target.value)}
              className="input mb-2"
              rows={3}
              placeholder={lang === 'fa' ? 'خالی بگذارید تا محتوای اصلی ارسال شود' : 'Leave empty to resend original content'}
            />
            <div className="flex gap-2">
              <button
                onClick={() => resendMutation.mutate(resendMsg || null)}
                disabled={resendMutation.isPending}
                className="btn-primary flex-1"
              >
                <Send className="w-4 h-4" />
                {resendMutation.isPending ? t('loading', lang) : (lang === 'fa' ? 'ارسال' : 'Send')}
              </button>
              <button onClick={() => setShowResend(false)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}

// ── Stats Modal ──
function StatsModal({ lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['order-stats'],
    queryFn: () => api.get('/orders/stats').then(r => r.data),
  })

  const s = data?.summary

  return (
    <Modal title={lang === 'fa' ? 'آمار سفارش‌ها' : 'Order Statistics'} onClose={onClose} maxWidth="max-w-2xl">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: lang === 'fa' ? 'کل سفارش' : 'Total Orders', value: s?.total_orders, color: '#6366f1' },
              { label: lang === 'fa' ? 'کل درآمد' : 'Total Revenue', value: `$${s?.total_revenue?.toFixed(0)}`, color: '#10b981' },
              { label: lang === 'fa' ? 'میانگین سفارش' : 'Avg Order', value: `$${s?.avg_order_value?.toFixed(2)}`, color: '#8b5cf6' },
              { label: lang === 'fa' ? 'خریداران یکتا' : 'Unique Buyers', value: s?.unique_buyers, color: '#f59e0b' },
            ].map((c, i) => (
              <div key={i} className="rounded-xl p-3 text-center" style={{ background: `${c.color}10`, border: `1px solid ${c.color}25` }}>
                <div className="font-bold text-lg" style={{ color: c.color }}>{c.value}</div>
                <div className="text-xs text-gray-500 mt-0.5">{c.label}</div>
              </div>
            ))}
          </div>

          {/* This week */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl p-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'امروز' : 'Today'}</div>
              <div className="font-bold text-white">{s?.today_orders} {lang === 'fa' ? 'سفارش' : 'orders'}</div>
              <div className="text-sm text-green-400">${s?.today_revenue?.toFixed(2)}</div>
            </div>
            <div className="rounded-xl p-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'این هفته' : 'This Week'}</div>
              <div className="font-bold text-white">{s?.week_orders} {lang === 'fa' ? 'سفارش' : 'orders'}</div>
              <div className="text-sm text-green-400">${s?.week_revenue?.toFixed(2)}</div>
            </div>
          </div>

          {/* Daily chart */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {lang === 'fa' ? 'سفارش‌های ۳۰ روز اخیر' : 'Orders — Last 30 Days'}
            </h4>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={data?.daily || []}>
                <defs>
                  <linearGradient id="orderGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => v?.slice(5)} interval={4} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px' }} />
                <Area type="monotone" dataKey="orders" stroke="#6366f1" strokeWidth={2} fill="url(#orderGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Revenue chart */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {lang === 'fa' ? 'درآمد ۳۰ روز اخیر ($)' : 'Revenue — Last 30 Days ($)'}
            </h4>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={data?.daily || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={v => v?.slice(5)} interval={4} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px' }} />
                <Bar dataKey="revenue" fill="#10b981" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </Modal>
  )
}

// ── Main Orders Page ──
export default function Orders() {
  const { lang } = useApp()
  const { toast } = useToast()
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [sortBy, setSortBy] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [detailOid, setDetailOid] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const limit = 20

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['orders', page, search, dateFrom, dateTo, sortBy],
    queryFn: () => {
      const params = new URLSearchParams({
        offset: page * limit,
        limit,
        ...(search && { search }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
        ...(sortBy && { sort: sortBy }),
      })
      return api.get(`/orders?${params}`).then(r => r.data)
    },
  })

  const handleSearch = (e) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(0)
  }

  const handleExportCSV = () => {
    const params = new URLSearchParams({
      ...(dateFrom && { date_from: dateFrom }),
      ...(dateTo && { date_to: dateTo }),
    })
    downloadFile(`/orders/export.csv?${params}`, 'orders.csv')
    toast(lang === 'fa' ? 'در حال دانلود...' : 'Downloading...', 'info')
  }

  const clearFilters = () => {
    setSearch('')
    setSearchInput('')
    setDateFrom('')
    setDateTo('')
    setSortBy('')
    setPage(0)
  }

  const orders = data?.orders || []
  const total = data?.total || 0
  const hasFilters = search || dateFrom || dateTo || sortBy

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('orders_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} {lang === 'fa' ? 'سفارش' : 'orders'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'آمار' : 'Stats'}>
            <BarChart2 className="w-4 h-4" />
          </button>
          <button onClick={handleExportCSV} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'خروجی CSV' : 'Export CSV'}>
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

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-3">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={lang === 'fa' ? 'جستجو با ID کاربر یا نام کاربری...' : 'Search by user ID or username...'}
          className="input flex-1"
        />
        <button type="submit" className="btn-primary px-4">
          <Search className="w-4 h-4" />
        </button>
        {hasFilters && (
          <button type="button" onClick={clearFilters} className="btn-secondary px-3">
            <X className="w-4 h-4" />
          </button>
        )}
      </form>

      {/* Filters */}
      {showFilters && (
        <div className="card mb-3 animate-slide-up" style={{ borderColor: 'rgba(99,102,241,0.2)' }}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="form-label">{lang === 'fa' ? 'از تاریخ' : 'From Date'}</label>
              <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(0) }} className="input" dir="ltr" />
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'تا تاریخ' : 'To Date'}</label>
              <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(0) }} className="input" dir="ltr" />
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'مرتب‌سازی' : 'Sort By'}</label>
              <select value={sortBy} onChange={(e) => { setSortBy(e.target.value); setPage(0) }} className="input">
                <option value="">{lang === 'fa' ? 'جدیدترین' : 'Newest'}</option>
                <option value="price">{lang === 'fa' ? 'بیشترین قیمت' : 'Highest Price'}</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {detailOid && <OrderDetailModal oid={detailOid} lang={lang} onClose={() => setDetailOid(null)} />}
      {showStats && <StatsModal lang={lang} onClose={() => setShowStats(false)} />}

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : orders.length === 0 ? (
        <div className="card text-center py-16">
          <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-white font-semibold">{t('no_data', lang)}</p>
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-soft, rgba(255,255,255,0.06))', background: 'var(--surface-hover, rgba(255,255,255,0.02))' }}>
                  <th className="table-header">#</th>
                  <th className="table-header">{t('orders_product', lang)}</th>
                  <th className="table-header">{t('user', lang)}</th>
                  <th className="table-header">{t('quantity', lang)}</th>
                  <th className="table-header">{t('price', lang)}</th>
                  <th className="table-header">{t('date', lang)}</th>
                  <th className="table-header">{t('actions', lang)}</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id} className="table-row">
                    <td className="table-cell font-mono text-xs text-gray-400">{o.id}</td>
                    <td className="table-cell">
                      <div className="text-gray-200 text-sm">{o.product_name || o.name}</div>
                      {o.warranty && <span className="text-xs text-green-400">🛡</span>}
                    </td>
                    <td className="table-cell">
                      <div className="text-gray-300 text-sm">@{o.username || 'N/A'}</div>
                      <div className="text-xs text-gray-500 font-mono">{o.user_id}</div>
                    </td>
                    <td className="table-cell text-gray-300">{o.quantity || 1}</td>
                    <td className="table-cell font-semibold text-white">${o.price}</td>
                    <td className="table-cell text-gray-500 text-xs">{o.created_at?.slice(0, 10)}</td>
                    <td className="table-cell">
                      <button
                        onClick={() => setDetailOid(o.id)}
                        className="action-btn action-view"
                        title={lang === 'fa' ? 'مشاهده جزئیات' : 'View Details'}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
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
        </div>
      )}
    </div>
  )
}
