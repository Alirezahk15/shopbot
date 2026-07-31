import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api from '../api/client.js'
import {
  Lock as LockIcon, Unlock, Plus, X, Edit, Clock,
  Link, MessageSquare, Users, Copy, CheckCircle,
  RefreshCw, Save, ExternalLink
} from 'lucide-react'

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

// ── Add/Edit Lock Modal ──
function LockFormModal({ item, type, lang, onClose, onSave }) {
  const [form, setForm] = useState({
    id: item?.channel_id || item?.group_id || '',
    title: item?.title || '',
    invite_link: item?.invite_link || '',
    custom_message: item?.custom_message || '',
    expires_at: item?.expires_at || '',
  })
  const [loading, setLoading] = useState(false)
  const [fetchingInfo, setFetchingInfo] = useState(false)

  const isEdit = !!item

  const fetchTelegramInfo = async () => {
    if (!form.id) return
    setFetchingInfo(true)
    try {
      const endpoint = type === 'channel' ? `/lock/channel/${form.id}/info` : `/lock/group/${form.id}/info`
      const res = await api.get(endpoint)
      const info = res.data
      setForm(prev => ({
        ...prev,
        title: info.title || prev.title,
        invite_link: info.invite_link || prev.invite_link,
      }))
    } catch (err) {
      // ignore
    } finally {
      setFetchingInfo(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onSave({ ...form, id: parseInt(form.id), expires_at: form.expires_at || null })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  const typeLabel = type === 'channel' ? (lang === 'fa' ? 'کانال' : 'Channel') : (lang === 'fa' ? 'گروه' : 'Group')

  return (
    <Modal title={isEdit ? `${lang === 'fa' ? 'ویرایش' : 'Edit'} ${typeLabel}` : `${lang === 'fa' ? 'قفل' : 'Lock'} ${typeLabel}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {!isEdit && (
          <div>
            <label className="form-label">{lang === 'fa' ? `شناسه ${typeLabel}` : `${typeLabel} ID`}</label>
            <div className="flex gap-2">
              <input
                type="number" dir="ltr"
                value={form.id}
                onChange={(e) => setForm({ ...form, id: e.target.value })}
                className="input flex-1"
                placeholder="-100123456789"
                required
                dir="ltr"
              />
              <button
                type="button"
                onClick={fetchTelegramInfo}
                disabled={!form.id || fetchingInfo}
                className="btn-secondary px-3"
                title={lang === 'fa' ? 'دریافت اطلاعات از تلگرام' : 'Fetch from Telegram'}
              >
                {fetchingInfo ? <div className="w-4 h-4 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              </button>
            </div>
          </div>
        )}

        <div>
          <label className="form-label">{lang === 'fa' ? 'عنوان نمایشی' : 'Display Title'}</label>
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="input"
            placeholder={lang === 'fa' ? 'نام کانال/گروه...' : 'Channel/Group name...'}
          />
        </div>

        <div>
          <label className="form-label">{lang === 'fa' ? 'لینک دعوت' : 'Invite Link'}</label>
          <input
            value={form.invite_link}
            onChange={(e) => setForm({ ...form, invite_link: e.target.value })}
            className="input"
            placeholder="https://t.me/..."
            dir="ltr"
          />
          <p className="text-xs text-gray-500 mt-1">{lang === 'fa' ? 'این لینک به کاربران نمایش داده می‌شود' : 'This link is shown to users'}</p>
        </div>

        <div>
          <label className="form-label">{lang === 'fa' ? 'پیام سفارشی (اختیاری)' : 'Custom Message (optional)'}</label>
          <textarea
            value={form.custom_message}
            onChange={(e) => setForm({ ...form, custom_message: e.target.value })}
            className="input"
            rows={3}
            placeholder={lang === 'fa' ? 'پیام برای کاربران غیرعضو...' : 'Message for non-members...'}
          />
          <p className="text-xs text-gray-500 mt-1">{lang === 'fa' ? 'اگر خالی باشد، پیام پیش‌فرض نمایش داده می‌شود' : 'If empty, default message is shown'}</p>
        </div>

        <div>
          <label className="form-label">{lang === 'fa' ? 'تاریخ انقضا (اختیاری)' : 'Expiry Date (optional)'}</label>
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
              {lang === 'fa' ? 'قفل بعد از این تاریخ خودکار برداشته می‌شود' : 'Lock will be automatically removed after this date'}
            </p>
          )}
        </div>

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={loading} className="btn-primary flex-1">
            <LockIcon className="w-4 h-4" />
            {loading ? t('loading', lang) : (isEdit ? t('save', lang) : (lang === 'fa' ? 'قفل کن' : 'Lock'))}
          </button>
          <button type="button" onClick={onClose} className="btn-secondary flex-1">{t('cancel', lang)}</button>
        </div>
      </form>
    </Modal>
  )
}

// ── Lock Item Card ──
function LockCard({ item, idKey, type, lang, onEdit, onUnlock, onCopyLink }) {
  const id = item[idKey]
  const isExpired = item.expires_at && new Date(item.expires_at) < new Date()
  const isExpiringSoon = item.expires_at && !isExpired && (new Date(item.expires_at) - new Date()) < 7 * 24 * 60 * 60 * 1000

  // Fetch live info (member count)
  const { data: liveInfo } = useQuery({
    queryKey: ['lock-info', type, id],
    queryFn: () => api.get(`/lock/${type}/${id}/info`).then(r => r.data),
    staleTime: 5 * 60 * 1000, // 5 min cache
    retry: false,
  })

  return (
    <div
      className="card"
      style={{
        borderColor: isExpired ? 'rgba(239,68,68,0.3)' : isExpiringSoon ? 'rgba(245,158,11,0.3)' : 'var(--surface-hover, rgba(255,255,255,0.08))',
      }}
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}
        >
          <LockIcon className="w-6 h-6" style={{ color: '#ef4444' }} />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-white">{item.title}</span>
            {isExpired && <span className="badge-red">{lang === 'fa' ? 'منقضی' : 'Expired'}</span>}
            {isExpiringSoon && !isExpired && <span className="badge-yellow">{lang === 'fa' ? 'به‌زودی منقضی' : 'Expiring Soon'}</span>}
          </div>

          <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-2">
            <span className="font-mono">{id}</span>
            {liveInfo?.member_count > 0 && (
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                {liveInfo.member_count.toLocaleString()} {lang === 'fa' ? 'عضو' : 'members'}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {lang === 'fa' ? 'قفل شده' : 'Locked'}: {item.locked_at?.slice(0, 10)}
            </span>
            {item.expires_at && (
              <span className="flex items-center gap-1" style={{ color: isExpired ? '#f87171' : isExpiringSoon ? '#fbbf24' : '#6b7280' }}>
                <Clock className="w-3 h-3" />
                {lang === 'fa' ? 'انقضا' : 'Expires'}: {item.expires_at}
              </span>
            )}
          </div>

          {/* Invite link */}
          {(item.invite_link || liveInfo?.invite_link) && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-indigo-400 truncate flex-1">
                {item.invite_link || liveInfo?.invite_link}
              </span>
              <button
                onClick={() => onCopyLink(item.invite_link || liveInfo?.invite_link)}
                className="action-btn action-view flex-shrink-0"
                title={lang === 'fa' ? 'کپی لینک' : 'Copy Link'}
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
              <a
                href={item.invite_link || liveInfo?.invite_link}
                target="_blank"
                rel="noopener noreferrer"
                className="action-btn action-info flex-shrink-0"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}

          {/* Custom message */}
          {item.custom_message && (
            <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
              <MessageSquare className="w-3 h-3" />
              {item.custom_message?.slice(0, 60)}{item.custom_message?.length > 60 ? '...' : ''}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-1 flex-shrink-0">
          <button onClick={() => onEdit(item)} className="action-btn action-warning" title={t('edit', lang)}>
            <Edit className="w-4 h-4" />
          </button>
          <button onClick={() => onUnlock(id)} className="action-btn action-success" title={t('lock_unlock', lang)}>
            <Unlock className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main Lock Page ──
export default function Lock() {
  const { lang } = useApp()
  const { toast } = useToast()
  const qc = useQueryClient()
  const [showAddChannel, setShowAddChannel] = useState(false)
  const [showAddGroup, setShowAddGroup] = useState(false)
  const [editItem, setEditItem] = useState(null)
  const [editType, setEditType] = useState(null)
  const [confirmModal, setConfirmModal] = useState(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['lock'],
    queryFn: () => api.get('/lock').then(r => r.data),
  })

  const lockChannelMutation = useMutation({
    mutationFn: (body) => api.post('/lock/channel', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lock'] }); toast(lang === 'fa' ? 'کانال قفل شد' : 'Channel locked', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const unlockChannelMutation = useMutation({
    mutationFn: (id) => api.delete(`/lock/channel/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lock'] }); toast(lang === 'fa' ? 'قفل کانال برداشته شد' : 'Channel unlocked', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const updateChannelMutation = useMutation({
    mutationFn: ({ id, ...body }) => api.put(`/lock/channel/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lock'] }); toast(lang === 'fa' ? 'کانال بروزرسانی شد' : 'Channel updated', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const lockGroupMutation = useMutation({
    mutationFn: (body) => api.post('/lock/group', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lock'] }); toast(lang === 'fa' ? 'گروه قفل شد' : 'Group locked', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const unlockGroupMutation = useMutation({
    mutationFn: (id) => api.delete(`/lock/group/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lock'] }); toast(lang === 'fa' ? 'قفل گروه برداشته شد' : 'Group unlocked', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const updateGroupMutation = useMutation({
    mutationFn: ({ id, ...body }) => api.put(`/lock/group/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lock'] }); toast(lang === 'fa' ? 'گروه بروزرسانی شد' : 'Group updated', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const checkExpiredMutation = useMutation({
    mutationFn: () => api.get('/lock/check-expired'),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['lock'] })
      const count = res.data.count
      toast(
        count > 0
          ? (lang === 'fa' ? `${count} قفل منقضی‌شده برداشته شد` : `${count} expired lock(s) removed`)
          : (lang === 'fa' ? 'هیچ قفل منقضی‌شده‌ای وجود ندارد' : 'No expired locks found'),
        count > 0 ? 'warning' : 'info'
      )
    },
  })

  const handleCopyLink = (link) => {
    navigator.clipboard.writeText(link).then(() => {
      toast(lang === 'fa' ? 'لینک کپی شد' : 'Link copied', 'success')
    })
  }

  const handleEditChannel = (item) => {
    setEditItem(item)
    setEditType('channel')
  }

  const handleEditGroup = (item) => {
    setEditItem(item)
    setEditType('group')
  }

  const handleSaveEdit = async (body) => {
    if (editType === 'channel') {
      await updateChannelMutation.mutateAsync({ id: editItem.channel_id, ...body })
    } else {
      await updateGroupMutation.mutateAsync({ id: editItem.group_id, ...body })
    }
    setEditItem(null)
    setEditType(null)
  }

  const channels = data?.channels || []
  const groups = data?.groups || []

  if (isLoading) return (
    <div className="flex justify-center py-12">
      <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
    </div>
  )

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('lock_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {channels.length} {lang === 'fa' ? 'کانال' : 'channels'} · {groups.length} {lang === 'fa' ? 'گروه' : 'groups'}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => checkExpiredMutation.mutate()} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'بررسی منقضی‌شده‌ها' : 'Check Expired'}>
            <Clock className="w-4 h-4" />
          </button>
          <button onClick={() => refetch()} className="btn-secondary py-2 px-3">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {showAddChannel && (
        <LockFormModal
          type="channel"
          lang={lang}
          onClose={() => setShowAddChannel(false)}
          onSave={(body) => lockChannelMutation.mutateAsync(body)}
        />
      )}
      {showAddGroup && (
        <LockFormModal
          type="group"
          lang={lang}
          onClose={() => setShowAddGroup(false)}
          onSave={(body) => lockGroupMutation.mutateAsync(body)}
        />
      )}
      {editItem && editType && (
        <LockFormModal
          item={editItem}
          type={editType}
          lang={lang}
          onClose={() => { setEditItem(null); setEditType(null) }}
          onSave={handleSaveEdit}
        />
      )}

      {/* Channels section */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <LockIcon className="w-4 h-4 text-red-400" />
            {t('lock_channels', lang)} ({channels.length})
          </h2>
          <button onClick={() => setShowAddChannel(true)} className="btn-primary py-1.5 px-3 text-sm">
            <Plus className="w-4 h-4" /> {t('lock_add_ch', lang)}
          </button>
        </div>

        {channels.length === 0 ? (
          <div className="card text-center py-8 text-gray-500 text-sm">
            {lang === 'fa' ? 'هیچ کانالی قفل نشده' : 'No locked channels'}
          </div>
        ) : (
          <div className="space-y-3">
            {channels.map(ch => (
              <LockCard
                key={ch.channel_id}
                item={ch}
                idKey="channel_id"
                type="channel"
                lang={lang}
                onEdit={handleEditChannel}
                onUnlock={(id) => setConfirmModal({
                  title: lang === 'fa' ? 'رفع قفل کانال' : 'Unlock Channel',
                  message: lang === 'fa' ? `قفل کانال "${ch.title}" برداشته شود؟` : `Unlock channel "${ch.title}"?`,
                  type: 'warning',
                  onConfirm: () => unlockChannelMutation.mutate(id),
                })}
                onCopyLink={handleCopyLink}
              />
            ))}
          </div>
        )}
      </div>

      {/* Groups section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <LockIcon className="w-4 h-4 text-red-400" />
            {t('lock_groups', lang)} ({groups.length})
          </h2>
          <button onClick={() => setShowAddGroup(true)} className="btn-primary py-1.5 px-3 text-sm">
            <Plus className="w-4 h-4" /> {t('lock_add_gr', lang)}
          </button>
        </div>

        {groups.length === 0 ? (
          <div className="card text-center py-8 text-gray-500 text-sm">
            {lang === 'fa' ? 'هیچ گروهی قفل نشده' : 'No locked groups'}
          </div>
        ) : (
          <div className="space-y-3">
            {groups.map(gr => (
              <LockCard
                key={gr.group_id}
                item={gr}
                idKey="group_id"
                type="group"
                lang={lang}
                onEdit={handleEditGroup}
                onUnlock={(id) => setConfirmModal({
                  title: lang === 'fa' ? 'رفع قفل گروه' : 'Unlock Group',
                  message: lang === 'fa' ? `قفل گروه "${gr.title}" برداشته شود؟` : `Unlock group "${gr.title}"?`,
                  type: 'warning',
                  onConfirm: () => unlockGroupMutation.mutate(id),
                })}
                onCopyLink={handleCopyLink}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
