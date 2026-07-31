import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api from '../api/client.js'
import {
  Plus, Trash2, ToggleLeft, ToggleRight, Wallet, X,
  Edit, BarChart2, History, ChevronUp, ChevronDown,
  DollarSign, MessageSquare, Save, TrendingUp, CreditCard
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

// ── Method Form (Add/Edit) ──
function MethodFormModal({ method, lang, onClose, onSave }) {
  const [form, setForm] = useState({
    name: method?.name || '',
    details: method?.details || '',
    min_amount: method?.min_amount || 0,
    max_amount: method?.max_amount || 0,
    guide_message: method?.guide_message || '',
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onSave(form)
      onClose()
    } finally {
      setLoading(false)
    }
  }

  const isEdit = !!method

  return (
    <Modal title={isEdit ? (lang === 'fa' ? 'ویرایش روش پرداخت' : 'Edit Payment Method') : t('pm_add', lang)} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {!isEdit && (
          <div>
            <label className="form-label">{t('name', lang)}</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input"
              placeholder={t('pm_name_ph', lang)}
              required
              dir="ltr"
            />
          </div>
        )}

        <div>
          <label className="form-label">{t('description', lang)}</label>
          <input
            value={form.details}
            onChange={(e) => setForm({ ...form, details: e.target.value })}
            className="input"
            placeholder={t('pm_details_ph', lang)}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="form-label">{lang === 'fa' ? 'حداقل مبلغ ($)' : 'Min Amount ($)'}</label>
            <input
              type="number" dir="ltr" step="0.01" min="0"
              value={form.min_amount}
              onChange={(e) => setForm({ ...form, min_amount: parseFloat(e.target.value) || 0 })}
              className="input"
              placeholder="0"
              dir="ltr"
            />
            <p className="text-xs text-gray-500 mt-1">{lang === 'fa' ? '۰ = بدون محدودیت' : '0 = no limit'}</p>
          </div>
          <div>
            <label className="form-label">{lang === 'fa' ? 'حداکثر مبلغ ($)' : 'Max Amount ($)'}</label>
            <input
              type="number" dir="ltr" step="0.01" min="0"
              value={form.max_amount}
              onChange={(e) => setForm({ ...form, max_amount: parseFloat(e.target.value) || 0 })}
              className="input"
              placeholder="0"
              dir="ltr"
            />
            <p className="text-xs text-gray-500 mt-1">{lang === 'fa' ? '۰ = بدون محدودیت' : '0 = no limit'}</p>
          </div>
        </div>

        <div>
          <label className="form-label">{lang === 'fa' ? 'پیام راهنمای سفارشی (اختیاری)' : 'Custom Guide Message (optional)'}</label>
          <textarea
            value={form.guide_message}
            onChange={(e) => setForm({ ...form, guide_message: e.target.value })}
            className="input"
            rows={3}
            placeholder={lang === 'fa' ? 'پیام راهنما برای کاربران...' : 'Guide message for users...'}
          />
          <p className="text-xs text-gray-500 mt-1">{lang === 'fa' ? 'اگر خالی باشد، پیام پیش‌فرض نمایش داده می‌شود' : 'If empty, default message is shown'}</p>
        </div>

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={loading} className="btn-primary flex-1">
            <Save className="w-4 h-4" />
            {loading ? t('loading', lang) : (isEdit ? t('save', lang) : t('add', lang))}
          </button>
          <button type="button" onClick={onClose} className="btn-secondary flex-1">{t('cancel', lang)}</button>
        </div>
      </form>
    </Modal>
  )
}

// ── Stats Modal ──
function StatsModal({ lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['method-stats'],
    queryFn: () => api.get('/methods/stats').then(r => r.data),
  })

  const methodColors = {
    usdt: '#10b981',
    card: '#f59e0b',
  }

  return (
    <Modal title={lang === 'fa' ? 'آمار روش‌های پرداخت' : 'Payment Method Statistics'} onClose={onClose} maxWidth="max-w-lg">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          {(data?.stats || []).map((m) => {
            const color = methodColors[m.name] || '#6366f1'
            const approvalRate = m.total_transactions > 0
              ? Math.round((m.approved_transactions / m.total_transactions) * 100)
              : 0

            return (
              <div key={m.id} className="rounded-xl p-4" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: `${color}15`, border: `1px solid ${color}30` }}
                  >
                    {m.name === 'card' ? <CreditCard className="w-5 h-5" style={{ color }} /> : <DollarSign className="w-5 h-5" style={{ color }} />}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-white">{m.name.toUpperCase()}</div>
                    <div className="text-xs text-gray-500">{m.details}</div>
                  </div>
                  <div className="text-end">
                    <div className="font-bold text-white">${m.total_amount?.toFixed(2)}</div>
                    <div className="text-xs text-gray-500">{lang === 'fa' ? 'مجموع' : 'Total'}</div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  {[
                    { label: lang === 'fa' ? 'کل تراکنش' : 'Total', value: m.total_transactions, color: '#6366f1' },
                    { label: lang === 'fa' ? 'تأیید شده' : 'Approved', value: m.approved_transactions, color: '#10b981' },
                    { label: lang === 'fa' ? 'نرخ تأیید' : 'Approval Rate', value: `${approvalRate}%`, color: color },
                  ].map((s, i) => (
                    <div key={i} className="rounded-lg p-2 text-center" style={{ background: `${s.color}10` }}>
                      <div className="font-bold text-sm" style={{ color: s.color }}>{s.value}</div>
                      <div className="text-xs text-gray-500">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Modal>
  )
}

// ── Logs Modal ──
function LogsModal({ method, lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['method-logs', method.id],
    queryFn: () => api.get(`/methods/${method.id}/logs`).then(r => r.data),
  })

  const actionColors = {
    add: '#10b981',
    update: '#6366f1',
    toggle: '#f59e0b',
    delete: '#ef4444',
  }

  return (
    <Modal title={`${lang === 'fa' ? 'تاریخچه تغییرات' : 'Change History'}: ${method.name}`} onClose={onClose}>
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {(data?.logs || []).length === 0 ? (
            <p className="text-center text-gray-500 text-sm py-6">{t('no_data', lang)}</p>
          ) : (
            (data?.logs || []).map(log => (
              <div key={log.id} className="flex items-start gap-3 rounded-xl px-3 py-2.5" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <div
                  className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                  style={{ background: actionColors[log.action] || '#6b7280' }}
                />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-semibold" style={{ color: actionColors[log.action] || '#9ca3af' }}>
                    {log.action}
                  </span>
                  {log.detail && <p className="text-xs text-gray-500 mt-0.5">{log.detail}</p>}
                </div>
                <span className="text-xs text-gray-600 flex-shrink-0">{log.created_at?.slice(0, 16)}</span>
              </div>
            ))
          )}
        </div>
      )}
    </Modal>
  )
}

// ── Main Methods Page ──
export default function Methods() {
  const { lang } = useApp()
  const { toast } = useToast()
  const qc = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editMethod, setEditMethod] = useState(null)
  const [logsMethod, setLogsMethod] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const [confirmModal, setConfirmModal] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['methods'],
    queryFn: () => api.get('/methods').then(r => r.data),
  })

  const addMutation = useMutation({
    mutationFn: (body) => api.post('/methods', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['methods'] }); toast(lang === 'fa' ? 'روش پرداخت اضافه شد' : 'Payment method added', 'success') },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }) => api.put(`/methods/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['methods'] }); toast(lang === 'fa' ? 'روش پرداخت بروزرسانی شد' : 'Method updated', 'success') },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const toggleMutation = useMutation({
    mutationFn: (id) => api.post(`/methods/${id}/toggle`),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['methods'] })
      toast(res.data.active ? (lang === 'fa' ? 'روش فعال شد' : 'Method activated') : (lang === 'fa' ? 'روش غیرفعال شد' : 'Method deactivated'), res.data.active ? 'success' : 'warning')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/methods/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['methods'] }); toast(lang === 'fa' ? 'روش پرداخت حذف شد' : 'Method deleted', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const reorderMutation = useMutation({
    mutationFn: (orderedIds) => api.post('/methods/reorder', { ordered_ids: orderedIds }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['methods'] }); toast(lang === 'fa' ? 'ترتیب ذخیره شد' : 'Order saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const methods = data?.methods || []

  const moveMethod = (index, direction) => {
    const newMethods = [...methods]
    const targetIndex = index + direction
    if (targetIndex < 0 || targetIndex >= newMethods.length) return
    ;[newMethods[index], newMethods[targetIndex]] = [newMethods[targetIndex], newMethods[index]]
    reorderMutation.mutate(newMethods.map(m => m.id))
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('pm_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{methods.length} {lang === 'fa' ? 'روش' : 'methods'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'آمار' : 'Stats'}>
            <BarChart2 className="w-4 h-4" />
          </button>
          <button onClick={() => setShowAddForm(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> {t('pm_add', lang)}
          </button>
        </div>
      </div>

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {showAddForm && (
        <MethodFormModal
          lang={lang}
          onClose={() => setShowAddForm(false)}
          onSave={(body) => addMutation.mutateAsync(body)}
        />
      )}
      {editMethod && (
        <MethodFormModal
          method={editMethod}
          lang={lang}
          onClose={() => setEditMethod(null)}
          onSave={(body) => updateMutation.mutateAsync({ id: editMethod.id, ...body })}
        />
      )}
      {logsMethod && <LogsModal method={logsMethod} lang={lang} onClose={() => setLogsMethod(null)} />}
      {showStats && <StatsModal lang={lang} onClose={() => setShowStats(false)} />}

      {/* Methods list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : methods.length === 0 ? (
        <div className="card text-center py-16">
          <Wallet className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-white font-semibold">{t('no_data', lang)}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {methods.map((m, index) => (
            <div
              key={m.id}
              className="card"
              style={{
                borderColor: !m.active ? 'rgba(107,114,128,0.3)' : 'var(--surface-hover, rgba(255,255,255,0.08))',
                opacity: !m.active ? 0.7 : 1,
              }}
            >
              <div className="flex items-start gap-4">
                {/* Order controls */}
                <div className="flex flex-col gap-1 flex-shrink-0">
                  <button
                    onClick={() => moveMethod(index, -1)}
                    disabled={index === 0}
                    className="action-btn action-neutral disabled:opacity-20"
                    title={lang === 'fa' ? 'بالاتر' : 'Move Up'}
                  >
                    <ChevronUp className="w-4 h-4" />
                  </button>
                  <span className="text-xs text-gray-600 text-center">{index + 1}</span>
                  <button
                    onClick={() => moveMethod(index, 1)}
                    disabled={index === methods.length - 1}
                    className="action-btn action-neutral disabled:opacity-20"
                    title={lang === 'fa' ? 'پایین‌تر' : 'Move Down'}
                  >
                    <ChevronDown className="w-4 h-4" />
                  </button>
                </div>

                {/* Icon */}
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{
                    background: m.name === 'card' ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)',
                    border: `1px solid ${m.name === 'card' ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)'}`,
                  }}
                >
                  {m.name === 'card'
                    ? <CreditCard className="w-6 h-6" style={{ color: '#f59e0b' }} />
                    : <DollarSign className="w-6 h-6" style={{ color: '#10b981' }} />
                  }
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold text-white">{m.name.toUpperCase()}</span>
                    {m.active
                      ? <span className="badge-green">{t('active', lang)}</span>
                      : <span className="badge-red">{t('inactive', lang)}</span>
                    }
                  </div>
                  {m.details && <p className="text-sm text-gray-400 mb-1">{m.details}</p>}

                  {/* Limits */}
                  <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                    {m.min_amount > 0 && (
                      <span className="flex items-center gap-1">
                        <DollarSign className="w-3 h-3" />
                        {lang === 'fa' ? 'حداقل' : 'Min'}: ${m.min_amount}
                      </span>
                    )}
                    {m.max_amount > 0 && (
                      <span className="flex items-center gap-1">
                        <DollarSign className="w-3 h-3" />
                        {lang === 'fa' ? 'حداکثر' : 'Max'}: ${m.max_amount}
                      </span>
                    )}
                    {m.guide_message && (
                      <span className="flex items-center gap-1 text-indigo-400">
                        <MessageSquare className="w-3 h-3" />
                        {lang === 'fa' ? 'پیام سفارشی' : 'Custom message'}
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-1 flex-shrink-0">
                  <button onClick={() => setLogsMethod(m)} className="action-btn action-view" title={lang === 'fa' ? 'تاریخچه' : 'History'}>
                    <History className="w-4 h-4" />
                  </button>
                  <button onClick={() => setEditMethod(m)} className="action-btn action-warning" title={t('edit', lang)}>
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => toggleMutation.mutate(m.id)}
                    className={`action-btn ${m.active ? 'action-success' : 'action-neutral'}`}
                    title={m.active ? (lang === 'fa' ? 'غیرفعال کردن' : 'Deactivate') : (lang === 'fa' ? 'فعال کردن' : 'Activate')}
                  >
                    {m.active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => setConfirmModal({
                      title: lang === 'fa' ? 'حذف روش پرداخت' : 'Delete Payment Method',
                      message: lang === 'fa' ? `روش "${m.name}" حذف شود؟` : `Delete method "${m.name}"?`,
                      type: 'danger',
                      onConfirm: () => deleteMutation.mutate(m.id),
                    })}
                    className="action-btn action-danger"
                    title={t('delete', lang)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}

          {/* Reorder hint */}
          <p className="text-xs text-gray-600 text-center mt-2">
            {lang === 'fa' ? '↑↓ برای تغییر ترتیب نمایش به کاربران' : '↑↓ to change display order for users'}
          </p>
        </div>
      )}
    </div>
  )
}
