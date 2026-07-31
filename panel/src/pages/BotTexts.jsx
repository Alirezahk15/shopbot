import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client.js'
import { useApp } from '../context/AppContext.jsx'
import { Languages, Search, RotateCcw, Save, CalendarClock, Crown, Plus, Trash2, ChevronDown } from 'lucide-react'

/* ── ردیف ویرایش متن ── */
function TextRow({ row, lang, onSaved }) {
  const [open, setOpen]   = useState(false)
  const [fa, setFa]       = useState(row.override_fa || '')
  const [en, setEn]       = useState(row.override_en || '')
  const [busy, setBusy]   = useState(false)
  const overridden = !!(row.override_fa || row.override_en)

  const save = async () => {
    setBusy(true)
    try {
      await api.put(`/texts/${row.key}`, { lang: 'fa', text: fa })
      await api.put(`/texts/${row.key}`, { lang: 'en', text: en })
      onSaved()
    } finally { setBusy(false) }
  }

  const reset = async () => {
    setBusy(true)
    try {
      setFa(''); setEn('')
      await api.put(`/texts/${row.key}`, { lang: 'fa', text: '' })
      await api.put(`/texts/${row.key}`, { lang: 'en', text: '' })
      onSaved()
    } finally { setBusy(false) }
  }

  return (
    <div className="rounded-xl mb-2 overflow-hidden"
         style={{ border: '1px solid var(--border-soft, rgba(255,255,255,0.07))', background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
      <button onClick={() => setOpen((o) => !o)}
              className="w-full flex items-center gap-3 p-3 text-start">
        <code className="text-xs flex-shrink-0" style={{ color: 'var(--primary)' }}>{row.key}</code>
        {overridden && (
          <span className="text-[10px] px-1.5 py-0.5 rounded flex-shrink-0"
                style={{ background: 'var(--primary-15, rgba(99,102,241,0.15))', color: 'var(--primary)' }}>
            {lang === 'fa' ? 'سفارشی' : 'custom'}
          </span>
        )}
        <span className="text-xs text-gray-500 truncate flex-1">
          {String(lang === 'fa' ? row.default_fa : row.default_en).slice(0, 80)}
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-gray-600 flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-400 mb-1">فارسی</label>
              <textarea className="input w-full" rows={2} value={fa} onChange={(e) => setFa(e.target.value)} placeholder={row.default_fa} />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">English</label>
              <textarea className="input w-full" rows={2} value={en} onChange={(e) => setEn(e.target.value)} placeholder={row.default_en} />
            </div>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">
            {lang === 'fa' ? 'متغیرهای داخل آکولاد مانند ' : 'Keep placeholders like '}
            <code>{'{name}'}</code>, <code>{'{s}'}</code>
            {lang === 'fa' ? ' را دست نخورده نگه دارید. خالی = متن پیش فرض' : ' unchanged. Empty = default text'}
          </p>
          <div className="flex gap-2">
            <button onClick={save} disabled={busy} className="btn-primary text-xs flex items-center gap-1.5">
              <Save className="w-3.5 h-3.5" />
              {lang === 'fa' ? 'ذخیره' : 'Save'}
            </button>
            <button onClick={reset} disabled={busy} className="btn-secondary text-xs flex items-center gap-1.5">
              <RotateCcw className="w-3.5 h-3.5" />
              {lang === 'fa' ? 'بازنشانی' : 'Reset'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function BotTexts() {
  const { lang } = useApp()
  const qc = useQueryClient()
  const [q, setQ]         = useState('')
  const [limit, setLimit] = useState(30)

  const { data: texts, isLoading } = useQuery({
    queryKey: ['bot-texts'],
    queryFn: () => api.get('/texts').then((r) => r.data.texts),
  })
  const { data: settings } = useQuery({
    queryKey: ['bot-texts-settings'],
    queryFn: () => api.get('/settings').then((r) => r.data),
  })

  const [extras, setExtras]     = useState(null)
  const [extrasMsg, setExtrasMsg] = useState('')

  useEffect(() => {
    if (settings && !extras) {
      let occ = []
      try { occ = JSON.parse(settings.occasion_messages || '[]') } catch { occ = [] }
      setExtras({
        occasions: Array.isArray(occ) ? occ : [],
        welcome_gold:   settings.welcome_gold   || '',
        welcome_silver: settings.welcome_silver || '',
      })
    }
  }, [settings, extras])

  const saveExtras = async () => {
    try {
      await api.post('/settings/bulk', {
        values: {
          occasion_messages: JSON.stringify((extras.occasions || []).filter((o) => (o.text || '').trim())),
          welcome_gold:   extras.welcome_gold   || '',
          welcome_silver: extras.welcome_silver || '',
        },
      })
      setExtrasMsg(lang === 'fa' ? 'ذخیره شد' : 'Saved')
      qc.invalidateQueries({ queryKey: ['bot-texts-settings'] })
    } catch {
      setExtrasMsg(lang === 'fa' ? 'خطا در ذخیره' : 'Save failed')
    }
    setTimeout(() => setExtrasMsg(''), 4000)
  }

  const setOcc = (i, field, val) =>
    setExtras((ex) => ({ ...ex, occasions: ex.occasions.map((o, j) => (j === i ? { ...o, [field]: val } : o)) }))

  const filtered = (texts || []).filter((r) => {
    if (!q.trim()) return true
    const needle = q.trim().toLowerCase()
    return r.key.toLowerCase().includes(needle)
        || String(r.default_fa).toLowerCase().includes(needle)
        || String(r.default_en).toLowerCase().includes(needle)
  })
  const overriddenCount = (texts || []).filter((r) => r.override_fa || r.override_en).length

  return (
    <div className="page-enter">

      {/* header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
             style={{ background: 'linear-gradient(135deg, #f59e0b, #f97316)', boxShadow: '0 4px 15px rgba(245,158,11,0.35)' }}>
          <Languages className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="section-title mb-0">{lang === 'fa' ? 'متن های ربات' : 'Bot Texts'}</h1>
          <p className="text-sm text-gray-400">
            {lang === 'fa'
              ? 'همه متن های ربات را بدون تغییر کد ویرایش کنید — تغییرات تا ۳۰ ثانیه اعمال می شود'
              : 'Edit every bot text without touching code — changes apply within 30 seconds'}
          </p>
        </div>
      </div>

      {/* Occasion messages */}
      <div className="card mb-4 animate-slide-up">
        <div className="flex items-center gap-2 mb-1">
          <CalendarClock className="w-4 h-4" style={{ color: 'var(--primary)' }} />
          <h2 className="text-sm font-semibold text-white">
            {lang === 'fa' ? 'پیام های مناسبتی' : 'Occasion messages'}
          </h2>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          {lang === 'fa'
            ? 'در بازه تاریخ تعیین شده، پیام بالای خوش آمدگویی ربات نمایش داده می شود'
            : 'Shown above the bot welcome message during the chosen date range'}
        </p>

        {/* هر مناسبت به عنوان یک کارت مجزا */}
        <div className="space-y-2 mb-3">
          {(extras?.occasions || []).map((o, i) => (
            <div key={i}
                 className="rounded-xl p-3"
                 style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))', border: '1px solid var(--border-soft, rgba(255,255,255,0.07))' }}>
              {/* متن مناسبت — تمام عرض */}
              <input
                className="input w-full mb-2"
                value={o.text || ''}
                onChange={(e) => setOcc(i, 'text', e.target.value)}
                placeholder={lang === 'fa' ? 'متن پیام مناسبتی...' : 'Occasion message text...'}
              />
              {/* بازه تاریخ + حذف در یک ردیف */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {lang === 'fa' ? 'از' : 'From'}
                  </span>
                  <input type="date" className="input flex-1 min-w-0 text-xs py-1.5" dir="ltr"
                         value={o.start || ''} onChange={(e) => setOcc(i, 'start', e.target.value)} />
                </div>
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {lang === 'fa' ? 'تا' : 'To'}
                  </span>
                  <input type="date" className="input flex-1 min-w-0 text-xs py-1.5" dir="ltr"
                         value={o.end || ''} onChange={(e) => setOcc(i, 'end', e.target.value)} />
                </div>
                <button
                  onClick={() => setExtras((ex) => ({ ...ex, occasions: ex.occasions.filter((_, j) => j !== i) }))}
                  className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: 'rgba(248,113,113,0.1)', color: '#f87171' }}
                  title={lang === 'fa' ? 'حذف' : 'Delete'}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setExtras((ex) => ({ ...ex, occasions: [...(ex?.occasions || []), { text: '', start: '', end: '' }] }))}
            className="btn-secondary text-xs flex items-center gap-1.5"
            disabled={!extras}
          >
            <Plus className="w-3.5 h-3.5" />
            {lang === 'fa' ? 'افزودن پیام' : 'Add message'}
          </button>
          <button onClick={saveExtras} disabled={!extras} className="btn-primary text-xs flex items-center gap-1.5">
            <Save className="w-3.5 h-3.5" />
            {lang === 'fa' ? 'ذخیره' : 'Save'}
          </button>
          {extrasMsg && <span className="text-xs text-gray-400">{extrasMsg}</span>}
        </div>
      </div>

      {/* Level-based welcome */}
      <div className="card mb-4 animate-slide-up" style={{ animationDelay: '0.05s' }}>
        <div className="flex items-center gap-2 mb-1">
          <Crown className="w-4 h-4" style={{ color: '#fbbf24' }} />
          <h2 className="text-sm font-semibold text-white">
            {lang === 'fa' ? 'خوش آمدگویی بر اساس سطح کاربر' : 'Level-based welcome'}
          </h2>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          {lang === 'fa'
            ? 'اگر سطح کاربران فعال باشد، کاربران طلایی و نقره ای پیام مخصوص خود را می بینند. خالی = پیام عادی'
            : 'When user levels are enabled, gold and silver users see their own welcome. Empty = normal welcome'}
        </p>

        {/* دو ستون — هر فیلد به اندازه نصف عرض */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <div>
            <label className="block text-xs mb-1.5 flex items-center gap-1">
              <span>🥇</span>
              <span className="text-gray-400">{lang === 'fa' ? 'کاربران طلایی' : 'Gold users'}</span>
            </label>
            <textarea
              className="input w-full"
              rows={4}
              value={extras?.welcome_gold || ''}
              onChange={(e) => setExtras((ex) => ({ ...ex, welcome_gold: e.target.value }))}
              placeholder={lang === 'fa' ? 'مثلا: کاربر طلایی عزیز خوش آمدید!' : 'e.g. Welcome back, gold member!'}
              disabled={!extras}
            />
          </div>
          <div>
            <label className="block text-xs mb-1.5 flex items-center gap-1">
              <span>🥈</span>
              <span className="text-gray-400">{lang === 'fa' ? 'کاربران نقره ای' : 'Silver users'}</span>
            </label>
            <textarea
              className="input w-full"
              rows={4}
              value={extras?.welcome_silver || ''}
              onChange={(e) => setExtras((ex) => ({ ...ex, welcome_silver: e.target.value }))}
              placeholder={lang === 'fa' ? 'مثلا: کاربر نقره ای عزیز خوش آمدید!' : 'e.g. Welcome back, silver member!'}
              disabled={!extras}
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={saveExtras} disabled={!extras} className="btn-primary text-sm flex items-center gap-1.5">
            <Save className="w-4 h-4" />
            {lang === 'fa' ? 'ذخیره پیام ها' : 'Save messages'}
          </button>
          {extrasMsg && <span className="text-xs text-gray-400">{extrasMsg}</span>}
        </div>
      </div>

      {/* All texts */}
      <div className="card animate-slide-up" style={{ animationDelay: '0.1s' }}>
        {/* header با جستجو در یک ردیف */}
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2 flex-wrap">
              {lang === 'fa' ? 'همه متن ها' : 'All texts'}
              <span className="text-xs text-gray-500 font-normal">
                {texts ? `${texts.length}` : ''}
                {overriddenCount > 0 && (
                  <span className="ms-1.5 px-1.5 py-0.5 rounded"
                        style={{ background: 'var(--primary-15, rgba(99,102,241,0.15))', color: 'var(--primary)' }}>
                    {overriddenCount} {lang === 'fa' ? 'سفارشی' : 'custom'}
                  </span>
                )}
              </span>
            </h2>
          </div>
          <div className="relative flex-shrink-0">
            <Search className="w-4 h-4 absolute top-1/2 -translate-y-1/2 text-gray-500"
                    style={{ insetInlineStart: '0.75rem' }} />
            <input
              className="input ps-9 w-56"
              value={q}
              onChange={(e) => { setQ(e.target.value); setLimit(30) }}
              placeholder={lang === 'fa' ? 'جستجو...' : 'Search texts...'}
            />
          </div>
        </div>

        {isLoading && <p className="text-sm text-gray-500">{lang === 'fa' ? 'در حال بارگذاری...' : 'Loading...'}</p>}

        {filtered.slice(0, limit).map((row) => (
          <TextRow key={row.key} row={row} lang={lang} onSaved={() => qc.invalidateQueries({ queryKey: ['bot-texts'] })} />
        ))}

        {filtered.length > limit && (
          <button onClick={() => setLimit((l) => l + 30)} className="btn-secondary text-xs w-full mt-2">
            {lang === 'fa' ? `نمایش بیشتر (${filtered.length - limit})` : `Show more (${filtered.length - limit})`}
          </button>
        )}

        {!isLoading && filtered.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            {lang === 'fa' ? 'موردی یافت نشد' : 'No results'}
          </p>
        )}
      </div>
    </div>
  )
}