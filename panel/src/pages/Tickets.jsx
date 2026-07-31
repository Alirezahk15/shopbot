import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api, { downloadFile } from '../api/client.js'
import {
  MessageSquare, CheckCircle, Send, X, Search, Filter,
  BarChart2, Download, Tag, AlertTriangle, Zap, StickyNote,
  UserCog, ChevronDown, Plus, Trash2, Clock, TrendingUp,
  BookOpen, Pencil
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

// ── Priority badge ──
function PriorityBadge({ priority, lang }) {
  if (priority === 'urgent') return <span className="badge-red flex items-center gap-1"><AlertTriangle className="w-3 h-3" />{lang === 'fa' ? 'فوری' : 'Urgent'}</span>
  if (priority === 'high') return <span className="badge-yellow flex items-center gap-1"><Zap className="w-3 h-3" />{lang === 'fa' ? 'مهم' : 'High'}</span>
  return <span className="badge-gray">{lang === 'fa' ? 'عادی' : 'Normal'}</span>
}

// ── Ticket Detail Modal ──
function TicketDetailModal({ tid, lang, onClose }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [reply, setReply] = useState('')
  const [internalNote, setInternalNote] = useState('')
  const [showNote, setShowNote] = useState(false)
  const [showTransfer, setShowTransfer] = useState(false)
  const [transferAdminId, setTransferAdminId] = useState('')
  const [transferNote, setTransferNote] = useState('')
  const [priority, setPriority] = useState(null)
  const [tags, setTags] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [showQuickReplies, setShowQuickReplies] = useState(false)

  const { data: ticket, isLoading, refetch } = useQuery({
    queryKey: ['ticket-detail', tid],
    queryFn: () => api.get(`/tickets/${tid}`).then(r => r.data),
  })

  // React Query v5 removed `onSuccess` on useQuery — sync editable state via effect
  useEffect(() => {
    if (ticket) {
      setPriority(ticket.priority || 'normal')
      setTags(ticket.tags || '')
      setInternalNote(ticket.internal_note || '')
    }
  }, [ticket])

  const { data: qrData } = useQuery({
    queryKey: ['quick-replies'],
    queryFn: () => api.get('/tickets/quick-replies').then(r => r.data),
  })

  const { data: adminsData } = useQuery({
    queryKey: ['admins'],
    queryFn: () => api.get('/admins').then(r => r.data),
  })

  const replyMutation = useMutation({
    mutationFn: (text) => api.post(`/tickets/${tid}/reply`, { reply: text }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
      refetch()
      setReply('')
      toast(lang === 'fa' ? 'پاسخ ارسال شد' : 'Reply sent', 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const closeMutation = useMutation({
    mutationFn: () => api.post(`/tickets/${tid}/close`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
      onClose()
      toast(lang === 'fa' ? 'تیکت بسته شد' : 'Ticket closed', 'success')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (body) => api.put(`/tickets/${tid}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
      refetch()
      toast(lang === 'fa' ? 'تیکت بروزرسانی شد' : 'Ticket updated', 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const transferMutation = useMutation({
    mutationFn: ({ admin_id, note }) => api.post(`/tickets/${tid}/transfer`, { admin_id, note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
      setShowTransfer(false)
      toast(lang === 'fa' ? 'تیکت منتقل شد' : 'Ticket transferred', 'success')
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const addTag = () => {
    if (!tagInput.trim()) return
    const currentTags = tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : []
    if (!currentTags.includes(tagInput.trim())) {
      const newTags = [...currentTags, tagInput.trim()].join(',')
      setTags(newTags)
      updateMutation.mutate({ tags: newTags })
    }
    setTagInput('')
  }

  const removeTag = (tag) => {
    const newTags = tags.split(',').map(t => t.trim()).filter(t => t && t !== tag).join(',')
    setTags(newTags)
    updateMutation.mutate({ tags: newTags })
  }

  if (isLoading) return (
    <Modal title={`Ticket #${tid}`} onClose={onClose} maxWidth="max-w-2xl">
      <div className="flex justify-center py-8">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
      </div>
    </Modal>
  )

  const statusColors = { open: '#f59e0b', answered: '#6366f1', closed: '#6b7280' }
  const statusColor = statusColors[ticket?.status] || '#6b7280'
  const tagList = tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : []

  return (
    <Modal title={`Ticket #${tid}`} onClose={onClose} maxWidth="max-w-2xl">
      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-white mb-1">{ticket?.subject}</h4>
          <div className="flex flex-wrap gap-2">
            <span className="badge text-xs" style={{ background: `${statusColor}15`, color: statusColor, border: `1px solid ${statusColor}30` }}>
              {ticket?.status}
            </span>
            <PriorityBadge priority={priority || ticket?.priority} lang={lang} />
            <span className="text-xs text-gray-500">@{ticket?.username || ticket?.user_id}</span>
            <span className="text-xs text-gray-500">{ticket?.created_at?.slice(0, 16)}</span>
          </div>
        </div>
      </div>

      {/* Priority selector */}
      <div className="flex gap-2 mb-4">
        {['normal', 'high', 'urgent'].map(p => (
          <button
            key={p}
            onClick={() => { setPriority(p); updateMutation.mutate({ priority: p }) }}
            className="flex-1 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: (priority || ticket?.priority) === p ? (p === 'urgent' ? 'rgba(239,68,68,0.2)' : p === 'high' ? 'rgba(245,158,11,0.2)' : 'rgba(107,114,128,0.2)') : 'var(--surface-hover, rgba(255,255,255,0.04))',
              border: `1px solid ${(priority || ticket?.priority) === p ? (p === 'urgent' ? 'rgba(239,68,68,0.4)' : p === 'high' ? 'rgba(245,158,11,0.4)' : 'rgba(107,114,128,0.4)') : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
              color: (priority || ticket?.priority) === p ? (p === 'urgent' ? '#f87171' : p === 'high' ? '#fbbf24' : '#9ca3af') : 'rgba(156,163,175,0.7)',
            }}
          >
            {p === 'normal' ? (lang === 'fa' ? 'عادی' : 'Normal') : p === 'high' ? (lang === 'fa' ? 'مهم' : 'High') : (lang === 'fa' ? 'فوری' : 'Urgent')}
          </button>
        ))}
      </div>

      {/* Tags */}
      <div className="mb-4">
        <div className="flex flex-wrap gap-1.5 mb-2">
          {tagList.map(tag => (
            <span key={tag} className="badge-blue flex items-center gap-1">
              <Tag className="w-3 h-3" /> {tag}
              <button onClick={() => removeTag(tag)} className="ms-1 hover:text-red-400">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTag()}
            placeholder={lang === 'fa' ? 'برچسب جدید...' : 'New tag...'}
            className="input flex-1 text-xs py-1.5"
          />
          <button onClick={addTag} disabled={!tagInput.trim()} className="btn-secondary py-1.5 px-3 text-xs">
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Message */}
      <div className="rounded-xl p-4 mb-4" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
        <div className="text-xs text-gray-500 mb-2">{lang === 'fa' ? 'پیام کاربر' : 'User Message'}</div>
        <p className="text-sm text-gray-200 whitespace-pre-wrap">{ticket?.message}</p>
      </div>

      {/* Previous reply */}
      {ticket?.admin_reply && (
        <div className="rounded-xl p-4 mb-4" style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)' }}>
          <div className="text-xs text-indigo-400 mb-2">{lang === 'fa' ? 'پاسخ قبلی' : 'Previous Reply'}</div>
          <p className="text-sm text-gray-200 whitespace-pre-wrap">{ticket.admin_reply}</p>
        </div>
      )}

      {/* Internal note */}
      {(ticket?.internal_note || showNote) && (
        <div className="rounded-xl p-4 mb-4" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <div className="text-xs text-yellow-400 mb-2 flex items-center gap-1">
            <StickyNote className="w-3 h-3" />
            {lang === 'fa' ? 'یادداشت داخلی (فقط ادمین‌ها می‌بینند)' : 'Internal Note (admins only)'}
          </div>
          <textarea
            value={internalNote}
            onChange={(e) => setInternalNote(e.target.value)}
            className="input text-sm"
            rows={3}
            placeholder={lang === 'fa' ? 'یادداشت داخلی...' : 'Internal note...'}
          />
          <button
            onClick={() => updateMutation.mutate({ internal_note: internalNote })}
            className="btn-warning mt-2 text-xs py-1.5 px-3"
          >
            <Save className="w-3.5 h-3.5" /> {t('save', lang)}
          </button>
        </div>
      )}

      {/* Reply area */}
      {ticket?.status !== 'closed' && (
        <div className="space-y-3">
          {/* Quick replies */}
          {showQuickReplies && (qrData?.quick_replies || []).length > 0 && (
            <div className="rounded-xl p-3 animate-slide-up" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.08))' }}>
              <div className="text-xs text-gray-400 mb-2">{lang === 'fa' ? 'پاسخ‌های سریع' : 'Quick Replies'}</div>
              <div className="space-y-1.5 max-h-40 overflow-y-auto">
                {(qrData?.quick_replies || []).map(qr => (
                  <button
                    key={qr.id}
                    onClick={() => { setReply(qr.content); setShowQuickReplies(false) }}
                    className="w-full text-start rounded-lg px-3 py-2 text-xs hover:bg-white/5 transition-colors"
                  >
                    <div className="font-medium text-gray-200">{qr.title}</div>
                    <div className="text-gray-500 truncate">{qr.content?.slice(0, 60)}...</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="relative">
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder={t('tick_reply_ph', lang)}
              className="input"
              rows={4}
            />
            <button
              onClick={() => setShowQuickReplies(!showQuickReplies)}
              className="absolute top-2 end-2 action-btn action-view"
              title={lang === 'fa' ? 'پاسخ سریع' : 'Quick Reply'}
            >
              <Zap className="w-4 h-4" />
            </button>
          </div>

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => replyMutation.mutate(reply)}
              disabled={!reply.trim() || replyMutation.isPending}
              className="btn-primary flex-1"
            >
              <Send className="w-4 h-4" />
              {replyMutation.isPending ? t('loading', lang) : t('tick_reply', lang)}
            </button>
            <button onClick={() => setShowNote(!showNote)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'یادداشت داخلی' : 'Internal Note'}>
              <StickyNote className="w-4 h-4" />
            </button>
            <button onClick={() => setShowTransfer(!showTransfer)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'انتقال تیکت' : 'Transfer'}>
              <UserCog className="w-4 h-4" />
            </button>
            <button onClick={() => closeMutation.mutate()} className="btn-secondary py-2 px-3" title={t('tick_close', lang)}>
              <CheckCircle className="w-4 h-4" />
            </button>
          </div>

          {/* Transfer form */}
          {showTransfer && (
            <div className="rounded-xl p-4 animate-slide-up" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.08))' }}>
              <div className="text-xs text-gray-400 mb-3">{lang === 'fa' ? 'انتقال به ادمین' : 'Transfer to Admin'}</div>
              <select
                value={transferAdminId}
                onChange={(e) => setTransferAdminId(e.target.value)}
                className="input mb-2"
              >
                <option value="">{lang === 'fa' ? 'انتخاب ادمین...' : 'Select admin...'}</option>
                {(adminsData?.admins || []).map(a => (
                  <option key={a.user_id} value={a.user_id}>
                    {a.username ? `@${a.username}` : a.user_id} ({a.is_super ? 'Super' : 'Admin'})
                  </option>
                ))}
              </select>
              <input
                value={transferNote}
                onChange={(e) => setTransferNote(e.target.value)}
                placeholder={lang === 'fa' ? 'یادداشت انتقال (اختیاری)' : 'Transfer note (optional)'}
                className="input mb-2"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => transferMutation.mutate({ admin_id: parseInt(transferAdminId), note: transferNote })}
                  disabled={!transferAdminId || transferMutation.isPending}
                  className="btn-primary flex-1 text-sm"
                >
                  {transferMutation.isPending ? t('loading', lang) : (lang === 'fa' ? 'انتقال' : 'Transfer')}
                </button>
                <button onClick={() => setShowTransfer(false)} className="btn-secondary flex-1 text-sm">{t('cancel', lang)}</button>
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
    queryKey: ['ticket-stats'],
    queryFn: () => api.get('/tickets/stats').then(r => r.data),
  })

  const s = data?.summary

  return (
    <Modal title={lang === 'fa' ? 'آمار تیکت‌ها' : 'Ticket Statistics'} onClose={onClose} maxWidth="max-w-2xl">
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
              { label: lang === 'fa' ? 'باز' : 'Open', value: s?.open, color: '#f59e0b' },
              { label: lang === 'fa' ? 'پاسخ داده' : 'Answered', value: s?.answered, color: '#10b981' },
              { label: lang === 'fa' ? 'بسته' : 'Closed', value: s?.closed, color: '#6b7280' },
            ].map((c, i) => (
              <div key={i} className="rounded-xl p-3 text-center" style={{ background: `${c.color}10`, border: `1px solid ${c.color}25` }}>
                <div className="font-bold text-lg" style={{ color: c.color }}>{c.value}</div>
                <div className="text-xs text-gray-500 mt-0.5">{c.label}</div>
              </div>
            ))}
          </div>

          {/* Priority + response time */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl p-3" style={{ background: 'rgba(239,68,68,0.08)' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'فوری' : 'Urgent'}</div>
              <div className="font-bold text-red-400">{s?.urgent}</div>
            </div>
            <div className="rounded-xl p-3" style={{ background: 'rgba(245,158,11,0.08)' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'مهم' : 'High'}</div>
              <div className="font-bold text-yellow-400">{s?.high_priority}</div>
            </div>
            <div className="rounded-xl p-3" style={{ background: 'rgba(99,102,241,0.08)' }}>
              <div className="text-xs text-gray-500 mb-1">{lang === 'fa' ? 'میانگین پاسخ' : 'Avg Response'}</div>
              <div className="font-bold text-indigo-400">{data?.avg_response_hours}h</div>
            </div>
          </div>

          {/* Daily chart */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {lang === 'fa' ? 'تیکت‌های ۱۴ روز اخیر' : 'Tickets — Last 14 Days'}
            </h4>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={data?.daily || []}>
                <defs>
                  <linearGradient id="ticketGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ec4899" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ec4899" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v?.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px' }} />
                <Area type="monotone" dataKey="count" stroke="#ec4899" strokeWidth={2} fill="url(#ticketGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </Modal>
  )
}

// ── Quick Replies Manager ──
function QuickRepliesModal({ lang, onClose }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [form, setForm] = useState({ title: '', content: '' })

  const { data, isLoading } = useQuery({
    queryKey: ['quick-replies'],
    queryFn: () => api.get('/tickets/quick-replies').then(r => r.data),
  })

  const addMutation = useMutation({
    mutationFn: (body) => api.post('/tickets/quick-replies', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['quick-replies'] }); setForm({ title: '', content: '' }); toast(lang === 'fa' ? 'قالب اضافه شد' : 'Template added', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/tickets/quick-replies/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['quick-replies'] }); toast(lang === 'fa' ? 'قالب حذف شد' : 'Template deleted', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  return (
    <Modal title={lang === 'fa' ? 'قالب‌های پاسخ سریع' : 'Quick Reply Templates'} onClose={onClose}>
      {/* Add form */}
      <div className="space-y-2 mb-4">
        <input
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder={lang === 'fa' ? 'عنوان قالب...' : 'Template title...'}
          className="input text-sm"
        />
        <textarea
          value={form.content}
          onChange={(e) => setForm({ ...form, content: e.target.value })}
          placeholder={lang === 'fa' ? 'متن پاسخ...' : 'Reply content...'}
          className="input text-sm"
          rows={3}
        />
        <button
          onClick={() => addMutation.mutate(form)}
          disabled={!form.title.trim() || !form.content.trim() || addMutation.isPending}
          className="btn-primary w-full text-sm"
        >
          <Plus className="w-4 h-4" /> {lang === 'fa' ? 'افزودن قالب' : 'Add Template'}
        </button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-4">
          <div className="w-6 h-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {(data?.quick_replies || []).map(qr => (
            <div key={qr.id} className="flex items-start gap-3 rounded-xl px-3 py-2.5" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-200">{qr.title}</div>
                <div className="text-xs text-gray-500 truncate">{qr.content?.slice(0, 60)}</div>
              </div>
              <button onClick={() => deleteMutation.mutate(qr.id)} className="action-btn action-danger flex-shrink-0">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
          {(data?.quick_replies || []).length === 0 && (
            <p className="text-center text-gray-500 text-sm py-4">{t('no_data', lang)}</p>
          )}
        </div>
      )}
    </Modal>
  )
}

// ── Main Tickets Page ──
function FaqModal({ lang, onClose }) {
  const fa = lang === 'fa'
  const { toast } = useToast()
  const qc = useQueryClient()
  const empty = { question: '', answer: '', keywords: '', lang: '' }
  const [form, setForm] = useState(empty)
  const [editing, setEditing] = useState(null)
  const [confirmDel, setConfirmDel] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['faqs'],
    queryFn: () => api.get('/faq').then(r => r.data),
  })
  const faqs = data?.faqs || []

  const saveMut = useMutation({
    mutationFn: () => editing ? api.put(`/faq/${editing}`, form) : api.post('/faq', form),
    onSuccess: () => {
      setForm(empty); setEditing(null)
      qc.invalidateQueries({ queryKey: ['faqs'] })
      toast(fa ? 'ذخیره شد' : 'Saved', 'success')
    },
    onError: (e) => toast(e.response?.data?.detail || t('error', lang), 'error'),
  })
  const delMut = useMutation({
    mutationFn: (id) => api.delete(`/faq/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['faqs'] }); toast(fa ? 'حذف شد' : 'Deleted', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  return (
    <Modal title={fa ? 'سوالات متداول (FAQ)' : 'FAQ Manager'} onClose={onClose} maxWidth="max-w-2xl">
      <p className="text-xs text-gray-500 mb-3">
        {fa ? 'قبل از ثبت تیکت، پاسخ‌های مرتبط به‌صورت خودکار به کاربر پیشنهاد می‌شود تا تعداد تیکت‌ها کم شود.' : 'Matching answers are auto-suggested to users before they open a ticket.'}
      </p>
      <div className="space-y-2 mb-4">
        <input className="input text-sm" placeholder={fa ? 'سوال...' : 'Question...'} value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} />
        <textarea className="input text-sm" rows="3" placeholder={fa ? 'پاسخ...' : 'Answer...'} value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })} />
        <div className="flex gap-2">
          <input className="input text-sm flex-1" placeholder={fa ? 'کلیدواژه‌ها (با کاما جدا کنید)' : 'Keywords (comma separated)'} value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} />
          <select className="input text-sm w-36" value={form.lang} onChange={(e) => setForm({ ...form, lang: e.target.value })}>
            <option value="">{fa ? 'هر دو زبان' : 'Both languages'}</option>
            <option value="fa">فارسی</option>
            <option value="en">English</option>
          </select>
        </div>
        <div className="flex gap-2">
          <button className="btn-primary" disabled={!form.question.trim() || !form.answer.trim() || saveMut.isPending}
            onClick={() => saveMut.mutate()}>
            <Plus className="w-4 h-4" /> {editing ? (fa ? 'ذخیره ویرایش' : 'Save changes') : (fa ? 'افزودن' : 'Add')}
          </button>
          {editing && (
            <button className="btn-secondary" onClick={() => { setEditing(null); setForm(empty) }}>
              {fa ? 'انصراف' : 'Cancel'}
            </button>
          )}
        </div>
      </div>
      {isLoading ? (
        <p className="text-gray-500 text-sm">{t('loading', lang)}</p>
      ) : faqs.length === 0 ? (
        <p className="text-gray-500 text-sm">{fa ? 'هنوز سوالی ثبت نشده' : 'No FAQs yet'}</p>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto">
          {faqs.map(fq => (
            <div key={fq.id} className="p-3 rounded-xl flex items-start gap-2" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white">
                  {fq.question}
                  {fq.lang && <span className="badge-purple text-[10px] ms-1">{fq.lang}</span>}
                </div>
                <div className="text-xs text-gray-400 mt-1 whitespace-pre-wrap">{fq.answer}</div>
                {fq.keywords && <div className="text-[10px] text-gray-500 mt-1">🔑 {fq.keywords}</div>}
              </div>
              <button className="btn-secondary py-1.5 px-2" title={fa ? 'ویرایش' : 'Edit'}
                onClick={() => { setEditing(fq.id); setForm({ question: fq.question, answer: fq.answer, keywords: fq.keywords || '', lang: fq.lang || '' }) }}>
                <Pencil className="w-3.5 h-3.5" />
              </button>
              <button className="btn-secondary py-1.5 px-2" title={fa ? 'حذف' : 'Delete'} onClick={() => setConfirmDel(fq.id)}>
                <Trash2 className="w-3.5 h-3.5 text-red-400" />
              </button>
            </div>
          ))}
        </div>
      )}
      {confirmDel && (
        <ConfirmModal
          title={fa ? 'حذف سوال' : 'Delete FAQ'}
          message={fa ? 'این سوال و پاسخ حذف شود؟' : 'Delete this FAQ entry?'}
          onConfirm={() => { delMut.mutate(confirmDel); setConfirmDel(null) }}
          onClose={() => setConfirmDel(null)}
        />
      )}
    </Modal>
  )
}

export default function Tickets() {
  const { lang } = useApp()
  const { toast } = useToast()
  const [filter, setFilter] = useState('open')
  const [priority, setPriority] = useState('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [sortBy, setSortBy] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [detailTid, setDetailTid] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const [showQuickReplies, setShowQuickReplies] = useState(false)
  const [showFaq, setShowFaq] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['tickets', filter, priority, search, dateFrom, dateTo, sortBy],
    queryFn: () => {
      const params = new URLSearchParams({
        ...(filter && { status: filter }),
        ...(priority && { priority }),
        ...(search && { search }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
        ...(sortBy && { sort: sortBy }),
      })
      return api.get(`/tickets?${params}`).then(r => r.data)
    },
  })

  const handleSearch = (e) => {
    e.preventDefault()
    setSearch(searchInput)
  }

  const handleExportCSV = () => {
    const params = new URLSearchParams({ ...(filter && { status: filter }) })
    downloadFile(`/tickets/export.csv?${params}`, 'tickets.csv')
    toast(lang === 'fa' ? 'در حال دانلود...' : 'Downloading...', 'info')
  }

  const tickets = data?.tickets || []

  const statusColors = { open: '#f59e0b', answered: '#6366f1', closed: '#6b7280' }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('tick_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tickets.length} {lang === 'fa' ? 'تیکت' : 'tickets'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-2 px-3">
            <BarChart2 className="w-4 h-4" />
          </button>
          <button onClick={() => setShowQuickReplies(true)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'قالب‌های پاسخ سریع' : 'Quick Reply Templates'}>
            <Zap className="w-4 h-4" />
          </button>
          <button onClick={() => setShowFaq(true)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'سوالات متداول (FAQ)' : 'FAQ Manager'}>
            <BookOpen className="w-4 h-4" />
          </button>
          <button onClick={handleExportCSV} className="btn-secondary py-2 px-3">
            <Download className="w-4 h-4" />
          </button>
          <button onClick={() => setShowFilters(!showFilters)} className={`btn-secondary py-2 px-3 ${showFilters ? 'text-indigo-400' : ''}`}>
            <Filter className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 mb-3 flex-wrap">
        {[
          { key: 'open', label: lang === 'fa' ? 'باز' : 'Open', color: '#f59e0b' },
          { key: 'answered', label: lang === 'fa' ? 'پاسخ داده' : 'Answered', color: '#6366f1' },
          { key: 'closed', label: lang === 'fa' ? 'بسته' : 'Closed', color: '#6b7280' },
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
          placeholder={lang === 'fa' ? 'جستجو در موضوع و متن تیکت...' : 'Search in subject and message...'}
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
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div>
              <label className="form-label">{lang === 'fa' ? 'اولویت' : 'Priority'}</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value)} className="input">
                <option value="">{lang === 'fa' ? 'همه' : 'All'}</option>
                <option value="urgent">{lang === 'fa' ? 'فوری' : 'Urgent'}</option>
                <option value="high">{lang === 'fa' ? 'مهم' : 'High'}</option>
                <option value="normal">{lang === 'fa' ? 'عادی' : 'Normal'}</option>
              </select>
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'از تاریخ' : 'From Date'}</label>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input" dir="ltr" />
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'تا تاریخ' : 'To Date'}</label>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input" dir="ltr" />
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'مرتب‌سازی' : 'Sort'}</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="input">
                <option value="">{lang === 'fa' ? 'جدیدترین' : 'Newest'}</option>
                <option value="oldest">{lang === 'fa' ? 'قدیمی‌ترین' : 'Oldest'}</option>
                <option value="priority">{lang === 'fa' ? 'اولویت' : 'Priority'}</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {detailTid && <TicketDetailModal tid={detailTid} lang={lang} onClose={() => setDetailTid(null)} />}
      {showStats && <StatsModal lang={lang} onClose={() => setShowStats(false)} />}
      {showQuickReplies && <QuickRepliesModal lang={lang} onClose={() => setShowQuickReplies(false)} />}
      {showFaq && <FaqModal lang={lang} onClose={() => setShowFaq(false)} />}

      {/* Tickets list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : tickets.length === 0 ? (
        <div className="card text-center py-16">
          <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-white font-semibold">{t('tick_no_tickets', lang)}</p>
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <div className="divide-y" style={{ borderColor: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
            {tickets.map((tk) => {
              const color = statusColors[tk.status] || '#6b7280'
              const tagList = tk.tags ? tk.tags.split(',').filter(Boolean) : []

              return (
                <div
                  key={tk.id}
                  className="flex items-center gap-4 px-4 py-3 hover:bg-white/5 cursor-pointer transition-colors"
                  onClick={() => setDetailTid(tk.id)}
                >
                  {/* Priority indicator */}
                  <div
                    className="w-1.5 h-10 rounded-full flex-shrink-0"
                    style={{
                      background: tk.priority === 'urgent' ? '#ef4444' : tk.priority === 'high' ? '#f59e0b' : 'rgba(107,114,128,0.3)',
                    }}
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium text-gray-200 truncate">{tk.subject}</span>
                      {tagList.map(tag => (
                        <span key={tag} className="badge-blue text-xs py-0 px-1.5">{tag}</span>
                      ))}
                    </div>
                    <div className="text-xs text-gray-500">
                      @{tk.username || 'N/A'} · #{tk.id} · {tk.created_at?.slice(0, 10)}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <PriorityBadge priority={tk.priority} lang={lang} />
                    <span
                      className="badge text-xs"
                      style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}
                    >
                      {tk.status === 'open' ? t('tick_open', lang) : tk.status === 'answered' ? t('tick_answered', lang) : t('tick_closed', lang)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// Missing import
function Save({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
      <polyline points="17 21 17 13 7 13 7 21"/>
      <polyline points="7 3 7 8 15 8"/>
    </svg>
  )
}
