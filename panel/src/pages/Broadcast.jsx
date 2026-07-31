import { useState, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api from '../api/client.js'
import {
  Radio, Send, AlertTriangle, CheckCircle, X, Plus, Trash2,
  History, BarChart2, Zap, Image, Video, FileText, Link,
  Users, Eye, Calendar, XCircle, Bot, CheckCheck,
  Paperclip, ChevronDown
} from 'lucide-react'

// ── Modal wrapper ──
function Modal({ title, onClose, children, maxWidth = 'max-w-lg' }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className={`w-full ${maxWidth} rounded-2xl p-5 max-h-[90vh] overflow-y-auto`}
        style={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid var(--primary-25, rgba(99,102,241,0.25))', boxShadow: 'var(--shadow-modal, 0 25px 50px rgba(0,0,0,0.5))', animation: 'slideUp 0.2s ease' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white text-sm">{title}</h3>
          <button onClick={onClose} className="action-btn action-neutral"><X className="w-4 h-4" /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ── Telegram Message Preview ──
function TelegramPreview({ message, mediaType, uploadedFile, buttonText, buttonUrl, lang }) {
  const now = new Date()
  const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
  const hasMedia = mediaType !== 'text' && uploadedFile
  const hasMessage = message?.trim()
  const hasButton = buttonText && buttonUrl
  const isEmpty = !hasMedia && !hasMessage

  return (
    <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: '#17212b', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))', minHeight: '420px' }}>
      {/* Header */}
      <div className="flex items-center gap-2.5 px-3 py-2.5 flex-shrink-0" style={{ background: '#232e3c', borderBottom: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
          <Bot className="w-4 h-4 text-white" />
        </div>
        <div>
          <div className="text-xs font-semibold text-white">Shop Bot</div>
          <div className="text-xs" style={{ color: '#6b7280' }}>bot</div>
        </div>
      </div>

      {/* Chat */}
      <div className="flex-1 p-3 overflow-y-auto" style={{ background: '#0e1621' }}>
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <Eye className="w-8 h-8 mb-2 opacity-20" style={{ color: '#6366f1' }} />
            <p className="text-xs text-gray-500">{lang === 'fa' ? 'پیش‌نمایش اینجا نمایش داده می‌شود' : 'Preview appears here'}</p>
          </div>
        ) : (
          <div className="flex justify-end">
            <div style={{ maxWidth: '88%' }}>
              {/* Media */}
              {hasMedia && (
                <div className="rounded-xl overflow-hidden mb-1" style={{ background: '#1e2c3a' }}>
                  {mediaType === 'photo' ? (
                    <div className="flex items-center justify-center p-4" style={{ background: 'rgba(99,102,241,0.1)', borderRadius: '12px', minHeight: '80px' }}>
                      <div className="text-center">
                        <Image className="w-8 h-8 mx-auto mb-1" style={{ color: '#6366f1' }} />
                        <p className="text-xs text-gray-400 truncate max-w-[120px]">{uploadedFile?.filename}</p>
                      </div>
                    </div>
                  ) : mediaType === 'video' ? (
                    <div className="flex items-center justify-center p-4" style={{ background: 'rgba(16,185,129,0.1)', borderRadius: '12px', minHeight: '80px' }}>
                      <div className="text-center">
                        <Video className="w-8 h-8 mx-auto mb-1" style={{ color: '#10b981' }} />
                        <p className="text-xs text-gray-400">{uploadedFile?.filename || 'Video'}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 p-3" style={{ background: 'rgba(139,92,246,0.1)', borderRadius: '12px' }}>
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(139,92,246,0.2)' }}>
                        <FileText className="w-4 h-4" style={{ color: '#8b5cf6' }} />
                      </div>
                      <div>
                        <p className="text-xs text-white">{uploadedFile?.filename || 'Document'}</p>
                        <p className="text-xs text-gray-500">{uploadedFile ? `${(uploadedFile.size / 1024).toFixed(1)} KB` : ''}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Text bubble */}
              {(hasMessage || hasButton) && (
                <div className="rounded-2xl px-3 py-2" style={{ background: '#2b5278', borderRadius: hasMedia ? '4px 14px 14px 14px' : '14px 4px 14px 14px' }}>
                  {hasMessage && (
                    <div className="text-sm text-white leading-relaxed" style={{ wordBreak: 'break-word' }} dangerouslySetInnerHTML={{ __html: message.replace(/\n/g, '<br/>') }} />
                  )}
                  {hasButton && (
                    <div className="mt-2 rounded-xl px-3 py-1.5 text-center text-xs font-medium" style={{ background: 'rgba(255,255,255,0.1)', color: '#64b5f6' }}>
                      {buttonText} ↗
                    </div>
                  )}
                  <div className="flex items-center justify-end gap-1 mt-1">
                    <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{timeStr}</span>
                    <CheckCheck className="w-3 h-3" style={{ color: '#64b5f6' }} />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Bottom bar */}
      <div className="px-3 py-2 flex items-center gap-2 flex-shrink-0" style={{ background: '#232e3c', borderTop: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
        <div className="flex-1 rounded-full px-3 py-1.5 text-xs" style={{ background: '#17212b', color: 'rgba(156,163,175,0.4)' }}>
          {lang === 'fa' ? 'پیام...' : 'Message...'}
        </div>
        <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ background: '#2b5278' }}>
          <Send className="w-3.5 h-3.5 text-white" />
        </div>
      </div>
    </div>
  )
}

// ── Attachment Picker Popup ──
function AttachmentPicker({ lang, onSelect, onClose }) {
  const fileInputRef = useRef()
  const [uploading, setUploading] = useState(false)
  const { toast } = useToast()

  const options = [
    { key: 'photo', icon: Image, label: lang === 'fa' ? 'تصویر' : 'Photo', color: '#10b981', accept: 'image/*' },
    { key: 'video', icon: Video, label: lang === 'fa' ? 'ویدیو' : 'Video', color: '#f59e0b', accept: 'video/*' },
    { key: 'document', icon: FileText, label: lang === 'fa' ? 'فایل' : 'File', color: '#8b5cf6', accept: '*/*' },
  ]

  const [selectedType, setSelectedType] = useState(null)

  const handleFile = async (file, type) => {
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post('/upload-media', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      onSelect(res.data)
      onClose()
      toast(lang === 'fa' ? 'فایل آپلود شد' : 'File uploaded', 'success')
    } catch (err) {
      toast(err.response?.data?.detail || (lang === 'fa' ? 'خطا در آپلود' : 'Upload failed'), 'error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      className="absolute bottom-full mb-2 start-0 rounded-2xl p-2 z-50 animate-slide-up"
      style={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid var(--primary-30, rgba(99,102,241,0.3))', boxShadow: 'var(--shadow-elevated, 0 8px 30px rgba(0,0,0,0.4))', minWidth: '160px' }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={selectedType ? options.find(o => o.key === selectedType)?.accept : '*/*'}
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0], selectedType)}
      />
      {uploading ? (
        <div className="flex items-center gap-2 px-3 py-2">
          <div className="w-4 h-4 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
          <span className="text-xs text-gray-400">{lang === 'fa' ? 'آپلود...' : 'Uploading...'}</span>
        </div>
      ) : (
        options.map(({ key, icon: Icon, label, color, accept }) => (
          <button
            key={key}
            onClick={() => { setSelectedType(key); setTimeout(() => fileInputRef.current?.click(), 50) }}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all hover:bg-white/5"
            style={{ color: 'rgba(209,213,219,0.9)' }}
          >
            <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${color}15` }}>
              <Icon className="w-3.5 h-3.5" style={{ color }} />
            </div>
            {label}
          </button>
        ))
      )}
    </div>
  )
}

// ── History Modal ──
function HistoryModal({ lang, onClose }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['broadcast-history'], queryFn: () => api.get('/broadcast/history').then(r => r.data) })
  const cancelMutation = useMutation({ mutationFn: (id) => api.post(`/broadcast/${id}/cancel`), onSuccess: () => { qc.invalidateQueries({ queryKey: ['broadcast-history'] }); toast(lang === 'fa' ? 'لغو شد' : 'Cancelled', 'warning') }, onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error') })
  const deleteMutation = useMutation({ mutationFn: (id) => api.delete(`/broadcast/history/${id}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ['broadcast-history'] }); toast(lang === 'fa' ? 'حذف شد' : 'Deleted', 'success') }, onError: () => toast(t('error', lang), 'error') })
  const statusColors = { sent: '#10b981', queued: '#6366f1', pending: '#f59e0b', cancelled: '#6b7280' }
  return (
    <Modal title={lang === 'fa' ? 'تاریخچه' : 'History'} onClose={onClose} maxWidth="max-w-xl">
      {isLoading ? <div className="flex justify-center py-6"><div className="w-7 h-7 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /></div>
      : (data?.history || []).length === 0 ? <p className="text-center text-gray-500 text-sm py-6">{t('no_data', lang)}</p>
      : (
        <div className="space-y-2 max-h-[55vh] overflow-y-auto">
          {(data?.history || []).map(b => {
            const color = statusColors[b.status] || '#6b7280'
            return (
              <div key={b.id} className="rounded-xl p-3 flex items-start gap-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-200 truncate">{b.message?.slice(0, 70)}</p>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    <span className="badge text-xs" style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}>{b.status}</span>
                    <span className="badge-gray text-xs">{b.user_count} {lang === 'fa' ? 'کاربر' : 'users'}</span>
                    <span className="text-xs text-gray-600">{b.created_at?.slice(0, 10)}</span>
                  </div>
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  {(b.status === 'pending' || b.status === 'queued') && <button onClick={() => cancelMutation.mutate(b.id)} className="action-btn action-warning"><X className="w-3.5 h-3.5" /></button>}
                  <button onClick={() => deleteMutation.mutate(b.id)} className="action-btn action-danger"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Modal>
  )
}

// ── Templates Modal ──
function TemplatesModal({ lang, onClose, onSelect }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [form, setForm] = useState({ title: '', message: '' })
  const [showAdd, setShowAdd] = useState(false)
  const { data, isLoading } = useQuery({ queryKey: ['broadcast-templates'], queryFn: () => api.get('/broadcast/templates').then(r => r.data) })
  const addMutation = useMutation({ mutationFn: (body) => api.post('/broadcast/templates', body), onSuccess: () => { qc.invalidateQueries({ queryKey: ['broadcast-templates'] }); setForm({ title: '', message: '' }); setShowAdd(false); toast(lang === 'fa' ? 'اضافه شد' : 'Added', 'success') }, onError: () => toast(t('error', lang), 'error') })
  const deleteMutation = useMutation({ mutationFn: (id) => api.delete(`/broadcast/templates/${id}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ['broadcast-templates'] }); toast(lang === 'fa' ? 'حذف شد' : 'Deleted', 'success') }, onError: () => toast(t('error', lang), 'error') })
  return (
    <Modal title={lang === 'fa' ? 'قالب‌ها' : 'Templates'} onClose={onClose}>
      {showAdd ? (
        <div className="space-y-2 mb-3 animate-slide-up">
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder={lang === 'fa' ? 'عنوان...' : 'Title...'} className="input text-sm" />
          <textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder={lang === 'fa' ? 'متن...' : 'Message...'} className="input text-sm" rows={3} />
          <div className="flex gap-2">
            <button onClick={() => addMutation.mutate(form)} disabled={!form.title || !form.message || addMutation.isPending} className="btn-primary flex-1 text-sm py-1.5">{t('save', lang)}</button>
            <button onClick={() => setShowAdd(false)} className="btn-secondary flex-1 text-sm py-1.5">{t('cancel', lang)}</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setShowAdd(true)} className="btn-secondary w-full mb-3 text-sm py-1.5"><Plus className="w-3.5 h-3.5" /> {lang === 'fa' ? 'افزودن' : 'Add'}</button>
      )}
      {isLoading ? <div className="flex justify-center py-4"><div className="w-6 h-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /></div>
      : (
        <div className="space-y-1.5 max-h-56 overflow-y-auto">
          {(data?.templates || []).map(tmpl => (
            <div key={tmpl.id} className="flex items-start gap-2 rounded-xl px-3 py-2 cursor-pointer hover:bg-white/5" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
              <div className="flex-1 min-w-0" onClick={() => { onSelect(tmpl); onClose() }}>
                <div className="text-xs font-medium text-gray-200">{tmpl.title}</div>
                <div className="text-xs text-gray-500 truncate">{tmpl.message?.slice(0, 50)}</div>
              </div>
              <button onClick={() => deleteMutation.mutate(tmpl.id)} className="action-btn action-danger flex-shrink-0"><Trash2 className="w-3 h-3" /></button>
            </div>
          ))}
          {(data?.templates || []).length === 0 && <p className="text-center text-gray-500 text-xs py-3">{t('no_data', lang)}</p>}
        </div>
      )}
    </Modal>
  )
}

// ── Stats Modal ──
function StatsModal({ lang, onClose }) {
  const { data, isLoading } = useQuery({ queryKey: ['broadcast-stats'], queryFn: () => api.get('/broadcast/stats').then(r => r.data) })
  const s = data?.summary
  return (
    <Modal title={lang === 'fa' ? 'آمار' : 'Stats'} onClose={onClose}>
      {isLoading ? <div className="flex justify-center py-6"><div className="w-7 h-7 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /></div>
      : (
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: lang === 'fa' ? 'کل' : 'Total', value: s?.total, color: '#6366f1' },
            { label: lang === 'fa' ? 'ارسال شده' : 'Sent', value: s?.sent, color: '#10b981' },
            { label: lang === 'fa' ? 'کاربران' : 'Users', value: s?.total_users_reached?.toLocaleString(), color: '#3b82f6' },
            { label: lang === 'fa' ? 'موفق' : 'Success', value: s?.total_success?.toLocaleString(), color: '#84cc16' },
          ].map((c, i) => (
            <div key={i} className="rounded-xl p-3 text-center" style={{ background: `${c.color}10`, border: `1px solid ${c.color}25` }}>
              <div className="font-bold text-lg" style={{ color: c.color }}>{c.value ?? '—'}</div>
              <div className="text-xs text-gray-500 mt-0.5">{c.label}</div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  )
}

// ── Main Broadcast Page ──
export default function Broadcast() {
  const { lang } = useApp()
  const { toast } = useToast()
  const qc = useQueryClient()

  const [form, setForm] = useState({
    message: '',
    media_type: 'text',
    media_url: '',
    target_filter: 'all',
    button_text: '',
    button_url: '',
    scheduled_at: '',
  })
  const [uploadedFile, setUploadedFile] = useState(null)
  const [showAttachPicker, setShowAttachPicker] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showTemplates, setShowTemplates] = useState(false)
  const [showStats, setShowStats] = useState(false)
  const [confirmModal, setConfirmModal] = useState(null)
  const [result, setResult] = useState(null)

  const { data: statusData } = useQuery({
    queryKey: ['broadcast-status'],
    queryFn: () => api.get('/broadcast/status').then(r => r.data),
    refetchInterval: 10000,
  })

  const broadcastMutation = useMutation({
    mutationFn: (body) => api.post('/broadcast', body),
    onSuccess: (res) => {
      setResult(res.data)
      qc.invalidateQueries({ queryKey: ['broadcast-history'] })
      qc.invalidateQueries({ queryKey: ['broadcast-status'] })
      toast(lang === 'fa' ? `پیام برای ${res.data.user_count} کاربر در صف قرار گرفت` : `Queued for ${res.data.user_count} users`, 'success')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const handleSend = () => {
    const finalMediaUrl = uploadedFile?.file_id || form.media_url
    if (!form.message.trim() && form.media_type === 'text') return
    setConfirmModal({
      title: lang === 'fa' ? 'ارسال پیام همگانی' : 'Send Broadcast',
      message: lang === 'fa' ? `پیام برای ${form.target_filter === 'all' ? 'همه کاربران' : `کاربران ${form.target_filter}`} ارسال شود؟` : `Send to ${form.target_filter === 'all' ? 'all users' : `${form.target_filter} users`}?`,
      type: 'warning',
      confirmText: lang === 'fa' ? 'بله، ارسال کن' : 'Yes, send',
      onConfirm: () => broadcastMutation.mutate({ ...form, media_url: finalMediaUrl, scheduled_at: form.scheduled_at || null }),
    })
  }

  const handleUpload = (data) => {
    setUploadedFile(data)
    setForm(prev => ({ ...prev, media_type: data.media_type, media_url: data.file_id }))
    setShowAttachPicker(false)
  }

  const handleClearUpload = () => {
    setUploadedFile(null)
    setForm(prev => ({ ...prev, media_type: 'text', media_url: '' }))
  }

  const targetFilters = [
    { key: 'all', label: lang === 'fa' ? 'همه' : 'All' },
    { key: 'fa', label: lang === 'fa' ? 'فارسی' : 'Persian' },
    { key: 'en', label: lang === 'fa' ? 'انگلیسی' : 'English' },
    { key: 'has_balance', label: lang === 'fa' ? 'دارای موجودی' : 'Has Balance' },
    { key: 'has_orders', label: lang === 'fa' ? 'دارای سفارش' : 'Has Orders' },
  ]

  const canSend = form.message.trim() || (form.media_type !== 'text' && (uploadedFile || form.media_url))

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-white">{t('bc_title', lang)}</h1>
          <p className="text-xs text-gray-500 mt-0.5">{lang === 'fa' ? 'ارسال پیام به کاربران' : 'Send message to users'}</p>
        </div>
        <div className="flex gap-1.5">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-1.5 px-2.5" title={lang === 'fa' ? 'آمار' : 'Stats'}><BarChart2 className="w-3.5 h-3.5" /></button>
          <button onClick={() => setShowHistory(true)} className="btn-secondary py-1.5 px-2.5" title={lang === 'fa' ? 'تاریخچه' : 'History'}><History className="w-3.5 h-3.5" /></button>
          <button onClick={() => setShowTemplates(true)} className="btn-secondary py-1.5 px-2.5" title={lang === 'fa' ? 'قالب‌ها' : 'Templates'}><Zap className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {/* Alerts */}
      {statusData?.pending && (
        <div className="alert-warning mb-3 py-2">
          <Radio className="w-3.5 h-3.5 flex-shrink-0" />
          <p className="text-xs flex-1">{lang === 'fa' ? `پیام در صف: ${statusData.user_count} کاربر` : `In queue: ${statusData.user_count} users`}</p>
        </div>
      )}
      {result && (
        <div className="alert-success mb-3 py-2">
          <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <p className="text-xs flex-1">{lang === 'fa' ? `در صف: ${result.user_count} کاربر` : `Queued: ${result.user_count} users`}</p>
          <button onClick={() => setResult(null)} className="btn-ghost p-0.5 flex-shrink-0"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {showHistory && <HistoryModal lang={lang} onClose={() => setShowHistory(false)} />}
      {showTemplates && <TemplatesModal lang={lang} onClose={() => setShowTemplates(false)} onSelect={(tmpl) => setForm(prev => ({ ...prev, message: tmpl.message }))} />}
      {showStats && <StatsModal lang={lang} onClose={() => setShowStats(false)} />}

      {/* ── Two-column layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        {/* LEFT: Compact form */}
        <div className="space-y-3">
          {/* Uploaded file badge */}
          {uploadedFile && (
            <div className="flex items-center gap-2 rounded-xl px-3 py-2 animate-slide-up" style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)' }}>
              <div className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(16,185,129,0.2)' }}>
                {uploadedFile.media_type === 'photo' ? <Image className="w-3.5 h-3.5 text-green-400" /> : uploadedFile.media_type === 'video' ? <Video className="w-3.5 h-3.5 text-green-400" /> : <FileText className="w-3.5 h-3.5 text-green-400" />}
              </div>
              <span className="text-xs text-green-300 flex-1 truncate">{uploadedFile.filename}</span>
              <span className="text-xs text-gray-500">{(uploadedFile.size / 1024).toFixed(1)} KB</span>
              <button onClick={handleClearUpload} className="btn-ghost p-0.5 text-red-400 flex-shrink-0"><XCircle className="w-4 h-4" /></button>
            </div>
          )}

          {/* Message textarea with attachment button */}
          <div className="card p-0 overflow-hidden">
            <textarea
              value={form.message}
              onChange={(e) => setForm({ ...form, message: e.target.value })}
              className="w-full px-4 pt-3 pb-2 text-sm text-gray-100 placeholder-gray-500 resize-none outline-none"
              style={{ background: 'transparent', minHeight: '120px' }}
              placeholder={t('bc_message_ph', lang)}
              dir={lang === 'fa' ? 'rtl' : 'ltr'}
            />
            <div className="px-4 pb-1 text-xs text-gray-500">
              {lang === 'fa' ? 'ایموجی پرمیوم: [emoji:شناسه:🔥]' : 'Premium emoji: [emoji:ID:🔥]'}
            </div>
            {/* Toolbar */}
            <div className="flex items-center gap-2 px-3 py-2" style={{ borderTop: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
              {/* Attachment button */}
              <div className="relative">
                <button
                  onClick={() => setShowAttachPicker(!showAttachPicker)}
                  className="w-7 h-7 rounded-lg flex items-center justify-center transition-all"
                  style={{
                    background: showAttachPicker ? 'rgba(99,102,241,0.2)' : 'var(--surface-hover, rgba(255,255,255,0.06))',
                    color: showAttachPicker ? '#818cf8' : 'rgba(156,163,175,0.7)',
                  }}
                  title={lang === 'fa' ? 'پیوست فایل' : 'Attach file'}
                >
                  <Paperclip className="w-3.5 h-3.5" />
                </button>
                {showAttachPicker && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setShowAttachPicker(false)} />
                    <div className="relative z-50">
                      <AttachmentPicker lang={lang} onSelect={handleUpload} onClose={() => setShowAttachPicker(false)} />
                    </div>
                  </>
                )}
              </div>

              <span className="text-xs text-gray-600 flex-1">HTML: &lt;b&gt;, &lt;i&gt;, &lt;code&gt;</span>

              {/* Char count */}
              <span className="text-xs text-gray-600">{form.message.length}</span>
            </div>
          </div>

          {/* Target + Advanced in one row */}
          <div className="card py-3 px-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{lang === 'fa' ? 'مخاطبان' : 'Audience'}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {targetFilters.map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setForm({ ...form, target_filter: key })}
                  className="px-2.5 py-1 rounded-lg text-xs font-medium transition-all"
                  style={{
                    background: form.target_filter === key ? 'rgba(16,185,129,0.15)' : 'var(--surface-hover, rgba(255,255,255,0.05))',
                    border: `1px solid ${form.target_filter === key ? 'rgba(16,185,129,0.4)' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
                    color: form.target_filter === key ? '#34d399' : 'rgba(156,163,175,0.7)',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Advanced options (collapsible) */}
          <div className="card py-2.5 px-4">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between text-xs font-semibold text-gray-400 uppercase tracking-wider"
            >
              <span>{lang === 'fa' ? 'تنظیمات پیشرفته' : 'Advanced Options'}</span>
              <ChevronDown className="w-3.5 h-3.5 transition-transform" style={{ transform: showAdvanced ? 'rotate(180deg)' : 'rotate(0deg)' }} />
            </button>

            {showAdvanced && (
              <div className="mt-3 space-y-3 animate-slide-up">
                {/* Inline button */}
                <div>
                  <label className="form-label">{lang === 'fa' ? 'دکمه Inline (اختیاری)' : 'Inline Button (optional)'}</label>
                  <div className="grid grid-cols-2 gap-2">
                    <input value={form.button_text} onChange={(e) => setForm({ ...form, button_text: e.target.value })} className="input text-sm py-1.5" placeholder={lang === 'fa' ? 'متن دکمه' : 'Button text'} />
                    <input value={form.button_url} onChange={(e) => setForm({ ...form, button_url: e.target.value })} className="input text-sm py-1.5" placeholder="https://..." dir="ltr" />
                  </div>
                </div>

                {/* Schedule */}
                <div>
                  <label className="form-label">{lang === 'fa' ? 'زمان‌بندی (اختیاری)' : 'Schedule (optional)'}</label>
                  <input type="datetime-local" value={form.scheduled_at} onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })} className="input text-sm py-1.5" dir="ltr" />
                </div>
              </div>
            )}
          </div>

          {/* Warning + Send */}
          <div className="flex items-center gap-2 rounded-xl px-3 py-2" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
            <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0" />
            <p className="text-xs text-yellow-300">{t('bc_warning', lang)}</p>
          </div>

          <button
            onClick={handleSend}
            disabled={!canSend || broadcastMutation.isPending}
            className="btn-primary w-full py-3"
          >
            {broadcastMutation.isPending ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                {t('loading', lang)}
              </span>
            ) : (
              <>
                <Send className="w-4 h-4" />
                {form.scheduled_at ? (lang === 'fa' ? 'زمان‌بندی' : 'Schedule') : t('bc_send', lang)}
              </>
            )}
          </button>
        </div>

        {/* RIGHT: Telegram Preview */}
        <div className="lg:sticky lg:top-4 lg:self-start">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Eye className="w-3 h-3" />
            {lang === 'fa' ? 'پیش‌نمایش' : 'Preview'}
          </div>
          <TelegramPreview
            message={form.message}
            mediaType={form.media_type}
            uploadedFile={uploadedFile}
            buttonText={form.button_text}
            buttonUrl={form.button_url}
            lang={lang}
          />
        </div>
      </div>
    </div>
  )
}
