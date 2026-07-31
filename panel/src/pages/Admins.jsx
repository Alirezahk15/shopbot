import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api from '../api/client.js'
import {
  Plus, Trash2, UserCog, Crown, User, X, Edit,
  Activity, BarChart2, Key, Bell, Clock, CheckSquare, Square,
  Shield, Save, Eye, EyeOff
} from 'lucide-react'

const ALL_PERMS = ['products', 'users', 'payments', 'tickets', 'discounts', 'warranty', 'broadcast', 'settings']
const NOTIFY_OPTIONS = ['payments', 'tickets', 'warranty', 'orders', 'deposits']

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

// ── Permission Checkboxes ──
function PermissionSelector({ value, onChange, lang }) {
  const isAll = value === 'all'
  const selected = isAll ? ALL_PERMS : (value || '').split(',').filter(p => p && p !== 'none')

  const toggle = (perm) => {
    if (isAll) {
      // Switch from "all" to specific perms minus this one
      const newPerms = ALL_PERMS.filter(p => p !== perm)
      onChange(newPerms.join(','))
    } else {
      const newPerms = selected.includes(perm)
        ? selected.filter(p => p !== perm)
        : [...selected, perm]
      onChange(newPerms.length === ALL_PERMS.length ? 'all' : (newPerms.join(',') || 'none'))
    }
  }

  const toggleAll = () => {
    onChange(isAll ? 'none' : 'all')
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="form-label mb-0">{t('permissions', lang)}</label>
        <button
          type="button"
          onClick={toggleAll}
          className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
        >
          {isAll ? <CheckSquare className="w-3.5 h-3.5" /> : <Square className="w-3.5 h-3.5" />}
          {lang === 'fa' ? 'همه دسترسی‌ها' : 'All permissions'}
        </button>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {ALL_PERMS.map(perm => {
          const active = isAll || selected.includes(perm)
          return (
            <button
              key={perm}
              type="button"
              onClick={() => toggle(perm)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all"
              style={{
                background: active ? 'rgba(99,102,241,0.15)' : 'var(--surface-hover, rgba(255,255,255,0.04))',
                border: `1px solid ${active ? 'rgba(99,102,241,0.4)' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
                color: active ? '#818cf8' : 'rgba(156,163,175,0.7)',
              }}
            >
              {active ? <CheckSquare className="w-3.5 h-3.5 flex-shrink-0" /> : <Square className="w-3.5 h-3.5 flex-shrink-0" />}
              {perm}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Notification Preferences ──
function NotifySelector({ value, onChange, lang }) {
  const isAll = value === 'all' || !value
  const selected = isAll ? NOTIFY_OPTIONS : (value || '').split(',').filter(o => o && o !== 'none')

  const toggle = (opt) => {
    if (isAll) {
      const newOpts = NOTIFY_OPTIONS.filter(o => o !== opt)
      onChange(newOpts.join(','))
    } else {
      const newOpts = selected.includes(opt)
        ? selected.filter(o => o !== opt)
        : [...selected, opt]
      onChange(newOpts.length === NOTIFY_OPTIONS.length ? 'all' : (newOpts.join(',') || 'none'))
    }
  }

  return (
    <div>
      <label className="form-label">{lang === 'fa' ? 'اعلان‌ها' : 'Notifications'}</label>
      <div className="flex flex-wrap gap-1.5">
        {NOTIFY_OPTIONS.map(opt => {
          const active = isAll || selected.includes(opt)
          return (
            <button
              key={opt}
              type="button"
              onClick={() => toggle(opt)}
              className="px-2.5 py-1 rounded-lg text-xs transition-all"
              style={{
                background: active ? 'rgba(16,185,129,0.15)' : 'var(--surface-hover, rgba(255,255,255,0.04))',
                border: `1px solid ${active ? 'rgba(16,185,129,0.4)' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
                color: active ? '#34d399' : 'rgba(156,163,175,0.7)',
              }}
            >
              {opt}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Add/Edit Admin Modal ──
function AdminFormModal({ admin, lang, onClose, onSave }) {
  const [form, setForm] = useState({
    user_id: admin?.user_id || '',
    permissions: admin?.permissions || 'all',
    expires_at: admin?.expires_at || '',
    notify_prefs: admin?.notify_prefs || 'all',
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onSave({
        ...form,
        user_id: parseInt(form.user_id),
        expires_at: form.expires_at || null,
      })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  const isEdit = !!admin

  return (
    <Modal title={isEdit ? (lang === 'fa' ? 'ویرایش ادمین' : 'Edit Admin') : t('adm_add', lang)} onClose={onClose} maxWidth="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {!isEdit && (
          <div>
            <label className="form-label">{t('adm_uid_ph', lang)}</label>
            <input
              type="number" dir="ltr"
              value={form.user_id}
              onChange={(e) => setForm({ ...form, user_id: e.target.value })}
              className="input"
              placeholder="123456789"
              required
              dir="ltr"
            />
          </div>
        )}

        <PermissionSelector
          value={form.permissions}
          onChange={(v) => setForm({ ...form, permissions: v })}
          lang={lang}
        />

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
              {lang === 'fa' ? 'ادمین موقت — دسترسی بعد از این تاریخ حذف می‌شود' : 'Temporary admin — access removed after this date'}
            </p>
          )}
        </div>

        <NotifySelector
          value={form.notify_prefs}
          onChange={(v) => setForm({ ...form, notify_prefs: v })}
          lang={lang}
        />

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={loading || (!isEdit && !form.user_id)} className="btn-primary flex-1">
            <Save className="w-4 h-4" />
            {loading ? t('loading', lang) : t('save', lang)}
          </button>
          <button type="button" onClick={onClose} className="btn-secondary flex-1">{t('cancel', lang)}</button>
        </div>
      </form>
    </Modal>
  )
}

// ── Activity Log Modal ──
function ActivityLogModal({ adminId, lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-logs', adminId],
    queryFn: () => api.get(`/admins/logs${adminId ? `?admin_id=${adminId}` : ''}`).then(r => r.data),
  })

  const actionColors = {
    payment_approve: '#10b981',
    payment_reject: '#ef4444',
    ticket_reply: '#6366f1',
    warranty_approve: '#84cc16',
    warranty_reject: '#f59e0b',
    admin_add: '#3b82f6',
    admin_remove: '#ef4444',
    admin_update: '#f59e0b',
    password_change: '#ec4899',
  }

  return (
    <Modal title={lang === 'fa' ? 'لاگ فعالیت‌ها' : 'Activity Log'} onClose={onClose} maxWidth="max-w-2xl">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {(data?.logs || []).length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-8">{t('no_data', lang)}</p>
          ) : (
            (data?.logs || []).map(log => (
              <div key={log.id} className="flex items-start gap-3 rounded-xl px-3 py-2.5" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <div
                  className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                  style={{ background: actionColors[log.action] || '#6b7280' }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-400">#{log.admin_id}</span>
                    <span
                      className="text-xs font-semibold"
                      style={{ color: actionColors[log.action] || '#9ca3af' }}
                    >
                      {log.action}
                    </span>
                  </div>
                  {log.detail && <p className="text-xs text-gray-500 mt-0.5 truncate">{log.detail}</p>}
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

// ── Stats Modal ──
function StatsModal({ lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => api.get('/admins/stats').then(r => r.data),
  })

  return (
    <Modal title={lang === 'fa' ? 'آمار عملکرد ادمین‌ها' : 'Admin Performance Stats'} onClose={onClose} maxWidth="max-w-2xl">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-3">
          {(data?.stats || []).map(a => (
            <div key={a.user_id} className="rounded-xl p-4" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
              <div className="flex items-center gap-2 mb-3">
                <div>
                  {a.username && <span className="text-white font-semibold text-sm">@{a.username} </span>}
                  <span className="font-mono text-xs text-gray-500">({a.user_id})</span>
                </div>
                {a.is_super
                  ? <span className="badge-yellow flex items-center gap-1"><Crown className="w-3 h-3" />{t('super_admin', lang)}</span>
                  : <span className="badge-blue flex items-center gap-1"><User className="w-3 h-3" />{t('regular_admin', lang)}</span>
                }
                <span className="text-xs text-gray-500 ms-auto">{lang === 'fa' ? 'مجموع' : 'Total'}: {a.total_actions}</span>
              </div>
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: lang === 'fa' ? 'تیکت' : 'Tickets', value: a.tickets_replied, color: '#6366f1' },
                  { label: lang === 'fa' ? 'تأیید' : 'Approved', value: a.payments_approved, color: '#10b981' },
                  { label: lang === 'fa' ? 'رد' : 'Rejected', value: a.payments_rejected, color: '#ef4444' },
                  { label: lang === 'fa' ? 'گارانتی' : 'Warranty', value: a.warranty_processed, color: '#f59e0b' },
                ].map((s, i) => (
                  <div key={i} className="text-center rounded-lg py-2" style={{ background: `${s.color}10` }}>
                    <div className="font-bold text-sm" style={{ color: s.color }}>{s.value}</div>
                    <div className="text-xs text-gray-500">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  )
}

// ── Change Password Modal ──
function ChangePasswordModal({ lang, onClose }) {
  const { toast } = useToast()
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.new_password !== form.confirm) {
      toast(lang === 'fa' ? 'رمزهای جدید یکسان نیستند' : 'New passwords do not match', 'error')
      return
    }
    setLoading(true)
    try {
      await api.post('/admins/change-password', {
        current_password: form.current_password,
        new_password: form.new_password,
      })
      toast(lang === 'fa' ? 'رمز عبور تغییر کرد — لطفاً دوباره وارد شوید' : 'Password changed — please log in again', 'success')
      setTimeout(() => {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }, 2000)
    } catch (err) {
      toast(err.response?.data?.detail || t('error', lang), 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title={lang === 'fa' ? 'تغییر رمز عبور پنل' : 'Change Panel Password'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="form-label">{lang === 'fa' ? 'رمز فعلی' : 'Current Password'}</label>
          <div className="relative">
            <input
              type={showCurrent ? 'text' : 'password'}
              value={form.current_password}
              onChange={(e) => setForm({ ...form, current_password: e.target.value })}
              className="input"
              style={{ paddingInlineEnd: '40px' }}
              required
              dir="ltr"
            />
            <button type="button" onClick={() => setShowCurrent(!showCurrent)} className="absolute top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300" style={{ insetInlineEnd: '12px' }}>
              {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>
        <div>
          <label className="form-label">{lang === 'fa' ? 'رمز جدید' : 'New Password'}</label>
          <div className="relative">
            <input
              type={showNew ? 'text' : 'password'}
              value={form.new_password}
              onChange={(e) => setForm({ ...form, new_password: e.target.value })}
              className="input"
              style={{ paddingInlineEnd: '40px' }}
              required
              minLength={6}
              dir="ltr"
            />
            <button type="button" onClick={() => setShowNew(!showNew)} className="absolute top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300" style={{ insetInlineEnd: '12px' }}>
              {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>
        <div>
          <label className="form-label">{lang === 'fa' ? 'تکرار رمز جدید' : 'Confirm New Password'}</label>
          <input
            type="password"
            value={form.confirm}
            onChange={(e) => setForm({ ...form, confirm: e.target.value })}
            className="input"
            required
            dir="ltr"
          />
        </div>
        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={loading} className="btn-primary flex-1">
            <Key className="w-4 h-4" />
            {loading ? t('loading', lang) : (lang === 'fa' ? 'تغییر رمز' : 'Change Password')}
          </button>
          <button type="button" onClick={onClose} className="btn-secondary flex-1">{t('cancel', lang)}</button>
        </div>
      </form>
    </Modal>
  )
}

// ── Main Admins Page ──
export default function Admins() {
  const { lang } = useApp()
  const { toast } = useToast()
  const qc = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [editAdmin, setEditAdmin] = useState(null)
  const [confirmModal, setConfirmModal] = useState(null)
  const [showLogs, setShowLogs] = useState(false)
  const [showStats, setShowStats] = useState(false)
  const [showChangePass, setShowChangePass] = useState(false)
  const [credAdmin, setCredAdmin] = useState(null)
  const [logAdminId, setLogAdminId] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admins'],
    queryFn: () => api.get('/admins').then(r => r.data),
  })

  const addMutation = useMutation({
    mutationFn: (body) => api.post('/admins', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admins'] })
      toast(lang === 'fa' ? 'ادمین جدید اضافه شد' : 'Admin added', 'success')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ uid, ...body }) => api.put(`/admins/${uid}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admins'] })
      toast(lang === 'fa' ? 'ادمین بروزرسانی شد' : 'Admin updated', 'success')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: (uid) => api.delete(`/admins/${uid}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admins'] })
      toast(lang === 'fa' ? 'ادمین حذف شد' : 'Admin removed', 'success')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const checkExpiredMutation = useMutation({
    mutationFn: () => api.get('/admins/check-expired'),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['admins'] })
      const count = res.data.count
      toast(
        count > 0
          ? (lang === 'fa' ? `${count} ادمین منقضی‌شده حذف شد` : `${count} expired admin(s) removed`)
          : (lang === 'fa' ? 'هیچ ادمین منقضی‌شده‌ای وجود ندارد' : 'No expired admins found'),
        count > 0 ? 'warning' : 'info'
      )
    },
  })

  const admins = data?.admins || []

  const getPermBadges = (perms) => {
    if (!perms || perms === 'all') return [{ label: 'all', color: '#f59e0b' }]
    if (perms === 'none') return [{ label: lang === 'fa' ? 'بدون دسترسی' : 'none', color: '#6b7280' }]
    return perms.split(',').filter(p => p && p !== 'none').map(p => ({ label: p, color: '#6366f1' }))
  }

  const isExpired = (expiresAt) => {
    if (!expiresAt) return false
    return new Date(expiresAt) < new Date()
  }

  const isExpiringSoon = (expiresAt) => {
    if (!expiresAt) return false
    const diff = new Date(expiresAt) - new Date()
    return diff > 0 && diff < 7 * 24 * 60 * 60 * 1000 // within 7 days
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('adm_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{admins.length} {lang === 'fa' ? 'ادمین' : 'admins'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'آمار عملکرد' : 'Performance Stats'}>
            <BarChart2 className="w-4 h-4" />
          </button>
          <button onClick={() => { setLogAdminId(null); setShowLogs(true) }} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'لاگ فعالیت' : 'Activity Log'}>
            <Activity className="w-4 h-4" />
          </button>
          <button onClick={() => checkExpiredMutation.mutate()} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'بررسی منقضی‌شده‌ها' : 'Check Expired'}>
            <Clock className="w-4 h-4" />
          </button>
          <button onClick={() => setShowChangePass(true)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'تغییر رمز پنل' : 'Change Panel Password'}>
            <Key className="w-4 h-4" />
          </button>
          <button onClick={() => setShowAddForm(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> {t('adm_add', lang)}
          </button>
        </div>
      </div>

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {showAddForm && (
        <AdminFormModal
          lang={lang}
          onClose={() => setShowAddForm(false)}
          onSave={(body) => addMutation.mutateAsync(body)}
        />
      )}
      {editAdmin && (
        <AdminFormModal
          admin={editAdmin}
          lang={lang}
          onClose={() => setEditAdmin(null)}
          onSave={(body) => updateMutation.mutateAsync({ uid: editAdmin.user_id, ...body })}
        />
      )}
      {showLogs && <ActivityLogModal adminId={logAdminId} lang={lang} onClose={() => setShowLogs(false)} />}
      {showStats && <StatsModal lang={lang} onClose={() => setShowStats(false)} />}
      {showChangePass && <ChangePasswordModal lang={lang} onClose={() => setShowChangePass(false)} />}
      {credAdmin && <CredentialsModal admin={credAdmin} lang={lang} onClose={() => setCredAdmin(null)} />}

      {/* Admins list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : admins.length === 0 ? (
        <div className="card text-center py-16">
          <UserCog className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-white font-semibold">{t('no_data', lang)}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {admins.map((a) => {
            const expired = isExpired(a.expires_at)
            const expiringSoon = isExpiringSoon(a.expires_at)
            return (
              <div
                key={a.user_id}
                className="card"
                style={{
                  borderColor: expired ? 'rgba(239,68,68,0.3)' : expiringSoon ? 'rgba(245,158,11,0.3)' : 'var(--surface-hover, rgba(255,255,255,0.08))',
                }}
              >
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{
                      background: a.is_super
                        ? 'linear-gradient(135deg, #f59e0b, #d97706)'
                        : 'linear-gradient(135deg, #6366f1, #4f46e5)',
                    }}
                  >
                    {a.is_super ? <Crown className="w-5 h-5 text-white" /> : <User className="w-5 h-5 text-white" />}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      <div className="flex items-center gap-1.5">
                        {a.username
                          ? <span className="text-white font-semibold text-sm">@{a.username}</span>
                          : <span className="text-gray-400 text-sm">{lang === 'fa' ? 'ناشناس' : 'Unknown'}</span>
                        }
                        <span className="font-mono text-xs text-gray-500">({a.user_id})</span>
                      </div>
                      {a.is_super
                        ? <span className="badge-yellow">{t('super_admin', lang)}</span>
                        : <span className="badge-blue">{t('regular_admin', lang)}</span>
                      }
                      {a.panel_username && <span className="badge-green">{lang === 'fa' ? 'پنل: ' : 'Panel: '}{a.panel_username}</span>}
                      {!!a.totp_enabled && <span className="badge-blue">2FA</span>}
                      {expired && <span className="badge-red">{lang === 'fa' ? 'منقضی' : 'Expired'}</span>}
                      {expiringSoon && !expired && <span className="badge-yellow">{lang === 'fa' ? 'به‌زودی منقضی' : 'Expiring Soon'}</span>}
                    </div>

                    {/* Permissions */}
                    <div className="flex flex-wrap gap-1 mb-2">
                      {getPermBadges(a.permissions).map(({ label, color }) => (
                        <span
                          key={label}
                          className="text-xs px-2 py-0.5 rounded-md font-mono"
                          style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}
                        >
                          {label}
                        </span>
                      ))}
                    </div>

                    {/* Meta */}
                    <div className="flex gap-3 text-xs text-gray-500">
                      <span>{lang === 'fa' ? 'افزوده' : 'Added'}: {a.added_at?.slice(0, 10)}</span>
                      {a.expires_at && (
                        <span style={{ color: expired ? '#f87171' : expiringSoon ? '#fbbf24' : '#6b7280' }}>
                          <Clock className="w-3 h-3 inline me-1" />
                          {lang === 'fa' ? 'انقضا' : 'Expires'}: {a.expires_at}
                        </span>
                      )}
                      {a.notify_prefs && a.notify_prefs !== 'all' && (
                        <span>
                          <Bell className="w-3 h-3 inline me-1" />
                          {a.notify_prefs}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-1 flex-shrink-0">
                    <button
                      onClick={() => { setLogAdminId(a.user_id); setShowLogs(true) }}
                      className="action-btn action-view"
                      title={lang === 'fa' ? 'لاگ فعالیت' : 'Activity Log'}
                    >
                      <Activity className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setEditAdmin(a)}
                      className="action-btn action-warning"
                      title={t('edit', lang)}
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setCredAdmin(a)}
                      className="action-btn action-info"
                      title={lang === 'fa' ? 'اطلاعات ورود پنل' : 'Panel Credentials'}
                    >
                      <Key className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setConfirmModal({
                        title: lang === 'fa' ? 'حذف ادمین' : 'Remove Admin',
                        message: lang === 'fa' ? `ادمین ${a.user_id} حذف شود؟` : `Remove admin ${a.user_id}?`,
                        type: 'danger',
                        onConfirm: () => deleteMutation.mutate(a.user_id),
                      })}
                      className="action-btn action-danger"
                      title={t('adm_remove', lang)}
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

// ── Panel Credentials Modal ──
function CredentialsModal({ admin, lang, onClose }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const fa = lang === 'fa'
  const [username, setUsername] = useState(admin.panel_username || '')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [resetTotp, setResetTotp] = useState(false)
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (body) => api.patch(`/admins/${admin.user_id}/credentials`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admins'] })
      toast(fa ? 'اطلاعات ورود پنل ذخیره شد' : 'Panel credentials saved', 'success')
      onClose()
    },
    onError: (err) => {
      const detail = String(err.response?.data?.detail || '')
      let msg = detail || (fa ? 'خطا در ذخیره' : 'Save failed')
      if (fa) {
        if (detail.includes('taken')) msg = 'این نام کاربری قبلاً استفاده شده است'
        else if (detail.includes('Username must')) msg = 'نام کاربری باید حداقل ۳ کاراکتر باشد'
        else if (detail.includes('Password must')) msg = 'رمز عبور باید حداقل ۶ کاراکتر باشد'
        else if (err.response?.status === 403) msg = 'فقط سوپرادمین می‌تواند این کار را انجام دهد'
      }
      setError(msg)
    },
  })

  const submit = (e) => {
    e.preventDefault()
    setError('')
    const body = { username: username.trim(), reset_totp: resetTotp }
    if (password) body.password = password
    mutation.mutate(body)
  }

  return (
    <Modal
      title={(fa ? 'اطلاعات ورود پنل — ' : 'Panel Credentials — ') + (admin.username ? '@' + admin.username : admin.user_id)}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-4">
        {error && (
          <div className="login-alert" style={{ padding: '10px 12px' }}>
            <span>{error}</span>
          </div>
        )}
        <p className="text-xs leading-relaxed" style={{ color: 'var(--text-dim, #9ca3af)' }}>
          {fa
            ? 'با تعریف نام کاربری و رمز، این ادمین با حساب خودش وارد پنل می‌شود و فقط به بخش‌های مجازش دسترسی دارد.'
            : 'With credentials set, this admin signs in with their own account and only sees allowed sections.'}
        </p>
        <div>
          <label className="form-label">{fa ? 'نام کاربری پنل' : 'Panel username'}</label>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="input" dir="ltr" placeholder="admin_user" />
        </div>
        <div>
          <label className="form-label">{fa ? 'رمز عبور جدید' : 'New password'}</label>
          <div className="relative">
            <input
              type={showPass ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              style={{ paddingInlineEnd: '40px' }}
              dir="ltr"
              placeholder={fa ? 'خالی = بدون تغییر' : 'empty = unchanged'}
            />
            <button
              type="button"
              onClick={() => setShowPass(!showPass)}
              className="absolute top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-300"
              style={{ insetInlineEnd: '12px' }}
            >
              {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>
        {!!admin.totp_enabled && (
          <button
            type="button"
            onClick={() => setResetTotp(!resetTotp)}
            className="flex items-center gap-2 text-xs"
            style={{ color: resetTotp ? '#f87171' : 'var(--text-dim, #9ca3af)' }}
          >
            {resetTotp ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
            {fa ? 'ریست تأیید دومرحله‌ای (2FA) این ادمین' : "Reset this admin's 2FA"}
          </button>
        )}
        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={mutation.isPending} className="btn-primary flex-1">
            <Save className="w-4 h-4" />
            {fa ? 'ذخیره' : 'Save'}
          </button>
          <button type="button" onClick={onClose} className="btn-secondary flex-1">
            {fa ? 'انصراف' : 'Cancel'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
