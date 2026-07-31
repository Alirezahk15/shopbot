import ImageUploader from '../components/ImageUploader.jsx'
import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client.js'
import { useApp } from '../context/AppContext.jsx'
import { SquarePlus, Plus, Pencil, Trash2, Link2, MessageSquare, FolderTree, X, Image as ImageIcon, Save, EyeOff, LayoutGrid } from 'lucide-react'

const TYPE_META = {
  text:    { fa: 'متن',    en: 'Text',    icon: MessageSquare, color: '#22c55e' },
  link:    { fa: 'لینک',   en: 'Link',    icon: Link2,         color: '#3b82f6' },
  submenu: { fa: 'زیرمنو', en: 'Submenu', icon: FolderTree,    color: '#f59e0b' },
}

function ButtonModal({ initial, submenus, lang, onClose, onSave }) {
  const [f, setF] = useState(initial)
  const [err, setErr] = useState('')
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }))

  const submit = async () => {
    if (!f.label.trim()) {
      setErr(lang === 'fa' ? 'متن دکمه الزامی است' : 'Label is required')
      return
    }
    if (f.type === 'link' && !/^(https?|tg):\/\//.test(f.content || '')) {
      setErr(lang === 'fa' ? 'لینک باید با http:// یا https:// شروع شود' : 'Link must start with http:// or https://')
      return
    }
    try {
      await onSave({ ...f, parent_id: f.parent_id ? Number(f.parent_id) : null, position: Number(f.position) || 0 })
    } catch (e) {
      setErr(e?.response?.data?.detail || (lang === 'fa' ? 'خطا در ذخیره' : 'Save failed'))
    }
  }

  return (
    <div className="fixed inset-0 z-[999] flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.6)' }} onClick={onClose}>
      <div className="rounded-2xl w-full max-w-md p-5"
           style={{ background: 'var(--surface-strong, #181b22)', border: '1px solid var(--border-soft, rgba(255,255,255,0.1))' }}
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white text-base">
            {initial.id ? (lang === 'fa' ? 'ویرایش دکمه' : 'Edit button') : (lang === 'fa' ? 'دکمه جدید' : 'New button')}
          </h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X className="w-5 h-5" /></button>
        </div>

        <label className="block text-xs text-gray-400 mb-1.5">{lang === 'fa' ? 'متن دکمه' : 'Label'}</label>
        <input className="input mb-3" value={f.label} onChange={(e) => set('label', e.target.value)} autoFocus />

        <label className="block text-xs text-gray-400 mb-1.5">{lang === 'fa' ? 'نوع دکمه' : 'Type'}</label>
        <div className="grid grid-cols-3 gap-2 mb-3">
          {Object.entries(TYPE_META).map(([k, m]) => (
            <button key={k} onClick={() => set('type', k)}
              className="rounded-xl p-2.5 text-xs font-medium flex flex-col items-center gap-1.5 transition-all"
              style={{
                background: f.type === k ? `${m.color}20` : 'var(--surface-hover, rgba(255,255,255,0.04))',
                border: f.type === k ? `1px solid ${m.color}60` : '1px solid var(--border-soft, rgba(255,255,255,0.08))',
                color: f.type === k ? m.color : 'var(--text-dim, #9ca3af)',
              }}>
              <m.icon className="w-4 h-4" />
              {lang === 'fa' ? m.fa : m.en}
            </button>
          ))}
        </div>

        {f.type === 'link' ? (
          <>
            <label className="block text-xs text-gray-400 mb-1.5">{lang === 'fa' ? 'آدرس لینک' : 'URL'}</label>
            <input className="input mb-3" dir="ltr" value={f.content} onChange={(e) => set('content', e.target.value)} placeholder="https://t.me/yourchannel" />
          </>
        ) : (
          <>
            <label className="block text-xs text-gray-400 mb-1.5">
              {f.type === 'submenu' ? (lang === 'fa' ? 'متن بالای زیرمنو (اختیاری)' : 'Submenu header (optional)') : (lang === 'fa' ? 'متن پاسخ (HTML مجاز)' : 'Reply text (HTML allowed)')}
            </label>
            <textarea className="input mb-3" rows={3} value={f.content} onChange={(e) => set('content', e.target.value)} />
          </>
        )}

        {f.type !== 'submenu' && submenus.length > 0 && (
          <>
            <label className="block text-xs text-gray-400 mb-1.5">{lang === 'fa' ? 'قرار گیرد داخل' : 'Place inside'}</label>
            <select className="input mb-3" value={f.parent_id || ''} onChange={(e) => set('parent_id', e.target.value)}>
              <option value="">{lang === 'fa' ? 'منوی اصلی' : 'Main menu'}</option>
              {submenus.map((s) => (<option key={s.id} value={s.id}>{s.label}</option>))}
            </select>
          </>
        )}

        <div className="flex items-center gap-4 mb-4">
          <div className="flex-1">
            <label className="block text-xs text-gray-400 mb-1.5">{lang === 'fa' ? 'ترتیب' : 'Order'}</label>
            <input type="number" className="input" value={f.position} onChange={(e) => set('position', e.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer mt-5">
            <input type="checkbox" checked={!!f.active} onChange={(e) => set('active', e.target.checked)} />
            {lang === 'fa' ? 'فعال' : 'Active'}
          </label>
        </div>

        {err && <p className="text-xs mb-3" style={{ color: '#f87171' }}>{err}</p>}
        <div className="flex gap-2">
          <button onClick={submit} className="btn-primary flex-1 text-sm">{lang === 'fa' ? 'ذخیره' : 'Save'}</button>
          <button onClick={onClose} className="btn-secondary text-sm">{lang === 'fa' ? 'انصراف' : 'Cancel'}</button>
        </div>
      </div>
    </div>
  )
}

const EMPTY = { label: '', type: 'text', content: '', parent_id: '', position: 0, active: true }

export default function MenuBuilder() {
  const { lang } = useApp()
  const qc = useQueryClient()
  const [modal, setModal] = useState(null)
  const [confirmDel, setConfirmDel] = useState(null)

  const { data: buttons, isLoading } = useQuery({
    queryKey: ['menu-buttons'],
    queryFn: () => api.get('/menu-buttons').then((r) => r.data.buttons),
  })
  const { data: cats } = useQuery({
    queryKey: ['mb-categories'],
    queryFn: () => api.get('/products/categories').then((r) => r.data.categories).catch(() => null),
  })
  const { data: settings } = useQuery({
    queryKey: ['mb-settings'],
    queryFn: () => api.get('/settings').then((r) => r.data),
  })

  const [menuImg, setMenuImg] = useState(null)
  const [catImgs, setCatImgs] = useState(null)
  const [imgMsg, setImgMsg] = useState('')

  useEffect(() => {
    if (settings && menuImg === null) setMenuImg(settings.menu_image_main || '')
  }, [settings, menuImg])
  useEffect(() => {
    if (cats && catImgs === null) setCatImgs(Object.fromEntries(cats.map((c) => [c.id, c.image || ''])))
  }, [cats, catImgs])

  const saveImages = async () => {
    try {
      await api.post('/settings/bulk', { values: { menu_image_main: menuImg || '' } })
      for (const c of cats || []) {
        if ((catImgs?.[c.id] ?? '') !== (c.image || '')) {
          await api.put(`/products/categories/${c.id}`, { name: c.name, image: catImgs[c.id] || '' })
        }
      }
      setImgMsg(lang === 'fa' ? 'ذخیره شد' : 'Saved')
      qc.invalidateQueries({ queryKey: ['mb-categories'] })
    } catch {
      setImgMsg(lang === 'fa' ? 'خطا در ذخیره' : 'Save failed')
    }
    setTimeout(() => setImgMsg(''), 4000)
  }

  const refresh = () => qc.invalidateQueries({ queryKey: ['menu-buttons'] })
  const saveBtn = async (f) => {
    if (modal?.data?.id) await api.put(`/menu-buttons/${modal.data.id}`, f)
    else await api.post('/menu-buttons', f)
    setModal(null)
    refresh()
  }
  const del = async (id) => {
    if (confirmDel !== id) {
      setConfirmDel(id)
      setTimeout(() => setConfirmDel((c) => (c === id ? null : c)), 3000)
      return
    }
    await api.delete(`/menu-buttons/${id}`)
    setConfirmDel(null)
    refresh()
  }

  const roots = (buttons || []).filter((b) => !b.parent_id)
  const childrenOf = (id) => (buttons || []).filter((b) => b.parent_id === id)
  const submenus = roots.filter((b) => b.type === 'submenu')

  const ButtonRow = ({ b, child }) => {
    const m = TYPE_META[b.type] || TYPE_META.text
    return (
      <div
        className={`flex items-center gap-3 p-3 rounded-xl mb-2 ${child ? 'ms-8' : ''}`}
        style={{ border: '1px solid var(--border-soft, rgba(255,255,255,0.07))', background: 'var(--surface-hover, rgba(255,255,255,0.03))', opacity: b.active ? 1 : 0.5 }}
      >
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
             style={{ background: `${m.color}20`, border: `1px solid ${m.color}40` }}>
          <m.icon className="w-4 h-4" style={{ color: m.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-white truncate">
            {b.label}
            {!b.active && <EyeOff className="w-3.5 h-3.5 inline ms-2 text-gray-500" />}
          </div>
          <div className="text-xs text-gray-500 truncate" dir={b.type === 'link' ? 'ltr' : undefined}>
            {lang === 'fa' ? m.fa : m.en}{b.content ? ` — ${String(b.content).slice(0, 50)}` : ''}
          </div>
        </div>
        <button onClick={() => setModal({ data: b })}
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: 'var(--surface-hover, rgba(255,255,255,0.05))', color: 'var(--text-dim, #9ca3af)' }}>
          <Pencil className="w-3.5 h-3.5" />
        </button>
        <button onClick={() => del(b.id)}
          className="h-8 rounded-lg flex items-center justify-center flex-shrink-0 px-2 text-xs font-medium"
          style={{ background: confirmDel === b.id ? 'rgba(248,113,113,0.2)' : 'var(--surface-hover, rgba(255,255,255,0.05))', color: '#f87171', minWidth: '32px' }}>
          {confirmDel === b.id ? (lang === 'fa' ? 'مطمئن؟' : 'Sure?') : <Trash2 className="w-3.5 h-3.5" />}
        </button>
      </div>
    )
  }

  return (
    <div className="page-enter">

      {/* header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
             style={{ background: 'linear-gradient(135deg, #06b6d4, #3b82f6)', boxShadow: '0 4px 15px rgba(6,182,212,0.35)' }}>
          <SquarePlus className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <h1 className="section-title mb-0">{lang === 'fa' ? 'منوساز' : 'Menu Builder'}</h1>
          <p className="text-sm text-gray-400">
            {lang === 'fa' ? 'دکمه های دلخواه را به منوی اصلی ربات اضافه کنید' : 'Add custom buttons to the bot main menu (link, text, submenu)'}
          </p>
        </div>
        <button onClick={() => setModal({ data: null })} className="btn-primary text-sm flex items-center gap-1.5">
          <Plus className="w-4 h-4" />
          {lang === 'fa' ? 'دکمه جدید' : 'New button'}
        </button>
      </div>

      {/* Custom buttons */}
      <div className="card mb-4 animate-slide-up">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <LayoutGrid className="w-4 h-4" style={{ color: 'var(--primary)' }} />
            {lang === 'fa' ? 'دکمه های سفارشی' : 'Custom buttons'}
            {(buttons || []).length > 0 && (
              <span className="text-xs text-gray-500 font-normal">
                ({(buttons || []).length})
              </span>
            )}
          </h2>
        </div>
        {isLoading && <p className="text-sm text-gray-500">{lang === 'fa' ? 'در حال بارگذاری...' : 'Loading...'}</p>}
        {!isLoading && roots.length === 0 && (
          <div className="text-center py-8 rounded-xl"
               style={{ border: '1px dashed var(--border-soft, rgba(255,255,255,0.1))' }}>
            <SquarePlus className="w-8 h-8 mx-auto mb-2 text-gray-600" />
            <p className="text-sm text-gray-500 mb-3">
              {lang === 'fa' ? 'هنوز دکمه ای اضافه نشده' : 'No buttons yet'}
            </p>
            <button onClick={() => setModal({ data: null })} className="btn-secondary text-xs flex items-center gap-1.5 mx-auto">
              <Plus className="w-3.5 h-3.5" />
              {lang === 'fa' ? 'اولین دکمه را بساز' : 'Create first button'}
            </button>
          </div>
        )}
        {roots.map((b) => (
          <div key={b.id}>
            <ButtonRow b={b} />
            {childrenOf(b.id).map((c) => <ButtonRow key={c.id} b={c} child />)}
          </div>
        ))}
      </div>

      {/* Menu images */}
      <div className="card animate-slide-up" style={{ animationDelay: '0.05s' }}>
        <div className="flex items-center gap-2 mb-1">
          <ImageIcon className="w-4 h-4" style={{ color: 'var(--primary)' }} />
          <h2 className="text-sm font-semibold text-white">
            {lang === 'fa' ? 'تصویر منوها' : 'Menu images'}
          </h2>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          {lang === 'fa'
            ? 'آدرس URL یا file_id تلگرام — خالی = بدون تصویر. بنر محصولات از صفحه محصولات تنظیم می شود'
            : 'Image URL or Telegram file_id — empty = no image. Product banners are set on the Products page'}
        </p>

        {/* main menu image */}
        <div className="mb-4">
          <label className="block text-xs text-gray-400 mb-1.5">
            {lang === 'fa' ? 'تصویر منوی اصلی (/start)' : 'Main menu image (/start)'}
          </label>
          <ImageUploader
            value={menuImg || ''}
            onChange={(v) => setMenuImg(v)}
            lang={lang}
            placeholder="https://example.com/banner.jpg"
            disabled={menuImg === null}
          />
        </div>

        {/* category images - proper 2-col grid */}
        {(cats || []).length > 0 && (
          <div className="mb-4">
            <label className="block text-xs text-gray-400 mb-2">
              {lang === 'fa' ? 'تصویر دسته بندی ها' : 'Category images'}
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {(cats || []).map((c) => (
                <div key={c.id}
                     className="flex items-center gap-2 rounded-lg p-2"
                     style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
                  <span className="text-xs text-gray-300 truncate flex-shrink-0 w-24">
                    {c.name}
                  </span>
                  <input
                    className="input flex-1 text-xs py-1.5"
                    dir="ltr"
                    value={catImgs?.[c.id] || ''}
                    onChange={(e) => setCatImgs((p) => ({ ...(p || {}), [c.id]: e.target.value }))}
                    placeholder="https://..."
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button onClick={saveImages} disabled={menuImg === null} className="btn-primary text-sm flex items-center gap-1.5">
            <Save className="w-4 h-4" />
            {lang === 'fa' ? 'ذخیره تصاویر' : 'Save images'}
          </button>
          {imgMsg && <span className="text-xs text-gray-400">{imgMsg}</span>}
        </div>
      </div>

      {modal && (
        <ButtonModal
          initial={modal.data ? { ...modal.data, parent_id: modal.data.parent_id || '', active: !!modal.data.active } : EMPTY}
          submenus={submenus.filter((s) => s.id !== modal.data?.id)}
          lang={lang}
          onClose={() => setModal(null)}
          onSave={saveBtn}
        />
      )}
    </div>
  )
}