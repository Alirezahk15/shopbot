import ImageUploader from '../components/ImageUploader.jsx'
import { useState, useEffect } from 'react'
import { useApp, FONT_STACKS } from '../context/AppContext.jsx'
import api from '../api/client.js'
import { ACCENT_PRESETS } from '../theme.js'
import { Moon, Sun, Check, Palette, Sparkles, Type, Building2, Sliders } from 'lucide-react'

const FONTS = [
  { key: 'default', fa: 'وزیرمتن', en: 'Vazirmatn' },
  { key: 'tahoma',  fa: 'تاهوما',  en: 'Tahoma'   },
  { key: 'system',  fa: 'سیستم',   en: 'System'   },
  { key: 'serif',   fa: 'سریف',    en: 'Serif'    },
]

export default function Appearance() {
  const { lang, darkMode, toggleDark, accent, setAccent, font, setFont, textScale, setTextScale } = useApp()
  const [brandTitle, setBrandTitle] = useState('')
  const [brandLogo,  setBrandLogo]  = useState('')
  const [brandMsg,   setBrandMsg]   = useState('')

  useEffect(() => {
    api.get('/brand')
      .then(r => { setBrandTitle(r.data.title || ''); setBrandLogo(r.data.logo || '') })
      .catch(() => {})
  }, [])

  const saveBrand = async () => {
    try {
      await api.post('/settings/bulk', { values: { panel_title: brandTitle, panel_logo_url: brandLogo } })
      setBrandMsg(lang === 'fa' ? 'ذخیره شد - برای نمایش در سایدبار رفرش کنید' : 'Saved - refresh to update the sidebar')
    } catch {
      setBrandMsg(lang === 'fa' ? 'خطا در ذخیره' : 'Save failed')
    }
    setTimeout(() => setBrandMsg(''), 4000)
  }

  return (
    <div className="page-enter">
      <div className="flex items-center gap-3 mb-6">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, var(--primary), var(--accent))', boxShadow: '0 4px 15px var(--primary-35, rgba(99,102,241,0.35))' }}
        >
          <Palette className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="section-title mb-0">{lang === 'fa' ? 'تم و ظاهر' : 'Appearance'}</h1>
          <p className="text-sm text-gray-400">
            {lang === 'fa' ? 'شخصی سازی رنگ بندی، فونت و حالت نمایش پنل' : "Customize the panel color scheme, font, and display mode"}
          </p>
        </div>
      </div>

      {/* Display mode - single row, pill toggle */}
      <div className="card mb-4 animate-slide-up">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                 style={{ background: 'var(--primary-15, rgba(99,102,241,0.15))' }}>
              {darkMode ? <Moon className="w-4 h-4" style={{ color: 'var(--primary)' }} /> : <Sun className="w-4 h-4" style={{ color: 'var(--primary)' }} />}
            </div>
            <div>
              <p className="text-sm font-semibold text-white leading-tight">
                {lang === 'fa' ? 'حالت نمایش' : 'Display mode'}
              </p>
              <p className="text-xs text-gray-500">
                {lang === 'fa' ? 'بین حالت تیره و روشن سوئیچ کنید' : 'Switch between dark and light mode'}
              </p>
            </div>
          </div>
          <div className="flex rounded-xl p-1 gap-1 flex-shrink-0"
               style={{ background: 'var(--surface-hover, rgba(255,255,255,0.05))', border: '1px solid var(--border-soft, rgba(255,255,255,0.08))' }}>
            {[
              { isDark: true,  IC: Moon, fa: 'تیره',  en: 'Dark'  },
              { isDark: false, IC: Sun,  fa: 'روشن', en: 'Light' },
            ].map(({ isDark, IC, fa, en }) => {
              const active = darkMode === isDark
              return (
                <button key={String(isDark)}
                  onClick={() => { if (darkMode !== isDark) toggleDark() }}
                  className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200"
                  style={{
                    background: active ? 'var(--primary)' : 'transparent',
                    color: active ? '#fff' : 'var(--text-dim, #9ca3af)',
                    boxShadow: active ? '0 2px 8px var(--primary-35, rgba(99,102,241,0.35))' : 'none',
                  }}>
                  <IC className="w-3.5 h-3.5" />
                  {lang === 'fa' ? fa : en}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Color theme */}
      <div className="card mb-4 animate-slide-up" style={{ animationDelay: '0.05s' }}>
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-4 h-4" style={{ color: 'var(--primary)' }} />
          <h2 className="text-sm font-semibold text-white">
            {lang === 'fa' ? 'رنگ بندی پنل' : 'Panel color theme'}
          </h2>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          {lang === 'fa' ? 'یک تم رنگی برای دکمه ها، سایدبار و المان های اصلی انتخاب کنید' : 'Pick a color theme for buttons, the sidebar, and key UI elements'}
        </p>
        {['dark', 'light'].map(groupKey => (
          <div key={groupKey} className="mb-4 last:mb-0">
            <p className="text-xs font-semibold uppercase tracking-wider mb-3"
               style={{ color: 'var(--text-dim, #6b7280)' }}>
              {groupKey === 'dark' ? (lang === 'fa' ? 'تم های تیره' : 'Dark themes') : (lang === 'fa' ? 'تم های روشن' : 'Light themes')}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
              {ACCENT_PRESETS.filter(p => p.group === groupKey).map((preset, i) => {
                const isSelected = accent === preset.key
                return (
                  <button key={preset.key} onClick={() => setAccent(preset.key)}
                    className="relative rounded-xl p-3 text-start overflow-hidden transition-all duration-200 hover-lift"
                    style={{
                      background: `linear-gradient(135deg, ${preset.primary}, ${preset.accent})`,
                      boxShadow: isSelected
                        ? `0 0 0 2px var(--surface-strong, #1a1a2e), 0 0 0 3.5px ${preset.primary}, 0 6px 18px ${preset.primary}50`
                        : `0 3px 10px ${preset.primary}28`,
                      animationDelay: `${i * 0.04}s`,
                    }}>
                    {isSelected && (
                      <div className="absolute top-2 end-2 w-5 h-5 rounded-full bg-white/30 flex items-center justify-center">
                        <Check className="w-3 h-3 text-white" />
                      </div>
                    )}
                    <p className="font-semibold text-xs text-white drop-shadow-sm leading-snug">
                      {preset.label[lang] || preset.label.en}
                    </p>
                    <p className="text-xs text-white/75 mt-0.5 leading-tight">
                      {preset.desc?.[lang] || preset.desc?.en}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Font & text size */}
      <div className="card mb-4 animate-slide-up" style={{ animationDelay: '0.1s' }}>
        <div className="flex items-center gap-2 mb-1">
          <Type className="w-4 h-4" style={{ color: 'var(--primary)' }} />
          <h2 className="text-sm font-semibold text-white">
            {lang === 'fa' ? 'فونت و اندازه متن' : 'Font & text size'}
          </h2>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          {lang === 'fa' ? 'فونت پنل و مقیاس نوشتاری را انتخاب کنید' : 'Pick the panel font and text scale'}
        </p>
        {/* grid 4-col - equal width, no flex-wrap overflow */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-5">
          {FONTS.map((f) => {
            const active = font === f.key
            return (
              <button key={f.key} onClick={() => setFont(f.key)}
                className="flex flex-col items-center gap-1.5 rounded-xl py-3 px-2 transition-all duration-200 hover-lift"
                style={{
                  background: active ? 'var(--primary-15, rgba(99,102,241,0.15))' : 'var(--surface-hover, rgba(255,255,255,0.04))',
                  border: active ? '1px solid var(--primary-40, rgba(99,102,241,0.4))' : '1px solid var(--border-soft, rgba(255,255,255,0.08))',
                  color: active ? 'var(--primary)' : 'var(--text-dim, #9ca3af)',
                }}>
                <span className="text-xl font-bold leading-none" style={{ fontFamily: FONT_STACKS[f.key] }}>Aa</span>
                <span className="text-xs font-medium">{lang === 'fa' ? f.fa : f.en}</span>
                {active && <Check className="w-3 h-3" />}
              </button>
            )
          })}
        </div>
        {/* slider row */}
        <div className="flex items-center gap-3 rounded-xl px-3 py-2.5"
             style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
          <Sliders className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--text-dim)' }} />
          <span className="text-xs text-gray-400 flex-shrink-0">
            {lang === 'fa' ? 'اندازه متن' : 'Text size'}
          </span>
          <input type="range" min="85" max="120" step="5"
            value={textScale} onChange={(e) => setTextScale(parseInt(e.target.value, 10))}
            className="flex-1 min-w-0" style={{ accentColor: 'var(--primary)' }} />
          <span className="text-xs font-bold flex-shrink-0 w-12 text-center rounded-lg py-0.5"
                style={{ color: 'var(--primary)', background: 'var(--primary-15, rgba(99,102,241,0.15))' }}>
            {textScale}%
          </span>
        </div>
      </div>

      {/* Brand */}
      <div className="card mb-4 animate-slide-up" style={{ animationDelay: '0.15s' }}>
        <div className="flex items-center gap-2 mb-1">
          <Building2 className="w-4 h-4" style={{ color: 'var(--primary)' }} />
          <h2 className="text-sm font-semibold text-white">
            {lang === 'fa' ? 'لوگو و نام برند' : 'Panel logo & brand name'}
          </h2>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          {lang === 'fa' ? 'نام و لوگوی دلخواه شما در سایدبار همه ادمین ها نمایش داده می شود' : 'Shown in the sidebar for all admins'}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{lang === 'fa' ? 'نام برند' : 'Brand name'}</label>
            <input className="input w-full" value={brandTitle} onChange={(e) => setBrandTitle(e.target.value)}
              placeholder={lang === 'fa' ? 'مثلا: Shop Bot' : 'e.g. Shop Bot'} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{lang === 'fa' ? 'لوگوی پنل' : 'Panel logo'}</label>
            <ImageUploader
              value={brandLogo}
              onChange={setBrandLogo}
              lang={lang}
              placeholder="https://example.com/logo.png"
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={saveBrand} className="btn-primary text-sm">{lang === 'fa' ? 'ذخیره برند' : 'Save brand'}</button>
          {brandMsg && <span className="text-xs text-gray-400">{brandMsg}</span>}
        </div>
      </div>

      {/* Live preview */}
      <div className="card animate-slide-up" style={{ animationDelay: '0.2s' }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-dim, #6b7280)' }}>
          {lang === 'fa' ? 'پیش نمایش زنده' : 'Live preview'}
        </p>
        <div className="flex flex-wrap items-center gap-2.5 mb-3">
          <button className="btn-primary text-sm">{lang === 'fa' ? 'دکمه اصلی' : 'Primary button'}</button>
          <button className="btn-secondary text-sm">{lang === 'fa' ? 'دکمه فرعی' : 'Secondary'}</button>
          <span className="badge-blue text-xs">{lang === 'fa' ? 'برچسب' : 'Badge'}</span>
          <span className="gradient-text font-bold text-sm">{lang === 'fa' ? 'متن رنگی' : 'Gradient text'}</span>
        </div>
        <input className="input" style={{ maxWidth: '260px' }}
          placeholder={lang === 'fa' ? 'یک فیلد نمونه...' : 'A sample input...'} readOnly />
      </div>
    </div>
  )
}