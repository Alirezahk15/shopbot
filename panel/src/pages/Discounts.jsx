import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api, { downloadFile } from '../api/client.js'
import {
  Plus, Trash2, Tag, X, Edit, ToggleLeft, ToggleRight,
  RefreshCw, Download, History, Clock, Package, CheckCircle
} from 'lucide-react'

// ── Modal wrapper ──
function Modal({ title, onClose, children, maxWidth = 'max-w-md' }) {
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

// ── Discount Form (Add/Edit) ──
function DiscountFormModal({ discount, products, lang, onClose, onSave }) {
  const [form, setForm] = useState({
    code: discount?.code || '',
    percent: discount?.percent || '',
    max_uses: discount?.max_uses || '',
    expires_at: discount?.expires_at || '',
    product_ids: discount?.product_ids || '',
  })
  const [loading, setLoading] = useState(false)
  const [selectedProducts, setSelectedProducts] = useState(
    discount?.product_ids ? discount.product_ids.split(',').map(Number) : []
  )

  const toggleProduct = (pid) => {
    setSelectedProducts(prev =>
      prev.includes(pid) ? prev.filter(p => p !== pid) : [...prev, pid]
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onSave({
        ...form,
        percent: parseInt(form.percent),
        max_uses: parseInt(form.max_uses),
        expires_at: form.expires_at || null,
        product_ids: selectedProducts.length > 0 ? selectedProducts.join(',') : null,
      })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  const isEdit = !!discount

  return (
    <Modal title={isEdit ? (lang === 'fa' ? 'ویرایش کد تخفیف' : 'Edit Discount Code') : t('disc_add', lang)} onClose={onClose} maxWidth="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {!isEdit && (
          <div>
            <label className="form-label">{t('disc_code', lang)}</label>
            <input
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
              className="input"
              placeholder={t('disc_code_ph', lang)}
              required
              dir="ltr"
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="form-label">{t('disc_percent', lang)} (%)</label>
            <input
              type="number" dir="ltr" min="1" max="100"
              value={form.percent}
              onChange={(e) => setForm({ ...form, percent: e.target.value })}
              className="input"
              placeholder="20"
              required
              dir="ltr"
            />
          </div>
          <div>
            <label className="form-label">{t('disc_max_uses', lang)}</label>
            <input
              type="number" dir="ltr" min="1"
              value={form.max_uses}
              onChange={(e) => setForm({ ...form, max_uses: e.target.value })}
              className="input"
              placeholder="100"
              required
              dir="ltr"
            />
          </div>
        </div>

        <div>
          <label className="form-label">
            {lang === 'fa' ? 'تاریخ انقضا (اختیاری)' : 'Expiry Date (optional)'}
          </label>
          <input
            type="date"
            value={form.expires_at || ''}
            onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
            className="input"
            dir="ltr"
          />
          {form.expires_at && (
            <p className="text-xs text-yellow-400 mt-1 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {lang === 'fa' ? 'کد بعد از این تاریخ غیرفعال می‌شود' : 'Code will be deactivated after this date'}
            </p>
          )}
        </div>

        {/* Product restriction */}
        <div>
          <label className="form-label">
            {lang === 'fa' ? 'محدودیت محصول (اختیاری)' : 'Product Restriction (optional)'}
          </label>
          <p className="text-xs text-gray-500 mb-2">
            {lang === 'fa' ? 'اگر انتخاب نکنید، برای همه محصولات اعمال می‌شود' : 'If none selected, applies to all products'}
          </p>
          <div className="max-h-32 overflow-y-auto space-y-1.5 rounded-xl p-2" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
            {products.map(p => (
              <button
                key={p.id}
                type="button"
                onClick={() => toggleProduct(p.id)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all"
                style={{
                  background: selectedProducts.includes(p.id) ? 'rgba(99,102,241,0.15)' : 'transparent',
                  color: selectedProducts.includes(p.id) ? '#818cf8' : 'rgba(156,163,175,0.8)',
                }}
              >
                <div
                  className="w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0"
                  style={{
                    borderColor: selectedProducts.includes(p.id) ? '#6366f1' : 'rgba(107,114,128,0.5)',
                    background: selectedProducts.includes(p.id) ? '#6366f1' : 'transparent',
                  }}
                >
                  {selectedProducts.includes(p.id) && <CheckCircle className="w-2.5 h-2.5 text-white" />}
                </div>
                <span className="truncate">{p.name}</span>
                <span className="ms-auto text-gray-500">${p.price}</span>
              </button>
            ))}
          </div>
          {selectedProducts.length > 0 && (
            <p className="text-xs text-indigo-400 mt-1">
              {selectedProducts.length} {lang === 'fa' ? 'محصول انتخاب شده' : 'products selected'}
            </p>
          )}
        </div>

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={loading} className="btn-primary flex-1">
            {loading ? t('loading', lang) : (isEdit ? t('save', lang) : t('add', lang))}
          </button>
          <button type="button" onClick={onClose} className="btn-secondary flex-1">{t('cancel', lang)}</button>
        </div>
      </form>
    </Modal>
  )
}

// ── Usage History Modal ──
function UsageModal({ code, lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['discount-usage', code],
    queryFn: () => api.get(`/discounts/${code}/usage`).then(r => r.data),
  })

  return (
    <Modal title={`${lang === 'fa' ? 'تاریخچه استفاده' : 'Usage History'}: ${code}`} onClose={onClose} maxWidth="max-w-lg">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[
              { label: lang === 'fa' ? 'استفاده شده' : 'Used', value: data?.code?.used || 0, color: '#6366f1' },
              { label: lang === 'fa' ? 'حداکثر' : 'Max', value: data?.code?.max_uses || 0, color: '#f59e0b' },
              { label: lang === 'fa' ? 'باقی‌مانده' : 'Remaining', value: Math.max(0, (data?.code?.max_uses || 0) - (data?.code?.used || 0)), color: '#10b981' },
            ].map((s, i) => (
              <div key={i} className="rounded-xl p-3 text-center" style={{ background: `${s.color}10`, border: `1px solid ${s.color}25` }}>
                <div className="font-bold text-lg" style={{ color: s.color }}>{s.value}</div>
                <div className="text-xs text-gray-500">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Usage list */}
          {(data?.usage || []).length === 0 ? (
            <p className="text-center text-gray-500 text-sm py-6">{t('no_data', lang)}</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {(data?.usage || []).map(u => (
                <div key={u.id} className="flex items-center gap-3 rounded-xl px-3 py-2" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-gray-200">@{u.username || u.user_id}</div>
                    <div className="text-xs text-gray-500 font-mono">{u.user_id}</div>
                  </div>
                  <div className="text-xs text-gray-500">{u.used_at?.slice(0, 16)}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </Modal>
  )
}

// ── Main Discounts Page ──
export default function Discounts() {
  const { lang } = useApp()
  const { toast } = useToast()
  const qc = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editDiscount, setEditDiscount] = useState(null)
  const [usageCode, setUsageCode] = useState(null)
  const [confirmModal, setConfirmModal] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['discounts'],
    queryFn: () => api.get('/discounts').then(r => r.data),
  })

  const { data: prodData } = useQuery({
    queryKey: ['products-simple'],
    queryFn: () => api.get('/products').then(r => r.data),
  })

  const addMutation = useMutation({
    mutationFn: (body) => api.post('/discounts', body),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['discounts'] })
      toast(lang === 'fa' ? `کد ${res.data.code} اضافه شد` : `Code ${res.data.code} added`, 'success')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ code, ...body }) => api.put(`/discounts/${code}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['discounts'] })
      toast(lang === 'fa' ? 'کد تخفیف بروزرسانی شد' : 'Discount code updated', 'success')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const toggleMutation = useMutation({
    mutationFn: (code) => api.post(`/discounts/${code}/toggle`),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['discounts'] })
      toast(res.data.active ? (lang === 'fa' ? 'کد فعال شد' : 'Code activated') : (lang === 'fa' ? 'کد غیرفعال شد' : 'Code deactivated'), res.data.active ? 'success' : 'warning')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const resetMutation = useMutation({
    mutationFn: (code) => api.post(`/discounts/${code}/reset`),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['discounts'] })
      toast(lang === 'fa' ? `استفاده از ${res.data.reset_from} به ۰ ریست شد` : `Usage reset from ${res.data.reset_from} to 0`, 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: (code) => api.delete(`/discounts/${code}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['discounts'] })
      toast(lang === 'fa' ? 'کد تخفیف حذف شد' : 'Discount code deleted', 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const checkExpiredMutation = useMutation({
    mutationFn: () => api.get('/discounts/check-expired'),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['discounts'] })
      const count = res.data.count
      toast(
        count > 0
          ? (lang === 'fa' ? `${count} کد منقضی‌شده غیرفعال شد` : `${count} expired code(s) deactivated`)
          : (lang === 'fa' ? 'هیچ کد منقضی‌شده‌ای وجود ندارد' : 'No expired codes found'),
        count > 0 ? 'warning' : 'info'
      )
    },
  })

  const handleExportCSV = () => {
    downloadFile('/discounts/export.csv', 'discounts.csv')
    toast(lang === 'fa' ? 'در حال دانلود...' : 'Downloading...', 'info')
  }

  const discounts = data?.discounts || []
  const products = prodData?.products || []

  const isExpired = (d) => d.expires_at && new Date(d.expires_at) < new Date()
  const isExpiringSoon = (d) => {
    if (!d.expires_at) return false
    const diff = new Date(d.expires_at) - new Date()
    return diff > 0 && diff < 7 * 24 * 60 * 60 * 1000
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('disc_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{discounts.length} {lang === 'fa' ? 'کد تخفیف' : 'codes'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => checkExpiredMutation.mutate()} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'بررسی منقضی‌شده‌ها' : 'Check Expired'}>
            <Clock className="w-4 h-4" />
          </button>
          <button onClick={handleExportCSV} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'خروجی CSV' : 'Export CSV'}>
            <Download className="w-4 h-4" />
          </button>
          <button onClick={() => setShowAddForm(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> {t('disc_add', lang)}
          </button>
        </div>
      </div>

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {showAddForm && (
        <DiscountFormModal
          products={products}
          lang={lang}
          onClose={() => setShowAddForm(false)}
          onSave={(body) => addMutation.mutateAsync(body)}
        />
      )}
      {editDiscount && (
        <DiscountFormModal
          discount={editDiscount}
          products={products}
          lang={lang}
          onClose={() => setEditDiscount(null)}
          onSave={(body) => updateMutation.mutateAsync({ code: editDiscount.code, ...body })}
        />
      )}
      {usageCode && <UsageModal code={usageCode} lang={lang} onClose={() => setUsageCode(null)} />}

      {/* Discounts list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : discounts.length === 0 ? (
        <div className="card text-center py-16">
          <Tag className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-white font-semibold">{t('no_data', lang)}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {discounts.map((d) => {
            const expired = isExpired(d)
            const expiringSoon = isExpiringSoon(d)
            const usagePct = d.max_uses > 0 ? Math.min(100, ((d.used || 0) / d.max_uses) * 100) : 0

            return (
              <div
                key={d.code}
                className="card"
                style={{
                  borderColor: expired ? 'rgba(239,68,68,0.3)' : !d.active ? 'rgba(107,114,128,0.3)' : expiringSoon ? 'rgba(245,158,11,0.3)' : 'var(--surface-hover, rgba(255,255,255,0.08))',
                  opacity: !d.active ? 0.7 : 1,
                }}
              >
                <div className="flex items-start gap-4">
                  {/* Code badge */}
                  <div
                    className="rounded-xl px-3 py-2 flex-shrink-0 text-center min-w-[80px]"
                    style={{
                      background: d.active && !expired ? 'rgba(6,182,212,0.1)' : 'rgba(107,114,128,0.1)',
                      border: `1px solid ${d.active && !expired ? 'rgba(6,182,212,0.3)' : 'rgba(107,114,128,0.3)'}`,
                    }}
                  >
                    <div
                      className="font-mono font-bold text-sm"
                      style={{ color: d.active && !expired ? '#22d3ee' : '#6b7280' }}
                    >
                      {d.code}
                    </div>
                    <div
                      className="text-lg font-bold mt-0.5"
                      style={{ color: d.active && !expired ? '#22d3ee' : '#6b7280' }}
                    >
                      {d.percent}%
                    </div>
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    {/* Badges */}
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {!d.active && <span className="badge-gray">{lang === 'fa' ? 'غیرفعال' : 'Inactive'}</span>}
                      {expired && <span className="badge-red">{lang === 'fa' ? 'منقضی' : 'Expired'}</span>}
                      {expiringSoon && !expired && <span className="badge-yellow">{lang === 'fa' ? 'به‌زودی منقضی' : 'Expiring Soon'}</span>}
                      {d.product_ids && (
                        <span className="badge-blue flex items-center gap-1">
                          <Package className="w-3 h-3" />
                          {d.product_ids.split(',').length} {lang === 'fa' ? 'محصول' : 'products'}
                        </span>
                      )}
                    </div>

                    {/* Usage progress */}
                    <div className="mb-2">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-gray-400">{lang === 'fa' ? 'استفاده' : 'Usage'}</span>
                        <span className={d.used >= d.max_uses ? 'text-red-400' : 'text-gray-400'}>
                          {d.used} / {d.max_uses}
                        </span>
                      </div>
                      <div className="h-1.5 rounded-full" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.08))' }}>
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${usagePct}%`,
                            background: usagePct >= 100 ? '#ef4444' : usagePct >= 80 ? '#f59e0b' : '#6366f1',
                          }}
                        />
                      </div>
                    </div>

                    {/* Meta */}
                    <div className="flex gap-3 text-xs text-gray-500">
                      {d.expires_at && (
                        <span style={{ color: expired ? '#f87171' : expiringSoon ? '#fbbf24' : '#6b7280' }}>
                          <Clock className="w-3 h-3 inline me-1" />
                          {lang === 'fa' ? 'انقضا' : 'Expires'}: {d.expires_at}
                        </span>
                      )}
                      {d.created_at && (
                        <span>{lang === 'fa' ? 'ایجاد' : 'Created'}: {d.created_at?.slice(0, 10)}</span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-1 flex-shrink-0">
                    <button onClick={() => setUsageCode(d.code)} className="action-btn action-view" title={lang === 'fa' ? 'تاریخچه استفاده' : 'Usage History'}>
                      <History className="w-4 h-4" />
                    </button>
                    <button onClick={() => setEditDiscount(d)} className="action-btn action-warning" title={t('edit', lang)}>
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => toggleMutation.mutate(d.code)}
                      className={`action-btn ${d.active ? 'action-success' : 'action-neutral'}`}
                      title={d.active ? (lang === 'fa' ? 'غیرفعال کردن' : 'Deactivate') : (lang === 'fa' ? 'فعال کردن' : 'Activate')}
                    >
                      {d.active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => setConfirmModal({
                        title: lang === 'fa' ? 'ریست استفاده' : 'Reset Usage',
                        message: lang === 'fa' ? `تعداد استفاده کد "${d.code}" به ۰ ریست شود؟` : `Reset usage count of "${d.code}" to 0?`,
                        type: 'warning',
                        onConfirm: () => resetMutation.mutate(d.code),
                      })}
                      className="action-btn action-warning"
                      title={lang === 'fa' ? 'ریست استفاده' : 'Reset Usage'}
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setConfirmModal({
                        title: lang === 'fa' ? 'حذف کد تخفیف' : 'Delete Discount Code',
                        message: lang === 'fa' ? `کد "${d.code}" حذف شود؟` : `Delete code "${d.code}"?`,
                        type: 'danger',
                        onConfirm: () => deleteMutation.mutate(d.code),
                      })}
                      className="action-btn action-danger"
                      title={t('delete', lang)}
                    >
                      <Trash2 className="w-4 h-4" />
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
