import { createContext, useContext, useState, useEffect } from 'react'
import { ACCENT_PRESETS, DEFAULT_ACCENT } from '../theme.js'

const AppContext = createContext()

// Converts '#rrggbb' + alpha(0-1) into 'rgba(r,g,b,a)'. Avoids relying on the
// CSS color-mix() function so every accent color works on older browsers too.
function hexToRgba(hex, alpha) {
  const clean = (hex || '#6366f1').replace('#', '')
  const r = parseInt(clean.slice(0, 2), 16)
  const g = parseInt(clean.slice(2, 4), 16)
  const b = parseInt(clean.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// فونت‌های قابل انتخاب پنل (صفحه تم و ظاهر)
export const FONT_STACKS = {
  default: "'Vazirmatn', 'Inter', system-ui, sans-serif",
  tahoma: "Tahoma, 'Vazirmatn', sans-serif",
  system: "system-ui, -apple-system, 'Segoe UI', sans-serif",
  serif: "Georgia, 'Times New Roman', serif",
}

export function AppProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('panel_lang') || 'fa')
  // darkMode defaults to true (this panel's native look is dark); explicit 'false' opts into light mode
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('panel_dark') !== 'false')
  const [accent, setAccentState] = useState(() => localStorage.getItem('panel_accent') || DEFAULT_ACCENT)
  const [font, setFontState] = useState(() => localStorage.getItem('panel_font') || 'default')
  const [textScale, setTextScaleState] = useState(() => {
    const v = parseInt(localStorage.getItem('panel_scale') || '100', 10)
    return Number.isFinite(v) ? Math.min(120, Math.max(85, v)) : 100
  })

  useEffect(() => {
    localStorage.setItem('panel_lang', lang)
    // RTL for Persian
    document.documentElement.dir = lang === 'fa' ? 'rtl' : 'ltr'
    document.documentElement.lang = lang
  }, [lang])

  useEffect(() => {
    localStorage.setItem('panel_dark', darkMode)
    document.documentElement.classList.toggle('dark', darkMode)
    document.documentElement.classList.toggle('light-mode', !darkMode)
  }, [darkMode])

  // Applies the chosen accent color AND the light/dark surface palette as CSS
  // variables on <html>, so every component (including ones using inline
  // styles like Sidebar) can react to both without needing color-mix().
  useEffect(() => {
    localStorage.setItem('panel_accent', accent)
    const preset = ACCENT_PRESETS.find(p => p.key === accent) || ACCENT_PRESETS[0]
    const root = document.documentElement.style

    root.setProperty('--primary', preset.primary)
    root.setProperty('--primary-dark', preset.primaryDark)
    root.setProperty('--accent', preset.accent)

    // Pre-computed alpha variants of the primary color (replaces color-mix()).
    ;[10, 15, 20, 25, 30, 35, 40, 50, 60, 80].forEach(pct => {
      root.setProperty(`--primary-${pct}`, hexToRgba(preset.primary, pct / 100))
    })

    // Light/dark aware surface palette.
    // Tint the sidebar background with the chosen accent so switching
    // presets visibly changes the sidebar too, not just buttons/highlights.
    const sidebarTint = hexToRgba(preset.primary, darkMode ? 0.20 : 0.12)
    // Fade the tint to 0% alpha of the SAME hue (not `transparent`) to avoid
    // a grey band mid-gradient, and paint it over an opaque base layer so
    // nothing behind the sidebar (modal overlays, glows) can bleed through.
    const sidebarFade = hexToRgba(preset.primary, 0)
    if (darkMode) {
      root.setProperty('--bg', '#0f0f1a')
      root.setProperty('--sidebar-bg', `linear-gradient(180deg, ${sidebarTint} 0%, ${sidebarFade} 45%), linear-gradient(180deg, #0d0d1f 0%, #111128 100%)`)
      root.setProperty('--surface-hover', 'rgba(255,255,255,0.05)')
      root.setProperty('--surface-strong', '#1a1a2e')
      root.setProperty('--border-soft', 'rgba(255,255,255,0.07)')
      root.setProperty('--text-dim', 'rgba(156,163,175,0.9)')
      root.setProperty('--text-strong', '#ffffff')
      root.setProperty('--ambient-opacity', '0.35')
      root.setProperty('--shadow-elevated', '0 8px 25px rgba(0,0,0,0.4)')
      root.setProperty('--shadow-modal', '0 25px 50px rgba(0,0,0,0.5)')
    } else {
      root.setProperty('--bg', '#f5f6fa')
      root.setProperty('--sidebar-bg', `linear-gradient(180deg, ${sidebarTint} 0%, ${sidebarFade} 40%), linear-gradient(180deg, #ffffff 0%, #eef0f5 100%)`)
      root.setProperty('--surface-hover', 'rgba(0,0,0,0.045)')
      root.setProperty('--surface-strong', '#ffffff')
      root.setProperty('--border-soft', 'rgba(0,0,0,0.09)')
      root.setProperty('--text-dim', 'rgba(55,65,81,0.95)')
      root.setProperty('--text-strong', '#111827')
      root.setProperty('--ambient-opacity', '0.12')
      root.setProperty('--shadow-elevated', '0 8px 24px rgba(100,116,139,0.16)')
      root.setProperty('--shadow-modal', '0 24px 48px rgba(100,116,139,0.22)')
    }
  }, [accent, darkMode])

  // فونت و اندازه متن پنل
  useEffect(() => {
    localStorage.setItem('panel_font', font)
    document.body.style.fontFamily = FONT_STACKS[font] || FONT_STACKS.default
  }, [font])

  useEffect(() => {
    localStorage.setItem('panel_scale', String(textScale))
    document.documentElement.style.fontSize = `${textScale}%`
  }, [textScale])

  const toggleLang = () => setLang(l => l === 'fa' ? 'en' : 'fa')
  const toggleDark = () => setDarkMode(d => !d)
  const setAccent = (key) => setAccentState(key)

  return (
    <AppContext.Provider value={{ lang, setLang, darkMode, toggleLang, toggleDark, accent, setAccent, font, setFont: setFontState, textScale, setTextScale: setTextScaleState }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  return useContext(AppContext)
}
