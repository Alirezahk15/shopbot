import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import api from '../api/client.js'
import {
  LayoutGrid, Plus, X, Trash2, Keyboard, MousePointerClick, ShieldCheck,
  Save, RotateCcw, EyeOff, User, Wallet, Headphones, Gift, ListTree, Undo2,
} from 'lucide-react'

const MENU_META = {
  main_reply: {
    icon: Keyboard,
    color: '#6366f1',
    desc: { fa: 'دکمه‌هایی که همیشه در پایین صفحه چت ربات نمایش داده می‌شوند', en: 'Buttons always shown at the bottom of the bot chat' },
  },
  main_inline: {
    icon: MousePointerClick,
    color: '#8b5cf6',
    desc: { fa: 'دکمه‌های شیشه‌ای منوی اصلی ربات', en: "Inline (glassy) buttons on the bot's main/welcome menu" },
  },
  admin_panel: {
    icon: ShieldCheck,
    color: '#f59e0b',
    desc: { fa: 'دکمه‌های صفحه اصلی پنل مدیریت داخل ربات', en: 'Buttons on the in-bot admin panel home screen' },
  },
  profile_menu: {
    icon: User,
    color: '#3b82f6',
    desc: { fa: 'دکمه‌های داخل زیرمنوی پروفایل (حساب من)', en: 'Buttons inside the profile submenu' },
  },
  recharge_menu: {
    icon: Wallet,
    color: '#10b981',
    desc: { fa: 'دکمه‌های روش‌های پرداخت در شارژ حساب — فقط روش‌های فعال در ربات نمایش داده می‌شوند', en: 'Payment buttons in the recharge submenu — only enabled methods are shown in the bot' },
  },
  support_menu: {
    icon: Headphones,
    color: '#f59e0b',
    desc: { fa: 'دکمه‌های داخل زیرمنوی پشتیبانی', en: 'Buttons inside the support submenu' },
  },
  invite_menu: {
    icon: Gift,
    color: '#ec4899',
    desc: { fa: 'دکمه‌های داخل زیرمنوی دعوت دوستان', en: 'Buttons inside the invite submenu' },
  },
}

const MENU_ORDER = ['main_reply', 'main_inline', 'admin_panel']

// کدام دکمه‌ها زیرمنوی قابل ویرایش دارند
const SUBMENUS = {
  btn_profile: 'profile_menu',
  btn_recharge: 'recharge_menu',
  btn_support: 'support_menu',
  btn_invite: 'invite_menu',
  kb_support: 'support_menu',
}

const COLORS = [
  { id: '', hex: '#6b7280', name: { fa: 'پیش‌فرض', en: 'Default' } },
  { id: 'blue', hex: '#3b82f6', name: { fa: 'آبی', en: 'Blue' } },
  { id: 'green', hex: '#22c55e', name: { fa: 'سبز', en: 'Green' } },
  { id: 'red', hex: '#ef4444', name: { fa: 'قرمز', en: 'Red' } },
]

function colorHex(colorId) {
  if (!colorId) return null
  return COLORS.find((c) => c.id === colorId)?.hex || null
}

function TabBtn({ active, onClick, icon: Icon, label, color }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap"
      style={{
        background: active ? `${color}15` : 'transparent',
        border: `1px solid ${active ? color + '40' : 'transparent'}`,
        color: active ? color : 'rgba(156,163,175,0.7)',
      }}
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      {label}
    </button>
  )
}

function Pill({ meta, lang, dimmed, stretch, onDrill, isDragging, onDragStart, onDragEnter, onDragEnd, onClick }) {
  const label = (meta.label && meta.label.trim()) || (lang === 'fa' ? meta.default_label_fa : meta.default_label_en)
  const hex = colorHex(meta.color)
  return (
    <button
      type="button"
      draggable
      onDragStart={onDragStart}
      onDragEnter={onDragEnter}
      onDragOver={(e) => e.preventDefault()}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className={`bl-pill px-3 py-2.5 rounded-lg text-sm font-medium transition-all select-none ${stretch ? 'flex-1 min-w-0 text-center truncate' : ''}`}
      style={{
        ...(hex ? { background: `${hex}22`, border: `1px solid ${hex}66`, color: hex } : {}),
        opacity: isDragging ? 0.3 : (dimmed ? 0.55 : 1),
        cursor: 'grab',
        borderStyle: dimmed ? 'dashed' : 'solid',
      }}
    >
      {label}
      {onDrill && (
        <span
          onClick={(e) => { e.stopPropagation(); onDrill() }}
          title={lang === 'fa' ? 'ویرایش دکمه‌های زیرمنو' : 'Edit submenu buttons'}
          className="bl-drill inline-flex items-center justify-center w-5 h-5 rounded-md ms-1.5 align-middle"
        >
          <ListTree className="w-3 h-3" />
        </span>
      )}
    </button>
  )
}

function EditModal({ meta, lang, onClose, onSave, onHide }) {
  const [label, setLabel] = useState(meta.label || '')
  const [color, setColor] = useState(meta.color || '')
  const defaultLabel = lang === 'fa' ? meta.default_label_fa : meta.default_label_en

  return (
    <div
      className="fixed inset-0 z-[999] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={onClose}
    >
      <div
        className="rounded-2xl w-full max-w-sm p-5"
        style={{ background: 'var(--surface-strong, #181b22)', border: '1px solid var(--border-soft, rgba(255,255,255,0.1))' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white text-base">
            {lang === 'fa' ? 'ویرایش دکمه' : 'Edit Button'}
          </h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="text-xs text-gray-500 mb-4">{defaultLabel}</div>

        <label className="block text-xs text-gray-400 mb-1.5">
          {lang === 'fa' ? 'متن دلخواه' : 'Custom text'}
        </label>
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="input mb-4"
          placeholder={defaultLabel}
          autoFocus
        />
        <p className="text-xs text-gray-500 -mt-2 mb-4 leading-relaxed">
          {lang === 'fa'
            ? 'ایموجی پرمیوم: [emoji:شناسه:🔥] — داخل دکمه‌ها ایموجی جایگزین نمایش داده می‌شود (مگر اینکه در تنظیمات فعال شود)'
            : 'Premium emoji: [emoji:ID:🔥] — buttons show the fallback emoji (unless enabled in Settings)'}
        </p>

        {/* افزودن سریع ایموجی به ابتدای متن دکمه */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {['🛍', '📦', '💳', '👤', '🎁', '⭐', '🔥', '💎', '🚀', '📞', '🧾', '🌐'].map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => setLabel((l) => (l ? `${e} ${l}` : `${e} ${defaultLabel || ''}`.trim()))}
              className="w-8 h-8 rounded-lg text-base leading-none"
              style={{ background: 'var(--surface-hover, rgba(255,255,255,0.06))', border: '1px solid var(--border-soft, rgba(255,255,255,0.08))' }}
            >
              {e}
            </button>
          ))}
        </div>

        <label className="block text-xs text-gray-400 mb-2">
          {lang === 'fa' ? 'رنگ دکمه' : 'Button color'}
        </label>
        <div className="flex items-center gap-2.5 mb-2">
          {COLORS.map((c) => (
            <button
              key={c.id}
              onClick={() => setColor(color === c.id ? '' : c.id)}
              title={c.name[lang === 'fa' ? 'fa' : 'en']}
              className="w-9 h-9 rounded-full transition-all"
              style={{
                background: c.hex,
                border: color === c.id ? '3px solid var(--text-main, #e5e7eb)' : '3px solid transparent',
                transform: color === c.id ? 'scale(1.12)' : 'scale(1)',
              }}
            />
          ))}
        </div>
        <p className="text-xs text-gray-500 mb-5 leading-relaxed">
          {lang === 'fa'
            ? 'تلگرام فقط رنگ‌های آبی، سبز و قرمز را برای دکمه‌ها پشتیبانی می‌کند — خاکستری یعنی رنگ پیش‌فرض'
            : 'Telegram only supports blue, green and red button colors — gray means default'}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onHide}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium"
            style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171' }}
          >
            <EyeOff className="w-4 h-4" />
            {lang === 'fa' ? 'مخفی کردن' : 'Hide'}
          </button>
          <button
            type="button"
            onClick={() => onSave({ label, color })}
            className="btn-primary flex-1 justify-center text-sm"
          >
            {t('save', lang)}
          </button>
        </div>
      </div>
    </div>
  )
}

function MenuPanel({ menuKey, data, lang, onDrill }) {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [rows, setRows] = useState([])
  const [hidden, setHidden] = useState([])
  const [metaMap, setMetaMap] = useState({})
  const [editingKey, setEditingKey] = useState(null)
  const [saved, setSaved] = useState(false)
  const draggedKeyRef = useRef(null)
  const [draggedKey, setDraggedKey] = useState(null)
  const meta = MENU_META[menuKey]

  useEffect(() => {
    const map = {}
    data.rows.forEach((row) => row.forEach((item) => { map[item.key] = item }))
    data.hidden.forEach((item) => { map[item.key] = item })
    setMetaMap(map)
    setRows(data.rows.map((row) => row.map((item) => item.key)))
    setHidden(data.hidden.map((item) => item.key))
  }, [data])

  const startDrag = (key) => {
    draggedKeyRef.current = key
    setDraggedKey(key)
  }

  const endDrag = () => {
    draggedKeyRef.current = null
    setDraggedKey(null)
    setRows((prev) => {
      const cleaned = prev.filter((r) => r.length > 0)
      return cleaned.length ? cleaned : [[]]
    })
  }

  const moveItem = (targetRowIdx, targetColIdx) => {
    const key = draggedKeyRef.current
    if (!key) return
    setRows((prevRows) => {
      let rowsCopy = prevRows.map((r) => [...r])
      let tRow = targetRowIdx
      let tCol = targetColIdx
      for (let r = 0; r < rowsCopy.length; r++) {
        const idx = rowsCopy[r].indexOf(key)
        if (idx !== -1) {
          rowsCopy[r].splice(idx, 1)
          if (r === tRow && idx < tCol) tCol = Math.max(0, tCol - 1)
          break
        }
      }
      if (tRow >= rowsCopy.length) {
        rowsCopy.push([])
        tRow = rowsCopy.length - 1
      }
      rowsCopy[tRow] = [...rowsCopy[tRow]]
      tCol = Math.min(tCol, rowsCopy[tRow].length)
      rowsCopy[tRow].splice(tCol, 0, key)
      return rowsCopy
    })
    setHidden((prev) => prev.filter((k) => k !== key))
  }

  const hideItem = (key) => {
    setRows((prev) => {
      const next = prev.map((r) => r.filter((k) => k !== key)).filter((r) => r.length > 0)
      return next.length ? next : [[]]
    })
    setHidden((prev) => (prev.includes(key) ? prev : [...prev, key]))
  }

  const restoreItem = (key) => {
    setRows((prev) => {
      const next = prev.length ? prev.map((r) => [...r]) : [[]]
      if (next.length === 0 || next[0].length === undefined) next.push([])
      next[0] = [...next[0], key]
      return next
    })
    setHidden((prev) => prev.filter((k) => k !== key))
  }

  const handleDropHide = (e) => {
    e.preventDefault()
    if (draggedKeyRef.current) hideItem(draggedKeyRef.current)
    endDrag()
  }

  const handleDropNewRow = (e) => {
    e.preventDefault()
    if (draggedKeyRef.current) moveItem(rows.length, 0)
    endDrag()
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      api.post(`/buttons/${menuKey}`, {
        rows: rows.filter((r) => r.length > 0),
        hidden,
        meta: Object.fromEntries(
          Object.entries(metaMap).map(([k, v]) => [k, { label: v.label || '', color: v.color || '' }])
        ),
      }),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      toast(lang === 'fa' ? 'چیدمان دکمه‌ها ذخیره شد' : 'Button layout saved', 'success')
      queryClient.invalidateQueries({ queryKey: ['button-layout'] })
    },
    onError: () => toast(lang === 'fa' ? 'خطا در ذخیره' : 'Save failed', 'error'),
  })

  const resetMutation = useMutation({
    mutationFn: () => api.post(`/buttons/${menuKey}/reset`),
    onSuccess: () => {
      toast(lang === 'fa' ? 'به حالت پیش‌فرض برگشت' : 'Reset to default', 'success')
      queryClient.invalidateQueries({ queryKey: ['button-layout'] })
    },
    onError: () => toast(lang === 'fa' ? 'خطا در بازنشانی' : 'Reset failed', 'error'),
  })

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${meta.color}20`, border: `1px solid ${meta.color}40` }}>
            <meta.icon className="w-4 h-4" style={{ color: meta.color }} />
          </div>
          <div>
            <div className="font-bold text-white text-sm">{lang === 'fa' ? data.label.fa : data.label.en}</div>
            <div className="text-xs text-gray-500">{lang === 'fa' ? meta.desc.fa : meta.desc.en}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {saved && (
            <span className="text-xs text-green-400">{lang === 'fa' ? 'ذخیره شد ✓' : 'Saved ✓'}</span>
          )}
          <button type="button" onClick={() => resetMutation.mutate()} disabled={resetMutation.isPending} className="btn-secondary text-xs px-3 py-1.5">
            <RotateCcw className="w-3.5 h-3.5" />
            {lang === 'fa' ? 'پیش‌فرض' : 'Reset'}
          </button>
          <button type="button" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="btn-primary text-xs px-3 py-1.5">
            <Save className="w-3.5 h-3.5" />
            {saveMutation.isPending ? t('loading', lang) : t('save', lang)}
          </button>
        </div>
      </div>

      {/* منطقه‌ی مخفی کردن: دکمه را بکش و اینجا ول کن */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDropHide}
        className="flex items-center justify-center gap-2 rounded-xl py-3 mb-4 text-xs"
        style={{ border: '1.5px dashed rgba(239,68,68,0.4)', background: 'rgba(239,68,68,0.06)', color: '#f87171' }}
      >
        <Trash2 className="w-3.5 h-3.5" />
        {lang === 'fa' ? 'برای مخفی کردن یک دکمه، آن را به اینجا بکشید' : 'Drag a button here to hide it from the keyboard'}
      </div>

      <div className="space-y-1.5 mb-4 w-full max-w-md mx-auto">
        {rows.map((row, rowIdx) => (
          <div
            key={rowIdx}
            className="bl-zone flex items-stretch gap-1.5 p-1.5 rounded-xl"
            style={{ minHeight: '52px' }}
          >
            {row.map((key, colIdx) => (
              <Pill
                key={key}
                meta={metaMap[key] || { key }}
                lang={lang}
                stretch
                onDrill={SUBMENUS[key] && onDrill ? () => onDrill(SUBMENUS[key]) : undefined}
                isDragging={draggedKey === key}
                onDragStart={() => startDrag(key)}
                onDragEnter={(e) => { e.preventDefault(); if (draggedKeyRef.current) moveItem(rowIdx, colIdx) }}
                onDragEnd={endDrag}
                onClick={() => setEditingKey(key)}
              />
            ))}
            {/* فضای پایان ردیف برای رها کردن در انتهای ردیف */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDragEnter={(e) => { e.preventDefault(); if (draggedKeyRef.current) moveItem(rowIdx, row.length) }}
              className="bl-zone flex-shrink-0 rounded-lg"
              style={{ width: '26px', minHeight: '38px' }}
            />
          </div>
        ))}

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDropNewRow}
          className="bl-zone flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-xs text-gray-500"
        >
          <Plus className="w-3.5 h-3.5" />
          {lang === 'fa' ? 'ردیف جدید را با رها کردن یک دکمه اینجا بسازید' : 'Drop a button here to start a new row'}
        </div>
      </div>

      {hidden.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-2">
            {lang === 'fa' ? 'دکمه‌های مخفی (برای نمایان دوباره بکشید یا به جدول بالا بکشید)' : 'Hidden buttons (drag up to show, or click to show)'}
          </div>
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); if (draggedKeyRef.current) { restoreItem(draggedKeyRef.current); endDrag() } }}
            className="bl-zone flex items-center gap-2 flex-wrap p-2.5 rounded-xl"
            style={{ minHeight: '52px' }}
          >
            {hidden.map((key) => (
              <Pill
                key={key}
                meta={metaMap[key] || { key }}
                lang={lang}
                dimmed
                isDragging={draggedKey === key}
                onDragStart={() => startDrag(key)}
                onDragEnter={() => {}}
                onDragEnd={endDrag}
                onClick={() => restoreItem(key)}
              />
            ))}
          </div>
        </div>
      )}

      {editingKey && metaMap[editingKey] && (
        <EditModal
          meta={metaMap[editingKey]}
          lang={lang}
          onClose={() => setEditingKey(null)}
          onSave={({ label, color }) => {
            setMetaMap((prev) => ({ ...prev, [editingKey]: { ...prev[editingKey], label, color } }))
            setEditingKey(null)
          }}
          onHide={() => {
            hideItem(editingKey)
            setEditingKey(null)
          }}
        />
      )}
    </div>
  )
}

export default function ButtonLayout() {
  const { lang } = useApp()
  const [activeMenu, setActiveMenu] = useState('main_reply')
  const [menuStack, setMenuStack] = useState([])

  const drill = (menuKey) => {
    setMenuStack((st) => [...st, activeMenu])
    setActiveMenu(menuKey)
  }

  const goBack = () => {
    setMenuStack((st) => {
      const copy = [...st]
      const prev = copy.pop()
      setActiveMenu(prev || 'main_reply')
      return copy
    })
  }

  const { data, isLoading } = useQuery({
    queryKey: ['button-layout'],
    queryFn: () => api.get('/buttons').then((r) => r.data),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.3)' }}>
          <LayoutGrid className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">{lang === 'fa' ? 'چیدمان دکمه‌ها' : 'Button Layout'}</h1>
          <p className="text-sm text-gray-500">
            {lang === 'fa'
              ? 'دکمه‌ها را بکش و جابه‌جا کن، روی یکی کلیک کن تا رنگ/متنش رو عوض کنی، یا به منطقه‌ی قرمز بکشید تا مخفیش کنی'
              : 'Drag buttons to rearrange, click one to change its color/text, or drop it on the red zone to hide it'}
          </p>
        </div>
      </div>

      {isLoading || !data ? (
        <div className="card text-center text-gray-500 py-10">{t('loading', lang)}</div>
      ) : (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            {MENU_ORDER.map((menuKey) => (
              <TabBtn
                key={menuKey}
                active={activeMenu === menuKey}
                onClick={() => { setMenuStack([]); setActiveMenu(menuKey) }}
                icon={MENU_META[menuKey].icon}
                color={MENU_META[menuKey].color}
                label={lang === 'fa' ? data[menuKey].label.fa : data[menuKey].label.en}
              />
            ))}
          </div>

          {!MENU_ORDER.includes(activeMenu) && (
            <button onClick={goBack} className="btn-secondary text-xs flex items-center gap-1.5 w-fit">
              <Undo2 className="w-3.5 h-3.5" />
              {lang === 'fa' ? 'بازگشت به منوی قبلی' : 'Back to previous menu'}
            </button>
          )}

          {data[activeMenu] && (
            <MenuPanel key={activeMenu} menuKey={activeMenu} data={data[activeMenu]} lang={lang} onDrill={drill} />
          )}
        </>
      )}
    </div>
  )
}
