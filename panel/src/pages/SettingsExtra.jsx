import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api, { downloadFile } from '../api/client.js'
import {
  ChevronDown, Server, Cpu, Activity, Database, HardDrive, Download, Upload,
  Trash2, RefreshCw, Save, Shield, Bot, Star, Wallet, CreditCard, Users,
  TrendingUp, Clock, AlertTriangle, Globe, Terminal, MessageSquare, Plus,
  X, KeyRound, Timer, Gauge, FileDown, Zap, MemoryStick, ListChecks,
} from 'lucide-react'

/* ─────────────────────── shared building blocks ─────────────────────── */

export function SectionCard({ icon: Icon, color = '#6366f1', title, subtitle, badge, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card p-0 overflow-hidden section-card">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 transition-all section-card-head"
        style={{ background: open ? `${color}08` : 'transparent' }}
      >
        <span
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${color}15` }}
        >
          <Icon className="w-4 h-4" style={{ color }} />
        </span>
        <span className="font-semibold text-sm text-white flex-1 text-start">{title}</span>
        {badge}
        {subtitle && (
          <span className="text-xs px-2 py-0.5 rounded-full me-2 hidden sm:inline" style={{ background: `${color}15`, color }}>
            {subtitle}
          </span>
        )}
        <ChevronDown
          className="w-4 h-4 text-gray-500 transition-transform"
          style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
        />
      </button>
      <div className={`group-collapse ${open ? 'open' : ''}`}>
        <div className="group-collapse-inner">
          <div className="px-4 pb-4" style={{ borderTop: `1px solid ${open ? color + '15' : 'transparent'}`, transition: 'border-color 0.3s ease' }}>
            <div className="pt-3" />
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

function Toggle({ on, onClick }) {
  return (
    <button type="button" onClick={onClick} className={`toggle-switch ${on ? 'on' : ''}`}>
      <span className="toggle-knob" />
    </button>
  )
}

function ToggleRow({ on, onClick, label, desc }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
      <Toggle on={on} onClick={onClick} />
      <div className="flex-1 min-w-0">
        <div className="text-sm text-white">{label}</div>
        {desc && <div className="text-[11px] mt-0.5" style={{ color: 'var(--text-dim)' }}>{desc}</div>}
      </div>
    </div>
  )
}

function useBulkSave(lang) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const fa = lang === 'fa'
  return useMutation({
    mutationFn: (values) => api.post('/settings/bulk', { values }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] })
      toast(fa ? 'ذخیره شد' : 'Saved', 'success')
    },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا در ذخیره' : 'Save failed'), 'error'),
  })
}

function SaveBtn({ mutation, values, lang }) {
  return (
    <button onClick={() => mutation.mutate(values)} disabled={mutation.isPending} className="btn-primary mt-3">
      <Save className="w-4 h-4" /> {mutation.isPending ? '...' : (lang === 'fa' ? 'ذخیره' : 'Save')}
    </button>
  )
}

function Bar({ percent, color }) {
  const p = Math.min(100, Math.max(0, percent || 0))
  const c = color || (p > 85 ? '#ef4444' : p > 65 ? '#f59e0b' : '#10b981')
  return (
    <div className="h-2 rounded-full w-full" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.08))' }}>
      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${p}%`, background: c }} />
    </div>
  )
}

function fmtUptime(sec, fa) {
  if (!sec && sec !== 0) return '—'
  const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60)
  if (fa) return `${d > 0 ? d + ' روز ' : ''}${h} ساعت ${m} دقیقه`
  return `${d > 0 ? d + 'd ' : ''}${h}h ${m}m`
}

/* ─────────────────────── System tab (live monitoring) ─────────────────────── */

export function SystemLiveTab({ lang, col = null }) {
  const fa = lang === 'fa'
  const { toast } = useToast()
  const live = useQuery({
    queryKey: ['system-live'],
    queryFn: () => api.get('/system/live').then(r => r.data),
    refetchInterval: 3000,
    refetchIntervalInBackground: false,
    retry: false,
  })
  const info = useQuery({
    queryKey: ['system-info'],
    queryFn: () => api.get('/settings/system-info').then(r => r.data),
  })
  const optimize = useMutation({
    mutationFn: () => api.post('/system/db/optimize'),
    onSuccess: (r) => toast(fa ? `بهینه‌سازی انجام شد — ${r.data.saved_kb} KB آزاد شد` : `Optimized — saved ${r.data.saved_kb} KB`, 'success'),
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا' : 'Error'), 'error'),
  })
  const [integrity, setIntegrity] = useState(null)
  const integrityM = useMutation({
    mutationFn: () => api.get('/system/db/integrity').then(r => r.data),
    onSuccess: (d) => { setIntegrity(d); toast(d.ok ? (fa ? 'دیتابیس سالم است ✅' : 'Database is healthy ✅') : (fa ? 'مشکل در دیتابیس!' : 'Integrity issues!'), d.ok ? 'success' : 'error') },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا' : 'Error'), 'error'),
  })

  const L = live.data
  const psutilMissing = live.isError
  const procs = L?.processes || {}

  const ProcCard = ({ title, icon: Icon, p, color }) => (
    <div className="rounded-xl p-3" style={{ background: `${color}0d`, border: `1px solid ${color}25` }}>
      <div className="flex items-center justify-between mb-2">
        <span className="flex items-center gap-2 text-sm font-semibold text-white"><Icon className="w-4 h-4" style={{ color }} />{title}</span>
        <span className="flex items-center gap-1.5 text-xs" style={{ color: p?.running ? '#10b981' : '#ef4444' }}>
          <span className="w-2 h-2 rounded-full" style={{ background: p?.running ? '#10b981' : '#ef4444' }} />
          {p?.running ? (fa ? 'در حال اجرا' : 'Running') : (fa ? 'خاموش' : 'Stopped')}
        </span>
      </div>
      {p?.running && (
        <div className="grid grid-cols-3 gap-2 text-center">
          <div><div className="text-xs" style={{ color: 'var(--text-dim)' }}>CPU</div><div className="text-sm font-bold text-white">{p.cpu_percent?.toFixed(1)}%</div></div>
          <div><div className="text-xs" style={{ color: 'var(--text-dim)' }}>RAM</div><div className="text-sm font-bold text-white">{p.memory_mb} MB</div></div>
          <div><div className="text-xs" style={{ color: 'var(--text-dim)' }}>{fa ? 'آپ‌تایم' : 'Uptime'}</div><div className="text-[11px] font-semibold text-white leading-5">{fmtUptime(p.uptime_seconds, fa)}</div></div>
        </div>
      )}
    </div>
  )

  const colA = (
    <>
      <SectionCard icon={Gauge} color="#10b981" title={fa ? 'مانیتورینگ زنده سرور' : 'Live Server Monitoring'} subtitle={fa ? 'به‌روزرسانی هر ۳ ثانیه' : 'refreshes every 3s'}>
        {psutilMissing ? (
          <div className="rounded-xl p-4 text-sm" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171' }}>
            {fa ? 'برای مانیتورینگ زنده باید کتابخانه psutil نصب شود: pip install psutil — سپس پنل را ری‌استارت کنید.' : 'Install psutil (pip install psutil) and restart the panel API to enable live monitoring.'}
          </div>
        ) : !L ? (
          <div className="flex justify-center py-6"><div className="w-6 h-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /></div>
        ) : (
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="rounded-xl p-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="flex items-center gap-2 text-sm text-white"><Cpu className="w-4 h-4 text-indigo-400" />CPU</span>
                  <span className="text-sm font-bold text-white">{L.cpu?.percent?.toFixed(1)}%</span>
                </div>
                <Bar percent={L.cpu?.percent} />
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {(L.cpu?.per_core || []).map((c, i) => (
                    <div key={i} className="flex-1 min-w-[36px]">
                      <div className="text-[10px] text-center mb-0.5" style={{ color: 'var(--text-dim)' }}>#{i + 1}</div>
                      <Bar percent={c} />
                    </div>
                  ))}
                </div>
                <div className="text-[11px] mt-2" style={{ color: 'var(--text-dim)' }}>
                  {L.cpu?.cores} {fa ? 'هسته' : 'cores'}{L.cpu?.freq_mhz ? ` — ${Math.round(L.cpu.freq_mhz)} MHz` : ''}{L.cpu?.load_avg ? ` — Load: ${L.cpu.load_avg.map(x => x.toFixed(2)).join(' / ')}` : ''}
                </div>
              </div>
              <div className="rounded-xl p-3" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="flex items-center gap-2 text-sm text-white"><MemoryStick className="w-4 h-4 text-purple-400" />RAM</span>
                  <span className="text-sm font-bold text-white">{L.memory?.percent?.toFixed(1)}%</span>
                </div>
                <Bar percent={L.memory?.percent} />
                <div className="text-[11px] mt-2" style={{ color: 'var(--text-dim)' }}>
                  {fa ? 'استفاده‌شده' : 'Used'}: {((L.memory?.used_mb || 0) / 1024).toFixed(1)} GB / {((L.memory?.total_mb || 0) / 1024).toFixed(1)} GB — {fa ? 'آزاد' : 'Free'}: {((L.memory?.available_mb || 0) / 1024).toFixed(1)} GB
                </div>
                {L.swap?.total_mb > 0 && (
                  <div className="mt-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px]" style={{ color: 'var(--text-dim)' }}>Swap</span>
                      <span className="text-[11px] text-white">{L.swap.percent?.toFixed(1)}%</span>
                    </div>
                    <Bar percent={L.swap.percent} color="#8b5cf6" />
                  </div>
                )}
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <ProcCard title={fa ? 'ربات تلگرام' : 'Telegram Bot'} icon={Bot} p={procs.bot} color="#3b82f6" />
              <ProcCard title={fa ? 'پنل مدیریت' : 'Admin Panel'} icon={Globe} p={procs.panel} color="#a855f7" />
            </div>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-[12px]" style={{ color: 'var(--text-dim)' }}>
              <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" />{fa ? 'آپ‌تایم سرور' : 'Server uptime'}: <b className="text-white">{fmtUptime(L.uptime_seconds, fa)}</b></span>
              {L.net && <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5" />{fa ? 'شبکه' : 'Net'}: ↑ {((L.net.bytes_sent || 0) / 1024 / 1024).toFixed(0)} MB — ↓ {((L.net.bytes_recv || 0) / 1024 / 1024).toFixed(0)} MB</span>}
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard icon={Database} color="#f59e0b" title={fa ? 'ابزارهای دیتابیس' : 'Database Tools'}>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => optimize.mutate()} disabled={optimize.isPending} className="btn-primary">
            <Zap className="w-4 h-4" /> {optimize.isPending ? (fa ? 'در حال بهینه‌سازی...' : 'Optimizing...') : (fa ? 'بهینه‌سازی (VACUUM)' : 'Optimize (VACUUM)')}
          </button>
          <button onClick={() => integrityM.mutate()} disabled={integrityM.isPending} className="btn-secondary">
            <Shield className="w-4 h-4" /> {integrityM.isPending ? '...' : (fa ? 'بررسی سلامت دیتابیس' : 'Integrity Check')}
          </button>
        </div>
        {integrity && (
          <div className="mt-3 rounded-xl p-3 text-sm" style={{ background: integrity.ok ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)', border: `1px solid ${integrity.ok ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)'}` }}>
            <div className="font-semibold mb-2" style={{ color: integrity.ok ? '#10b981' : '#ef4444' }}>
              {integrity.ok ? (fa ? '✅ دیتابیس سالم است' : '✅ Database is healthy') : `⚠️ ${integrity.result}`}
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px]" style={{ color: 'var(--text-dim)' }}>
              {(integrity.tables || []).map(tb => <span key={tb.name}>{tb.name}: <b className="text-white">{tb.rows}</b></span>)}
            </div>
          </div>
        )}
        <p className="text-[11px] mt-3" style={{ color: 'var(--text-dim)' }}>
          {fa ? 'بکاپ‌گیری به تب «بکاپ» منتقل شده است.' : 'Backups have moved to the “Backup” tab.'}
        </p>
      </SectionCard>
    </>
  )
  const colB = (
    <>

      <SectionCard icon={Server} color="#3b82f6" title={fa ? 'اطلاعات سیستم و دیتابیس' : 'System & Database Info'}>
        {info.data && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Python', value: info.data.python_version, color: '#6366f1' },
                { label: 'OS', value: info.data.os, color: '#3b82f6' },
                { label: 'SQLite', value: info.data.sqlite_version, color: '#10b981' },
                { label: fa ? 'حجم DB' : 'DB Size', value: `${info.data.db_size_kb} KB`, color: '#f59e0b' },
              ].map((s, i) => (
                <div key={i} className="rounded-xl p-3" style={{ background: `${s.color}10`, border: `1px solid ${s.color}20` }}>
                  <div className="text-xs mb-0.5" style={{ color: 'var(--text-dim)' }}>{s.label}</div>
                  <div className="font-semibold text-white text-sm">{s.value}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: fa ? 'کاربران' : 'Users', value: info.data.records?.users, color: '#6366f1' },
                { label: fa ? 'سفارش‌ها' : 'Orders', value: info.data.records?.orders, color: '#10b981' },
                { label: fa ? 'تراکنش‌ها' : 'Transactions', value: info.data.records?.transactions, color: '#f59e0b' },
              ].map((s, i) => (
                <div key={i} className="rounded-xl p-3 text-center" style={{ background: `${s.color}10`, border: `1px solid ${s.color}20` }}>
                  <div className="font-bold text-lg" style={{ color: s.color }}>{s.value?.toLocaleString()}</div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>{s.label}</div>
                </div>
              ))}
            </div>
            {info.data.disk && (
              <div>
                <div className="flex justify-between text-xs mb-1" style={{ color: 'var(--text-dim)' }}>
                  <span className="flex items-center gap-1.5"><HardDrive className="w-3.5 h-3.5" />{fa ? 'دیسک — استفاده‌شده' : 'Disk — used'}: {info.data.disk.used_gb} GB</span>
                  <span>{fa ? 'آزاد' : 'Free'}: {info.data.disk.free_gb} GB</span>
                </div>
                <Bar percent={info.data.disk.percent} />
              </div>
            )}
          </div>
        )}
      </SectionCard>
    </>
  )
  if (col === 0) return colA
  if (col === 1) return colB
  return (
    <div className="settings-masonry">
      <div className="settings-col">{colA}</div>
      <div className="settings-col">{colB}</div>
    </div>
  )
}

/* ─────────────────────── Backup & Restore tab ─────────────────────── */

export function BackupTab({ lang, col = null }) {
  const fa = lang === 'fa'
  const { toast } = useToast()
  const qc = useQueryClient()
  const fileRef = useRef(null)
  const [confirmModal, setConfirmModal] = useState(null)
  const [form, setForm] = useState({ interval_value: '0', interval_unit: 'hours', to_telegram: true, keep_local: true, keep_last: '10' })

  const cfg = useQuery({ queryKey: ['backup-config'], queryFn: () => api.get('/system/backup/config').then(r => r.data) })
  const list = useQuery({ queryKey: ['backup-list'], queryFn: () => api.get('/system/backup/list').then(r => r.data) })

  useEffect(() => {
    if (cfg.data) setForm({
      interval_value: String(cfg.data.interval_value ?? '0'),
      interval_unit: cfg.data.interval_unit || 'hours',
      to_telegram: !!cfg.data.to_telegram,
      keep_local: !!cfg.data.keep_local,
      keep_last: String(cfg.data.keep_last || '10'),
    })
  }, [cfg.data])

  const saveCfg = useMutation({
    mutationFn: () => api.post('/system/backup/config', {
      interval_value: parseFloat(form.interval_value) || 0,
      interval_unit: form.interval_unit,
      to_telegram: form.to_telegram,
      keep_local: form.keep_local,
      keep_last: parseInt(form.keep_last) || 10,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['backup-config'] }); toast(fa ? 'تنظیمات بکاپ ذخیره شد' : 'Backup settings saved', 'success') },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا در ذخیره' : 'Save failed'), 'error'),
  })

  const runNow = useMutation({
    mutationFn: () => api.post('/system/backup/run'),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ['backup-list'] }); toast(fa ? `بکاپ ساخته شد (${r.data.size_kb} KB)` : `Backup created (${r.data.size_kb} KB)`, 'success') },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا در بکاپ' : 'Backup failed'), 'error'),
  })

  const del = useMutation({
    mutationFn: (name) => api.delete(`/system/backup/${encodeURIComponent(name)}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['backup-list'] }); toast(fa ? 'حذف شد' : 'Deleted', 'success') },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا' : 'Error'), 'error'),
  })

  const restore = useMutation({
    mutationFn: (file) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post('/system/backup/restore', fd, { timeout: 120000 })
    },
    onSuccess: (r) => {
      qc.invalidateQueries()
      toast(fa ? `بازیابی انجام شد ✅ (بکاپ ایمنی: ${r.data.safety_backup})` : `Restored ✅ (safety backup: ${r.data.safety_backup})`, 'success')
    },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا در بازیابی' : 'Restore failed'), 'error'),
  })

  const onRestoreFile = (e) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    setConfirmModal({
      type: 'warning',
      title: fa ? 'بازیابی دیتابیس' : 'Restore Database',
      message: fa
        ? `همه داده‌های فعلی با محتوای «${f.name}» جایگزین می‌شود. قبل از جایگزینی، یک بکاپ ایمنی خودکار ساخته می‌شود. ادامه می‌دهید؟`
        : `All current data will be replaced with "${f.name}". A safety backup is created first. Continue?`,
      confirmText: fa ? 'بله، بازیابی کن' : 'Yes, restore',
      onConfirm: () => restore.mutate(f),
    })
  }

  const colA = (
    <>
      <SectionCard icon={Timer} color="#10b981" title={fa ? 'بکاپ خودکار' : 'Auto Backup'} subtitle={fa ? 'دقیقه / ساعت / روز' : 'minutes / hours / days'}>
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="form-label">{fa ? 'هر چند وقت یک‌بار؟ (۰ = خاموش)' : 'Interval (0 = off)'}</label>
            <input type="number" min="0" value={form.interval_value} onChange={(e) => setForm({ ...form, interval_value: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'واحد زمان' : 'Unit'}</label>
            <select value={form.interval_unit} onChange={(e) => setForm({ ...form, interval_unit: e.target.value })} className="input">
              <option value="minutes">{fa ? 'دقیقه' : 'Minutes'}</option>
              <option value="hours">{fa ? 'ساعت' : 'Hours'}</option>
              <option value="days">{fa ? 'روز' : 'Days'}</option>
            </select>
          </div>
          <div>
            <label className="form-label">{fa ? 'نگه‌داری چند بکاپ آخر' : 'Keep last N backups'}</label>
            <input type="number" min="1" max="100" value={form.keep_last} onChange={(e) => setForm({ ...form, keep_last: e.target.value })} className="input" dir="ltr" />
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-3 mt-4">
          <ToggleRow on={form.to_telegram} onClick={() => setForm({ ...form, to_telegram: !form.to_telegram })}
            label={fa ? 'ارسال به تلگرام' : 'Send to Telegram'}
            desc={fa ? 'ارسال فایل بکاپ به گروه گزارش‌ها / پیوی ادمین‌ها' : 'Send backup file to reports group / admin DMs'} />
          <ToggleRow on={form.keep_local} onClick={() => setForm({ ...form, keep_local: !form.keep_local })}
            label={fa ? 'ذخیره روی سرور' : 'Keep on server'}
            desc={fa ? 'نگه‌داری نسخه محلی در پوشه backups' : 'Keep a local copy in the backups folder'} />
        </div>
        <p className="text-[11px] mt-3" style={{ color: 'var(--text-dim)' }}>
          {fa ? 'حداقل فاصله مجاز ۵ دقیقه است. مثال: «۳۰ دقیقه»، «۶ ساعت»، «۲ روز».' : 'Minimum interval is 5 minutes. e.g. 30 minutes, 6 hours, 2 days.'}
          {cfg.data?.last_backup_ts ? ` — ${fa ? 'آخرین بکاپ' : 'Last backup'}: ${new Date(parseFloat(cfg.data.last_backup_ts) * 1000).toLocaleString(fa ? 'fa-IR' : 'en-US')}` : ''}
        </p>
        <div className="flex flex-wrap gap-2 mt-2">
          <button onClick={() => saveCfg.mutate()} disabled={saveCfg.isPending} className="btn-primary">
            <Save className="w-4 h-4" /> {saveCfg.isPending ? '...' : (fa ? 'ذخیره تنظیمات' : 'Save settings')}
          </button>
          <button onClick={() => runNow.mutate()} disabled={runNow.isPending} className="btn-secondary">
            <RefreshCw className={`w-4 h-4 ${runNow.isPending ? 'animate-spin' : ''}`} /> {fa ? 'بکاپ فوری الان' : 'Backup now'}
          </button>
        </div>
      </SectionCard>

      <SectionCard icon={Upload} color="#ef4444" title={fa ? 'بازیابی (Restore)' : 'Restore'}>
        <p className="text-sm mb-3 leading-6" style={{ color: 'var(--text-dim)' }}>
          {fa
            ? 'یک فایل بکاپ (.db) را انتخاب کنید تا جایگزین دیتابیس فعلی شود. قبل از جایگزینی، فایل بررسی و از دیتابیس فعلی بکاپ ایمنی گرفته می‌شود. بعد از بازیابی، ربات و پنل را ری‌استارت کنید.'
            : 'Pick a backup (.db) file to replace the current database. The file is validated and a safety backup is created first. Restart the bot and panel afterwards.'}
        </p>
        <input ref={fileRef} type="file" accept=".db,.sqlite,.sqlite3" className="hidden" onChange={onRestoreFile} />
        <button onClick={() => fileRef.current?.click()} disabled={restore.isPending} className="btn-primary" style={{ background: '#ef4444' }}>
          <Upload className="w-4 h-4" /> {restore.isPending ? (fa ? 'در حال بازیابی...' : 'Restoring...') : (fa ? 'انتخاب فایل و بازیابی' : 'Choose file & restore')}
        </button>
      </SectionCard>
    </>
  )
  const colB = (
    <>

      <SectionCard icon={Database} color="#6366f1" title={fa ? 'بکاپ‌های موجود' : 'Existing Backups'} subtitle={`${list.data?.backups?.length || 0}`}>
        {(list.data?.backups || []).length === 0 ? (
          <p className="text-sm py-2" style={{ color: 'var(--text-dim)' }}>{fa ? 'هنوز بکاپی روی سرور ذخیره نشده است.' : 'No backups stored on the server yet.'}</p>
        ) : (
          <div className="space-y-2">
            {list.data.backups.map(b => (
              <div key={b.name} className="flex flex-wrap items-center gap-3 p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <Database className="w-4 h-4 flex-shrink-0" style={{ color: b.is_safety ? '#f59e0b' : '#6366f1' }} />
                <div className="flex-1 min-w-[180px]">
                  <div className="text-sm text-white font-mono" dir="ltr">{b.name}</div>
                  <div className="text-[11px]" style={{ color: 'var(--text-dim)' }}>{b.mtime} — {b.size_kb} KB{b.is_safety ? (fa ? ' — بکاپ ایمنی قبل از بازیابی' : ' — pre-restore safety') : ''}</div>
                </div>
                <div className="flex gap-1.5">
                  <button onClick={() => downloadFile(`/system/backup/download/${encodeURIComponent(b.name)}`, b.name)} className="action-btn action-neutral" title={fa ? 'دانلود' : 'Download'}><Download className="w-4 h-4" /></button>
                  <button onClick={() => setConfirmModal({ type: 'danger', title: fa ? 'حذف بکاپ' : 'Delete Backup', message: fa ? `فایل «${b.name}» برای همیشه حذف می‌شود.` : `"${b.name}" will be permanently deleted.`, confirmText: fa ? 'بله، حذف کن' : 'Yes, delete', onConfirm: () => del.mutate(b.name) })} className="action-btn action-danger" title={fa ? 'حذف' : 'Delete'}><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
          </div>
        )}
        <button onClick={() => downloadFile('/settings/backup', 'shop.db')} className="btn-secondary mt-3">
          <FileDown className="w-4 h-4" /> {fa ? 'دانلود مستقیم دیتابیس فعلی (shop.db)' : 'Download current database (shop.db)'}
        </button>
      </SectionCard>
    </>
  )
  const modal = confirmModal ? <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} /> : null
  if (col === 0) return <>{colA}{modal}</>
  if (col === 1) return <>{colB}{modal}</>
  return (
    <div className="settings-masonry">
      <div className="settings-col">{colA}</div>
      <div className="settings-col">{colB}</div>
      {modal}
    </div>
  )
}

/* ─────────────────────── Payment tab extras ─────────────────────── */

export function PaymentExtraCards({ data, lang, col = null }) {
  const fa = lang === 'fa'
  const save = useBulkSave(lang)
  const [f, setF] = useState({
    pm_card: '1', pm_usdt_bep20: '1', pm_usdt_trc20: '0', pm_ton: '0', pm_stars: '0', pm_zarinpal: '0',
    usdt_trc20_wallet: '', ton_wallet: '', stars_per_usd: '50', zarinpal_merchant: '', panel_base_url: '',
    deposit_bonus_percent: '0', deposit_bonus_min: '0', card_pending_expire_hours: '0',
  })
  useEffect(() => {
    if (data) setF(prev => {
      const n = { ...prev }
      Object.keys(n).forEach(k => { const v = data[k]; if (v !== undefined && v !== null) n[k] = v === true ? '1' : v === false ? '0' : String(v) })
      if (data.pm_card === undefined) n.pm_card = '1'
      if (data.pm_usdt_bep20 === undefined) n.pm_usdt_bep20 = '1'
      return n
    })
  }, [data])
  const tg = (k, def = '0') => (f[k] ?? def) === '1'
  const flip = (k) => setF({ ...f, [k]: tg(k) ? '0' : '1' })

  const methods = [
    { k: 'pm_usdt_bep20', label: 'USDT — BEP20', desc: fa ? 'روش فعلی (BSC)' : 'Current method (BSC)' },
    { k: 'pm_usdt_trc20', label: 'USDT — TRC20', desc: fa ? 'شبکه ترون، تایید خودکار با هش' : 'TRON network, auto-verified by hash' },
    { k: 'pm_ton', label: 'TON', desc: fa ? 'تایید خودکار با کد Memo اختصاصی' : 'Auto-verified via unique memo' },
    { k: 'pm_stars', label: fa ? 'استارز تلگرام ⭐' : 'Telegram Stars ⭐', desc: fa ? 'پرداخت داخل خود تلگرام' : 'Native in-Telegram payment' },
    { k: 'pm_zarinpal', label: fa ? 'زرین‌پال 🇮🇷' : 'Zarinpal 🇮🇷', desc: fa ? 'درگاه ریالی با شارژ خودکار' : 'IRR gateway with auto top-up' },
    { k: 'pm_card', label: fa ? 'کارت‌به‌کارت' : 'Card-to-card', desc: fa ? 'با تایید دستی/خودکار' : 'Manual/auto confirmation' },
  ]

  const colA = (
    <>
      <SectionCard icon={Wallet} color="#f59e0b" title={fa ? 'روش‌های پرداخت (جدید)' : 'Payment Methods (new)'}>
        <div className="grid md:grid-cols-2 gap-3">
          {methods.map(m => (
            <ToggleRow key={m.k} on={tg(m.k, m.k === 'pm_card' || m.k === 'pm_usdt_bep20' ? '1' : '0')} onClick={() => flip(m.k)} label={m.label} desc={m.desc} />
          ))}
        </div>
        <div className="grid md:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="form-label">{fa ? 'آدرس کیف پول USDT (TRC20)' : 'USDT TRC20 wallet'}</label>
            <input value={f.usdt_trc20_wallet} onChange={(e) => setF({ ...f, usdt_trc20_wallet: e.target.value })} className="input" dir="ltr" placeholder="T..." />
          </div>
          <div>
            <label className="form-label">{fa ? 'آدرس کیف پول TON' : 'TON wallet'}</label>
            <input value={f.ton_wallet} onChange={(e) => setF({ ...f, ton_wallet: e.target.value })} className="input" dir="ltr" placeholder="UQ... / EQ..." />
          </div>
          <div>
            <label className="form-label">{fa ? 'نرخ استارز (چند استار = ۱ دلار)' : 'Stars per USD'}</label>
            <input type="number" min="1" value={f.stars_per_usd} onChange={(e) => setF({ ...f, stars_per_usd: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'مرچنت زرین‌پال (Merchant ID)' : 'Zarinpal Merchant ID'}</label>
            <input value={f.zarinpal_merchant} onChange={(e) => setF({ ...f, zarinpal_merchant: e.target.value })} className="input" dir="ltr" placeholder="xxxxxxxx-xxxx-..." />
          </div>
          <div className="md:col-span-2">
            <label className="form-label">{fa ? 'آدرس عمومی پنل (برای کال‌بک زرین‌پال)' : 'Public panel URL (Zarinpal callback)'}</label>
            <input value={f.panel_base_url} onChange={(e) => setF({ ...f, panel_base_url: e.target.value })} className="input" dir="ltr" placeholder="https://panel.example.com" />
          </div>
        </div>
        <SaveBtn mutation={save} values={{
          pm_card: f.pm_card, pm_usdt_bep20: f.pm_usdt_bep20, pm_usdt_trc20: f.pm_usdt_trc20,
          pm_ton: f.pm_ton, pm_stars: f.pm_stars, pm_zarinpal: f.pm_zarinpal,
          usdt_trc20_wallet: f.usdt_trc20_wallet, ton_wallet: f.ton_wallet,
          stars_per_usd: f.stars_per_usd, zarinpal_merchant: f.zarinpal_merchant, panel_base_url: f.panel_base_url,
        }} lang={lang} />
      </SectionCard>
    </>
  )
  const colB = (
    <>

      <SectionCard icon={Star} color="#10b981" title={fa ? 'بونوس شارژ و انقضای کارت‌به‌کارت' : 'Deposit Bonus & Card Expiry'}>
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="form-label">{fa ? 'درصد بونوس شارژ (۰ = خاموش)' : 'Bonus percent (0 = off)'}</label>
            <input type="number" min="0" value={f.deposit_bonus_percent} onChange={(e) => setF({ ...f, deposit_bonus_percent: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'حداقل مبلغ برای بونوس ($)' : 'Min deposit for bonus ($)'}</label>
            <input type="number" min="0" value={f.deposit_bonus_min} onChange={(e) => setF({ ...f, deposit_bonus_min: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'انقضای پرداخت کارتی (ساعت، ۰ = خاموش)' : 'Card payment expiry (hours, 0 = off)'}</label>
            <input type="number" min="0" value={f.card_pending_expire_hours} onChange={(e) => setF({ ...f, card_pending_expire_hours: e.target.value })} className="input" dir="ltr" />
          </div>
        </div>
        <p className="text-[11px] mt-3" style={{ color: 'var(--text-dim)' }}>
          {fa ? 'مثال: بونوس ۱۰٪ با حداقل ۲۰ دلار یعنی هر واریز بالای ۲۰ دلار، ۱۰٪ شارژ هدیه می‌گیرد. پرداخت‌های کارتی تاییدنشده بعد از مهلت تعیین‌شده خودکار منقضی می‌شوند.' : 'e.g. 10% bonus with $20 minimum. Pending card payments auto-expire after the set hours.'}
        </p>
        <SaveBtn mutation={save} values={{
          deposit_bonus_percent: f.deposit_bonus_percent, deposit_bonus_min: f.deposit_bonus_min,
          card_pending_expire_hours: f.card_pending_expire_hours,
        }} lang={lang} />
      </SectionCard>
    </>
  )
  if (col === 0) return colA
  if (col === 1) return colB
  return (
    <div className="settings-masonry">
      <div className="settings-col">{colA}</div>
      <div className="settings-col">{colB}</div>
    </div>
  )
}

/* ─────────────────────── Bot tab extras ─────────────────────── */

export function BotExtraCards({ data, lang, col = null }) {
  const fa = lang === 'fa'
  const { toast } = useToast()
  const qc = useQueryClient()
  const save = useBulkSave(lang)
  const [f, setF] = useState({
    captcha_enabled: '0', antispam_per_min: '0', levels_enabled: '0',
    level_silver_spend: '50', level_silver_discount: '3', level_gold_spend: '200', level_gold_discount: '7',
    sales_paused: '0', faq_suggest: '1', sla_urgent_hours: '0', ref_fraud_daily: '0',
  })
  useEffect(() => {
    if (data) setF(prev => {
      const n = { ...prev }
      Object.keys(n).forEach(k => { const v = data[k]; if (v !== undefined && v !== null && v !== '') n[k] = v === true ? '1' : v === false ? '0' : String(v) })
      return n
    })
  }, [data])

  const [cmd, setCmd] = useState({ trigger: '', response: '' })
  const cmds = useQuery({ queryKey: ['custom-commands'], queryFn: () => api.get('/settings/custom-commands').then(r => r.data) })
  const addCmd = useMutation({
    mutationFn: () => api.post('/settings/custom-commands', cmd),
    onSuccess: () => { setCmd({ trigger: '', response: '' }); qc.invalidateQueries({ queryKey: ['custom-commands'] }); toast(fa ? 'دستور اضافه شد' : 'Command added', 'success') },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا' : 'Error'), 'error'),
  })
  const delCmd = useMutation({
    mutationFn: (id) => api.delete(`/settings/custom-commands/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['custom-commands'] }); toast(fa ? 'حذف شد' : 'Deleted', 'success') },
  })

  const [msg, setMsg] = useState({ text: '', send_time: '10:00' })
  const msgs = useQuery({ queryKey: ['scheduled-messages'], queryFn: () => api.get('/settings/scheduled-messages').then(r => r.data) })
  const addMsg = useMutation({
    mutationFn: () => api.post('/settings/scheduled-messages', msg),
    onSuccess: () => { setMsg({ text: '', send_time: '10:00' }); qc.invalidateQueries({ queryKey: ['scheduled-messages'] }); toast(fa ? 'پیام زمان‌بندی شد' : 'Message scheduled', 'success') },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا' : 'Error'), 'error'),
  })
  const delMsg = useMutation({
    mutationFn: (id) => api.delete(`/settings/scheduled-messages/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['scheduled-messages'] }); toast(fa ? 'حذف شد' : 'Deleted', 'success') },
  })

  const colA = (
    <>
      <SectionCard icon={Shield} color="#ef4444" title={fa ? 'امنیت ربات (کپچا و ضداسپم)' : 'Bot Security (Captcha & Anti-spam)'}>
        <div className="grid md:grid-cols-2 gap-3">
          <ToggleRow on={f.captcha_enabled === '1'} onClick={() => setF({ ...f, captcha_enabled: f.captcha_enabled === '1' ? '0' : '1' })}
            label={fa ? 'کپچای ضدربات در /start' : 'Anti-bot captcha on /start'}
            desc={fa ? 'سوال ریاضی ساده برای کاربران جدید (ادمین‌ها معاف هستند)' : 'Simple math question for new users (admins exempt)'} />
          <div className="p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
            <label className="form-label">{fa ? 'حداکثر پیام در دقیقه (۰ = خاموش)' : 'Max messages per minute (0 = off)'}</label>
            <input type="number" min="0" value={f.antispam_per_min} onChange={(e) => setF({ ...f, antispam_per_min: e.target.value })} className="input" dir="ltr" />
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-3 mt-3">
          <ToggleRow on={f.sales_paused === '1'} onClick={() => setF({ ...f, sales_paused: f.sales_paused === '1' ? '0' : '1' })}
            label={fa ? '🛑 توقف اضطراری فروش' : '🛑 Emergency sales pause'}
            desc={fa ? 'خرید موقتاً بسته می‌شود ولی بقیه بخش‌ها فعال می‌ماند' : 'Purchases are blocked; everything else stays available'} />
          <ToggleRow on={f.faq_suggest === '1'} onClick={() => setF({ ...f, faq_suggest: f.faq_suggest === '1' ? '0' : '1' })}
            label={fa ? '💡 پیشنهاد خودکار FAQ قبل از تیکت' : '💡 Auto-suggest FAQ before tickets'}
            desc={fa ? 'پاسخ‌های متداول مرتبط قبل از ثبت تیکت به کاربر نمایش داده می‌شود' : 'Matching FAQ answers are shown before a ticket is created'} />
          <div className="p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
            <label className="form-label">{fa ? 'هشدار SLA تیکت فوری (ساعت، ۰ = خاموش)' : 'Urgent ticket SLA alert (hours, 0 = off)'}</label>
            <input type="number" min="0" step="0.5" value={f.sla_urgent_hours} onChange={(e) => setF({ ...f, sla_urgent_hours: e.target.value })} className="input" dir="ltr" />
          </div>
          <div className="p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
            <label className="form-label">{fa ? 'آستانه رفرال مشکوک در روز (۰ = خاموش)' : 'Suspicious referrals per day (0 = off)'}</label>
            <input type="number" min="0" value={f.ref_fraud_daily} onChange={(e) => setF({ ...f, ref_fraud_daily: e.target.value })} className="input" dir="ltr" />
          </div>
        </div>
        <SaveBtn mutation={save} values={{
          captcha_enabled: f.captcha_enabled, antispam_per_min: f.antispam_per_min,
          sales_paused: f.sales_paused, faq_suggest: f.faq_suggest,
          sla_urgent_hours: f.sla_urgent_hours, ref_fraud_daily: f.ref_fraud_daily,
        }} lang={lang} />
      </SectionCard>

      <SectionCard icon={TrendingUp} color="#f59e0b" title={fa ? 'سطح‌بندی کاربران (برنزی/نقره‌ای/طلایی)' : 'User Levels (Bronze/Silver/Gold)'}>
        <ToggleRow on={f.levels_enabled === '1'} onClick={() => setF({ ...f, levels_enabled: f.levels_enabled === '1' ? '0' : '1' })}
          label={fa ? 'فعال‌سازی سطح کاربران' : 'Enable user levels'}
          desc={fa ? 'بر اساس مجموع خرید؛ تخفیف خودکار روی خریدها اعمال می‌شود و سطح در پروفایل نمایش داده می‌شود' : 'Based on total spend; discount auto-applies and level shows in profile'} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div>
            <label className="form-label">{fa ? 'نقره‌ای از ($)' : 'Silver from ($)'}</label>
            <input type="number" min="0" value={f.level_silver_spend} onChange={(e) => setF({ ...f, level_silver_spend: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'تخفیف نقره‌ای (%)' : 'Silver discount (%)'}</label>
            <input type="number" min="0" value={f.level_silver_discount} onChange={(e) => setF({ ...f, level_silver_discount: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'طلایی از ($)' : 'Gold from ($)'}</label>
            <input type="number" min="0" value={f.level_gold_spend} onChange={(e) => setF({ ...f, level_gold_spend: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'تخفیف طلایی (%)' : 'Gold discount (%)'}</label>
            <input type="number" min="0" value={f.level_gold_discount} onChange={(e) => setF({ ...f, level_gold_discount: e.target.value })} className="input" dir="ltr" />
          </div>
        </div>
        <SaveBtn mutation={save} values={{
          levels_enabled: f.levels_enabled,
          level_silver_spend: f.level_silver_spend, level_silver_discount: f.level_silver_discount,
          level_gold_spend: f.level_gold_spend, level_gold_discount: f.level_gold_discount,
        }} lang={lang} />
      </SectionCard>
    </>
  )
  const colB = (
    <>

      <SectionCard icon={Terminal} color="#3b82f6" title={fa ? 'دستورهای سفارشی' : 'Custom Commands'} subtitle={`${cmds.data?.commands?.length || 0}`}>
        <p className="text-[12px] mb-3" style={{ color: 'var(--text-dim)' }}>
          {fa ? 'هر متنی که کاربر دقیقاً بفرستد (مثل «قیمت» یا /price)، ربات پاسخ تعیین‌شده را می‌دهد. HTML و ایموجی پرمیوم پشتیبانی می‌شود.' : 'When a user sends the exact trigger text (e.g. /price), the bot replies with your response. HTML and premium emoji supported.'}
        </p>
        <div className="space-y-2 mb-3">
          {(cmds.data?.commands || []).map(c => (
            <div key={c.id} className="flex items-start gap-3 p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
              <code className="text-xs px-2 py-1 rounded-lg flex-shrink-0" style={{ background: 'rgba(59,130,246,0.12)', color: '#60a5fa' }}>{c.trigger}</code>
              <div className="flex-1 text-xs leading-5 whitespace-pre-wrap break-words" style={{ color: 'var(--text-dim)' }}>{c.response}</div>
              <button onClick={() => delCmd.mutate(c.id)} className="action-btn action-danger flex-shrink-0"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
        <div className="grid gap-3">
          <input value={cmd.trigger} onChange={(e) => setCmd({ ...cmd, trigger: e.target.value })} className="input" placeholder={fa ? 'متن دستور (مثل: قیمت یا /price)' : 'Trigger (e.g. /price)'} />
          <textarea value={cmd.response} onChange={(e) => setCmd({ ...cmd, response: e.target.value })} className="input" rows={3} placeholder={fa ? 'پاسخ ربات...' : 'Bot response...'} />
          <button onClick={() => addCmd.mutate()} disabled={addCmd.isPending || !cmd.trigger.trim() || !cmd.response.trim()} className="btn-primary w-fit">
            <Plus className="w-4 h-4" /> {fa ? 'افزودن دستور' : 'Add command'}
          </button>
        </div>
      </SectionCard>

      <SectionCard icon={Clock} color="#8b5cf6" title={fa ? 'پیام‌های زمان‌بندی‌شده' : 'Scheduled Messages'} subtitle={`${msgs.data?.messages?.length || 0}`}>
        <p className="text-[12px] mb-3" style={{ color: 'var(--text-dim)' }}>
          {fa ? 'هر روز رأس ساعت تعیین‌شده (به وقت سرور) برای همه کاربران غیرمسدود ارسال می‌شود.' : 'Sent daily at the set time (server time) to all non-blocked users.'}
        </p>
        <div className="space-y-2 mb-3">
          {(msgs.data?.messages || []).map(m => (
            <div key={m.id} className="flex items-start gap-3 p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
              <code className="text-xs px-2 py-1 rounded-lg flex-shrink-0" style={{ background: 'rgba(139,92,246,0.12)', color: '#a78bfa' }} dir="ltr">{m.send_time}</code>
              <div className="flex-1 text-xs leading-5 whitespace-pre-wrap break-words" style={{ color: 'var(--text-dim)' }}>{m.text}</div>
              <button onClick={() => delMsg.mutate(m.id)} className="action-btn action-danger flex-shrink-0"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
        <div className="grid gap-3">
          <textarea value={msg.text} onChange={(e) => setMsg({ ...msg, text: e.target.value })} className="input" rows={3} placeholder={fa ? 'متن پیام...' : 'Message text...'} />
          <div className="flex gap-2">
            <input value={msg.send_time} onChange={(e) => setMsg({ ...msg, send_time: e.target.value })} className="input" style={{ width: 110 }} placeholder="10:00" dir="ltr" />
            <button onClick={() => addMsg.mutate()} disabled={addMsg.isPending || !msg.text.trim()} className="btn-primary">
              <Plus className="w-4 h-4" /> {fa ? 'افزودن پیام' : 'Add message'}
            </button>
          </div>
        </div>
      </SectionCard>
    </>
  )
  if (col === 0) return colA
  if (col === 1) return colB
  return (
    <div className="settings-masonry">
      <div className="settings-col">{colA}</div>
      <div className="settings-col">{colB}</div>
    </div>
  )
}

/* ─────────────────────── Referral tab extras ─────────────────────── */

export function ReferralExtraCards({ data, lang, col = null }) {
  const fa = lang === 'fa'
  const save = useBulkSave(lang)
  const [f, setF] = useState({
    referral_l2_percent: '0', referral_signup_bonus: '0', referral_daily_cap: '0',
    referral_leaderboard: '0', referral_banner_text: '',
  })
  useEffect(() => {
    if (data) setF(prev => {
      const n = { ...prev }
      Object.keys(n).forEach(k => { const v = data[k]; if (v !== undefined && v !== null) n[k] = v === true ? '1' : v === false ? '0' : String(v) })
      return n
    })
  }, [data])
  const timeline = useQuery({ queryKey: ['referral-timeline'], queryFn: () => api.get('/settings/referral-timeline').then(r => r.data) })
  const tl = timeline.data?.timeline || []
  const tlMap = Object.fromEntries(tl.map(x => [String(x.d).slice(0, 10), x.c]))
  const days = Array.from({ length: 30 }, (_, i) => {
    const d = new Date(Date.now() - (29 - i) * 86400000).toISOString().slice(0, 10)
    return { d, c: tlMap[d] || 0 }
  })
  const totalC = days.reduce((s, x) => s + x.c, 0)
  const maxC = Math.max(1, ...days.map(x => x.c))

  const colA = (
    <>
      <SectionCard icon={Users} color="#8b5cf6" title={fa ? 'رفرال پیشرفته' : 'Advanced Referral'}>
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="form-label">{fa ? 'پورسانت سطح ۲ (%) — زیرمجموعهٔ زیرمجموعه' : 'Level-2 percent (%)'}</label>
            <input type="number" min="0" value={f.referral_l2_percent} onChange={(e) => setF({ ...f, referral_l2_percent: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'پاداش ثابت عضویت ($)' : 'Signup bonus ($)'}</label>
            <input type="number" min="0" step="0.1" value={f.referral_signup_bonus} onChange={(e) => setF({ ...f, referral_signup_bonus: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'سقف پورسانت روزانه ($ ، ۰ = بدون سقف)' : 'Daily earning cap ($, 0 = none)'}</label>
            <input type="number" min="0" value={f.referral_daily_cap} onChange={(e) => setF({ ...f, referral_daily_cap: e.target.value })} className="input" dir="ltr" />
          </div>
        </div>
        <div className="mt-4">
          <ToggleRow on={f.referral_leaderboard === '1'} onClick={() => setF({ ...f, referral_leaderboard: f.referral_leaderboard === '1' ? '0' : '1' })}
            label={fa ? 'لیدربرد برترین معرف‌ها 🏆' : 'Top referrers leaderboard 🏆'}
            desc={fa ? 'نمایش ۱۰ معرف برتر با دکمه در منوی دعوت ربات' : 'Shows top 10 referrers via a button in the invite menu'} />
        </div>
        <div className="mt-4">
          <label className="form-label">{fa ? 'متن تبلیغاتی بنر دعوت (اختیاری، HTML و ایموجی پرمیوم مجاز)' : 'Invite banner text (optional, HTML allowed)'}</label>
          <textarea value={f.referral_banner_text} onChange={(e) => setF({ ...f, referral_banner_text: e.target.value })} className="input" rows={2} placeholder={fa ? 'مثلاً: 🔥 با دعوت دوستانت درآمد دلاری داشته باش!' : 'e.g. 🔥 Earn by inviting friends!'} />
        </div>
        <SaveBtn mutation={save} values={{
          referral_l2_percent: f.referral_l2_percent, referral_signup_bonus: f.referral_signup_bonus,
          referral_daily_cap: f.referral_daily_cap, referral_leaderboard: f.referral_leaderboard,
          referral_banner_text: f.referral_banner_text,
        }} lang={lang} />
      </SectionCard>
    </>
  )
  const colB = (
    <>

      <SectionCard icon={TrendingUp} color="#10b981" title={fa ? 'روند زیرمجموعه‌گیری (۳۰ روز اخیر)' : 'Referral signups (last 30 days)'}>
        {totalC === 0 ? (
          <p className="text-sm py-2" style={{ color: 'var(--text-dim)' }}>{fa ? 'در ۳۰ روز اخیر زیرمجموعه جدیدی ثبت نشده است.' : 'No referral signups in the last 30 days.'}</p>
        ) : (
          <>
            <div className="flex items-end" style={{ height: 110, gap: 3 }} dir="ltr">
              {days.map(x => (
                <div key={x.d} className="flex-1 rounded-t-sm" title={`${x.d}: ${x.c}`}
                  style={{ minWidth: 0, height: x.c > 0 ? `${Math.max(10, (x.c / maxC) * 100)}%` : 3, background: x.c > 0 ? 'linear-gradient(180deg, #8b5cf6, #6366f1)' : 'var(--surface-hover, rgba(255,255,255,0.08))' }} />
              ))}
            </div>
            <div className="flex items-center justify-between mt-2 text-[11px]" dir="ltr" style={{ color: 'var(--text-dim)' }}>
              <span>{days[0].d}</span>
              <span className="font-semibold" style={{ color: '#8b5cf6' }}>{fa ? `مجموع: ${totalC}` : `Total: ${totalC}`}</span>
              <span>{days[29].d}</span>
            </div>
          </>
        )}
      </SectionCard>
    </>
  )
  if (col === 0) return colA
  if (col === 1) return colB
  return (
    <div className="settings-masonry">
      <div className="settings-col">{colA}</div>
      <div className="settings-col">{colB}</div>
    </div>
  )
}

/* ─────────────────────── Panel tab extras ─────────────────────── */

export function PanelExtraCards({ lang, col = null }) {
  const fa = lang === 'fa'
  const { toast } = useToast()
  const qc = useQueryClient()
  const [f, setF] = useState({ port: '', host: '', ip_allowlist: '' })
  const cfg = useQuery({ queryKey: ['panel-config'], queryFn: () => api.get('/system/panel-config').then(r => r.data) })
  useEffect(() => {
    if (cfg.data) setF({ port: String(cfg.data.port || ''), host: cfg.data.host || '', ip_allowlist: cfg.data.ip_allowlist || '' })
  }, [cfg.data])

  const saveCfg = useMutation({
    mutationFn: () => api.post('/system/panel-config', {
      port: parseInt(f.port) || undefined,
      host: f.host,
      ip_allowlist: f.ip_allowlist,
    }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['panel-config'] })
      toast(r.data.restart_required
        ? (fa ? 'ذخیره شد — برای اعمال پورت/هاست، سرویس پنل را ری‌استارت کنید' : 'Saved — restart the panel service to apply port/host')
        : (fa ? 'ذخیره شد' : 'Saved'), 'success')
    },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا در ذخیره' : 'Save failed'), 'error'),
  })

  const sessions = useQuery({ queryKey: ['panel-sessions'], queryFn: () => api.get('/system/sessions').then(r => r.data) })
  const revoke = useMutation({
    mutationFn: (sid) => api.post('/system/sessions/revoke', { sid }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['panel-sessions'] }); toast(fa ? 'نشست باطل شد' : 'Session revoked', 'success') },
  })

  const deploy = useMutation({
    mutationFn: () => api.get('/system/deploy').then(r => r.data),
    onSuccess: (d) => {
      Object.entries(d.files || {}).forEach(([path, content]) => {
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = path.split('/').pop()
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      })
      toast(fa ? 'فایل‌های استقرار دانلود شد' : 'Deploy files downloaded', 'success')
    },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا' : 'Error'), 'error'),
  })

  const colA = (
    <>
      <SectionCard icon={Globe} color="#a855f7" title={fa ? 'پیکربندی سرور پنل (پورت / IP)' : 'Panel Server Config (port / IP)'}>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="form-label">{fa ? 'پورت پنل' : 'Panel port'}</label>
            <input type="number" min="1" max="65535" value={f.port} onChange={(e) => setF({ ...f, port: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'آدرس bind (پیش‌فرض 0.0.0.0)' : 'Bind address (default 0.0.0.0)'}</label>
            <input value={f.host} onChange={(e) => setF({ ...f, host: e.target.value })} className="input" dir="ltr" placeholder="0.0.0.0" />
          </div>
          <div className="md:col-span-2">
            <label className="form-label">{fa ? 'لیست سفید IP (با کاما جدا کنید — خالی = همه مجاز)' : 'IP allowlist (comma-separated — empty = allow all)'}</label>
            <input value={f.ip_allowlist} onChange={(e) => setF({ ...f, ip_allowlist: e.target.value })} className="input" dir="ltr" placeholder="1.2.3.4, 5.6.7.8" />
            <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-dim)' }}>
              {fa ? 'IP فعلی خودتان را حتماً در لیست بگذارید، وگرنه دسترسی‌تان قطع می‌شود! (127.0.0.1 همیشه مجاز است)' : 'Include your own IP or you will lock yourself out! (127.0.0.1 is always allowed)'}
            </p>
          </div>
        </div>
        <button onClick={() => saveCfg.mutate()} disabled={saveCfg.isPending} className="btn-primary mt-3">
          <Save className="w-4 h-4" /> {saveCfg.isPending ? '...' : (fa ? 'ذخیره' : 'Save')}
        </button>
      </SectionCard>
    </>
  )
  const colB = (
    <>

      <SectionCard icon={KeyRound} color="#ef4444" title={fa ? 'نشست‌های ورود به پنل' : 'Panel Login Sessions'} subtitle={`${sessions.data?.sessions?.length || 0}`}>
        {(sessions.data?.sessions || []).length === 0 ? (
          <p className="text-sm py-2" style={{ color: 'var(--text-dim)' }}>{fa ? 'نشستی ثبت نشده است.' : 'No sessions recorded.'}</p>
        ) : (
          <div className="space-y-2" style={{ maxHeight: 320, overflowY: 'auto' }}>
            {sessions.data.sessions.map(s => (
              <div key={s.sid} className="flex flex-wrap items-center gap-3 p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.status === 'active' ? '#10b981' : s.status === 'revoked' ? '#ef4444' : '#6b7280' }} />
                <div className="flex-1 min-w-[160px]">
                  <div className="text-sm text-white" dir="ltr">{s.ip || '—'}</div>
                  <div className="text-[11px] truncate" style={{ color: 'var(--text-dim)', maxWidth: 380 }} dir="ltr">{s.created_at} — {s.user_agent || ''}</div>
                </div>
                <span className="text-[11px] px-2 py-0.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-dim)' }}>{s.status}</span>
                {s.status === 'active' && (
                  <button onClick={() => revoke.mutate(s.sid)} className="action-btn action-danger" title={fa ? 'ابطال نشست' : 'Revoke'}><X className="w-4 h-4" /></button>
                )}
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard icon={Terminal} color="#10b981" title={fa ? 'استقرار روی سرور لینوکس' : 'Linux Deployment'}>
        <p className="text-sm leading-6 mb-3" style={{ color: 'var(--text-dim)' }}>
          {fa
            ? 'فایل‌های آماده نصب: اسکریپت install.sh + سرویس‌های systemd برای ربات و پنل + کانفیگ nginx (با پورت فعلی پنل). همین فایل‌ها در پوشه deploy/ پروژه هم موجودند.'
            : 'Ready-made install.sh, systemd services for the bot and panel, and an nginx config (using the current panel port). Also available in the project deploy/ folder.'}
        </p>
        <button onClick={() => deploy.mutate()} disabled={deploy.isPending} className="btn-primary">
          <FileDown className="w-4 h-4" /> {deploy.isPending ? '...' : (fa ? 'دانلود فایل‌های استقرار' : 'Download deploy files')}
        </button>
      </SectionCard>
    </>
  )
  if (col === 0) return colA
  if (col === 1) return colB
  return (
    <div className="settings-masonry">
      <div className="settings-col">{colA}</div>
      <div className="settings-col">{colB}</div>
    </div>
  )
}

/* ─────────────────────── Reports tab extras ─────────────────────── */

export function ReportsExtraCards({ data, lang, col = null }) {
  const fa = lang === 'fa'
  const save = useBulkSave(lang)
  const [f, setF] = useState({
    report_weekly: '0', report_monthly: '0', report_quiet_start: '', report_quiet_end: '',
    alert_big_deposit: '0', alert_low_stock: '0',
  })
  useEffect(() => {
    if (data) setF(prev => {
      const n = { ...prev }
      Object.keys(n).forEach(k => { const v = data[k]; if (v !== undefined && v !== null) n[k] = v === true ? '1' : v === false ? '0' : String(v) })
      return n
    })
  }, [data])
  const [days, setDays] = useState('30')

  const cats = [
    { key: 'sales', label: fa ? 'فروش‌ها' : 'Sales' },
    { key: 'payments', label: fa ? 'پرداخت‌های کارتی' : 'Card payments' },
    { key: 'deposits', label: fa ? 'واریزها' : 'Deposits' },
    { key: 'tickets', label: fa ? 'تیکت‌ها' : 'Tickets' },
    { key: 'warranty', label: fa ? 'گارانتی' : 'Warranty' },
    { key: 'new_users', label: fa ? 'کاربران' : 'Users' },
  ]

  const colA = (
    <>
      <SectionCard icon={ListChecks} color="#22c55e" title={fa ? 'گزارش‌های دوره‌ای و ساعت سکوت' : 'Periodic Reports & Quiet Hours'}>
        <div className="grid md:grid-cols-2 gap-3">
          <ToggleRow on={f.report_weekly === '1'} onClick={() => setF({ ...f, report_weekly: f.report_weekly === '1' ? '0' : '1' })}
            label={fa ? 'گزارش هفتگی 📅' : 'Weekly report 📅'} desc={fa ? 'جمعه‌ها بعد از ظهر — خلاصه ۷ روز' : 'Fridays — 7-day summary'} />
          <ToggleRow on={f.report_monthly === '1'} onClick={() => setF({ ...f, report_monthly: f.report_monthly === '1' ? '0' : '1' })}
            label={fa ? 'گزارش ماهانه 🗓' : 'Monthly report 🗓'} desc={fa ? 'اول هر ماه میلادی — خلاصه ۳۰ روز' : '1st of each month — 30-day summary'} />
        </div>
        <div className="grid md:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="form-label">{fa ? 'شروع ساعت سکوت (مثلاً 23:00 — خالی = خاموش)' : 'Quiet hours start (e.g. 23:00 — empty = off)'}</label>
            <input value={f.report_quiet_start} onChange={(e) => setF({ ...f, report_quiet_start: e.target.value })} className="input" dir="ltr" placeholder="23:00" />
          </div>
          <div>
            <label className="form-label">{fa ? 'پایان ساعت سکوت (مثلاً 08:00)' : 'Quiet hours end (e.g. 08:00)'}</label>
            <input value={f.report_quiet_end} onChange={(e) => setF({ ...f, report_quiet_end: e.target.value })} className="input" dir="ltr" placeholder="08:00" />
          </div>
        </div>
        <p className="text-[11px] mt-2" style={{ color: 'var(--text-dim)' }}>
          {fa ? 'در ساعت سکوت هیچ گزارشی ارسال نمی‌شود؛ فقط «خطاها و هشدارها» مستثنا هستند.' : 'No reports are sent during quiet hours, except the Errors & Alerts category.'}
        </p>
        <SaveBtn mutation={save} values={{
          report_weekly: f.report_weekly, report_monthly: f.report_monthly,
          report_quiet_start: f.report_quiet_start, report_quiet_end: f.report_quiet_end,
        }} lang={lang} />
      </SectionCard>
    </>
  )
  const colB = (
    <>

      <SectionCard icon={AlertTriangle} color="#ef4444" title={fa ? 'هشدارهای هوشمند' : 'Smart Alerts'}>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="form-label">{fa ? 'هشدار واریز بزرگ از ($ ، ۰ = خاموش)' : 'Big-deposit alert from ($, 0 = off)'}</label>
            <input type="number" min="0" value={f.alert_big_deposit} onChange={(e) => setF({ ...f, alert_big_deposit: e.target.value })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'هشدار موجودی کم (تعداد ≤ ، ۰ = خاموش)' : 'Low-stock alert (count ≤, 0 = off)'}</label>
            <input type="number" min="0" value={f.alert_low_stock} onChange={(e) => setF({ ...f, alert_low_stock: e.target.value })} className="input" dir="ltr" />
          </div>
        </div>
        <p className="text-[11px] mt-2" style={{ color: 'var(--text-dim)' }}>
          {fa ? 'هشدار موجودی کم روزی یک‌بار (بعد از ساعت ۹ صبح) در دسته «خطاها و هشدارها» ارسال می‌شود.' : 'Low-stock alert is sent once a day (after 9 AM) to the Errors & Alerts category.'}
        </p>
        <SaveBtn mutation={save} values={{ alert_big_deposit: f.alert_big_deposit, alert_low_stock: f.alert_low_stock }} lang={lang} />
      </SectionCard>

      <SectionCard icon={FileDown} color="#3b82f6" title={fa ? 'خروجی CSV (اکسل)' : 'CSV Export (Excel)'}>
        <div className="flex items-center gap-3 mb-3">
          <label className="form-label" style={{ margin: 0 }}>{fa ? 'بازه:' : 'Range:'}</label>
          <select value={days} onChange={(e) => setDays(e.target.value)} className="input" style={{ width: 150 }}>
            <option value="7">{fa ? '۷ روز اخیر' : 'Last 7 days'}</option>
            <option value="30">{fa ? '۳۰ روز اخیر' : 'Last 30 days'}</option>
            <option value="90">{fa ? '۹۰ روز اخیر' : 'Last 90 days'}</option>
            <option value="0">{fa ? 'همه' : 'All time'}</option>
          </select>
        </div>
        <div className="flex flex-wrap gap-2">
          {cats.map(c => (
            <button key={c.key} onClick={() => downloadFile(`/system/export/${c.key}?days=${days}`, `${c.key}.csv`)} className="btn-secondary">
              <Download className="w-4 h-4" /> {c.label}
            </button>
          ))}
        </div>
      </SectionCard>
    </>
  )
  if (col === 0) return colA
  if (col === 1) return colB
  return (
    <div className="settings-masonry">
      <div className="settings-col">{colA}</div>
      <div className="settings-col">{colB}</div>
    </div>
  )
}
