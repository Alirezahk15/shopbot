import api from '../api/client.js'
import { useState, useEffect } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { pathAllowed, getAdminInfo, clearAuth } from '../auth.js'
import AccountModal from './AccountModal.jsx'
import {
  LayoutDashboard, Users, Package, ShoppingCart,
  CreditCard, Ticket, Settings, LogOut, Bot,
  Tag, Shield, Lock, UserCog, Wallet, Radio,
  Languages, ChevronRight, ChevronLeft, ChevronDown, LayoutGrid,
  Palette, FileCode2, UserCircle2,
  SquarePlus,
} from 'lucide-react'

// ── Navigation structure ──
const navGroups = [
  {
    key: 'main',
    label: { fa: 'اصلی', en: 'Main' },
    items: [
      { to: '/', icon: LayoutDashboard, key: 'nav_dashboard', color: '#6366f1', exact: true },
    ],
  },
  {
    key: 'users',
    label: { fa: 'کاربران', en: 'Users' },
    icon: Users,
    color: '#3b82f6',
    items: [
      { to: '/users', icon: Users, key: 'nav_users', color: '#3b82f6' },
      { to: '/admins', icon: UserCog, key: 'nav_admins', color: '#f97316' },
    ],
  },
  {
    key: 'shop',
    label: { fa: 'فروشگاه', en: 'Shop' },
    icon: Package,
    color: '#8b5cf6',
    items: [
      { to: '/products', icon: Package, key: 'nav_products', color: '#8b5cf6' },
      { to: '/orders', icon: ShoppingCart, key: 'nav_orders', color: '#10b981' },
      { to: '/discounts', icon: Tag, key: 'nav_discounts', color: '#06b6d4' },
    ],
  },
  {
    key: 'finance',
    label: { fa: 'مالی', en: 'Finance' },
    icon: CreditCard,
    color: '#f59e0b',
    items: [
      { to: '/payments', icon: CreditCard, key: 'nav_payments', color: '#f59e0b' },
      { to: '/methods', icon: Wallet, key: 'nav_methods', color: '#a855f7' },
    ],
  },
  {
    key: 'support',
    label: { fa: 'پشتیبانی', en: 'Support' },
    icon: Ticket,
    color: '#ec4899',
    items: [
      { to: '/tickets', icon: Ticket, key: 'nav_tickets', color: '#ec4899' },
      { to: '/warranty', icon: Shield, key: 'nav_warranty', color: '#84cc16' },
    ],
  },
  {
    key: 'system',
    label: { fa: 'سیستم', en: 'System' },
    icon: Settings,
    color: '#6b7280',
    items: [
      { to: '/lock', icon: Lock, key: 'nav_lock', color: '#ef4444' },
      { to: '/broadcast', icon: Radio, key: 'nav_broadcast', color: '#14b8a6' },
      { to: '/settings', icon: Settings, key: 'nav_settings', color: '#6b7280' },
    ],
  },
  {
    key: 'advanced',
    label: { fa: 'شخصی‌سازی', en: 'Personalization' },
    icon: Palette,
    color: '#8b5cf6',
    items: [
      { to: '/appearance', icon: Palette, key: 'nav_appearance', color: '#8b5cf6' },
      { to: '/buttons', icon: LayoutGrid, key: 'nav_buttons', color: '#22c55e' },
      { to: '/bot-texts', icon: Languages, key: 'nav_bot_texts', color: '#f59e0b' },
      { to: '/menu-builder', icon: SquarePlus, key: 'nav_menu_builder', color: '#06b6d4' },
    ],
  },
]

// ── Single nav item ──
function NavItem({ item, collapsed, lang }) {
  const [tooltipTop, setTooltipTop] = useState(null)
  return (
    <NavLink
      to={item.to}
      end={item.exact}
      onMouseEnter={(e) => {
        if (!collapsed) return
        const rect = e.currentTarget.getBoundingClientRect()
        setTooltipTop(rect.top + rect.height / 2)
      }}
      onMouseLeave={() => setTooltipTop(null)}
      className={`flex items-center py-2 rounded-xl text-sm font-medium transition-all duration-200 group relative ${collapsed ? 'justify-center px-0' : 'gap-3 px-3'}`}
      style={({ isActive }) => isActive ? {
        background: 'linear-gradient(135deg, var(--primary-25, rgba(99,102,241,0.25)), var(--primary-10, rgba(99,102,241,0.1)))',
        border: '1px solid var(--primary-35, rgba(99,102,241,0.35))',
        boxShadow: '0 2px 10px var(--primary-15, rgba(99,102,241,0.15))',
        color: 'var(--text-strong, white)',
      } : { color: 'var(--text-dim, rgba(156,163,175,0.9))' }}
    >
      {({ isActive }) => (
        <>
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-200"
            style={{
              background: isActive ? 'var(--primary-20, rgba(99,102,241,0.2))' : 'var(--surface-hover, rgba(255,255,255,0.05))',
              border: `1px solid ${isActive ? 'var(--primary-40, rgba(99,102,241,0.4))' : 'transparent'}`,
            }}
          >
            <item.icon className="w-3.5 h-3.5" style={{ color: isActive ? 'var(--primary)' : 'var(--text-dim, rgba(156,163,175,0.8))' }} />
          </div>
          {!collapsed && (
            <span className="truncate flex-1 text-xs">{t(item.key, lang)}</span>
          )}
          {/* Tooltip when collapsed — position:fixed so the scrollable nav cannot clip it */}
          {collapsed && tooltipTop !== null && (
            <div
              className="z-[100] px-2 py-1 rounded-lg text-xs pointer-events-none whitespace-nowrap"
              style={{
                background: 'var(--surface-strong, #1a1a2e)',
                border: '1px solid var(--primary-30, rgba(99,102,241,0.3))',
                color: 'var(--text-strong, white)',
                position: 'fixed',
                top: tooltipTop,
                insetInlineStart: 'calc(var(--sidebar-width, 64px) + 8px)',
                transform: 'translateY(-50%)',
              }}
            >
              {t(item.key, lang)}
            </div>
          )}
        </>
      )}
    </NavLink>
  )
}

// ── Group with accordion ──
function NavGroup({ group, collapsed, lang, openKey, onToggle }) {
  const location = useLocation()
  const isGroupActive = group.items.some(item =>
    item.exact ? location.pathname === item.to : location.pathname.startsWith(item.to)
  )

  // Single-item groups (Dashboard) — render directly without accordion
  if (group.items.length === 1 && !group.icon) {
    return <NavItem item={group.items[0]} collapsed={collapsed} lang={lang} />
  }

  // In collapsed mode — show items directly (no accordion header)
  if (collapsed) {
    return (
      <div className="space-y-0.5">
        {group.items.map(item => (
          <NavItem key={item.to} item={item} collapsed={true} lang={lang} />
        ))}
      </div>
    )
  }

  const isOpen = openKey === group.key

  // Height: each item is 36px + 2px gap, plus 20px top/bottom padding + 16px shadow bleed
  const subMenuHeight = group.items.length * 38 + 36

  return (
    <div>
      {/* Group header button */}
      <button
        onClick={() => onToggle(group.key)}
        className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all duration-200"
        style={isGroupActive ? {
          background: 'var(--primary-10, rgba(99,102,241,0.1))',
          color: 'var(--primary)',
        } : { color: 'var(--text-dim, rgba(156,163,175,0.9))' }}
        onMouseEnter={e => { if (!isGroupActive) e.currentTarget.style.color = 'var(--text-strong, white)' }}
        onMouseLeave={e => { if (!isGroupActive) e.currentTarget.style.color = 'var(--text-dim, rgba(156,163,175,0.9))' }}
      >
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{
            background: isGroupActive ? 'var(--primary-20, rgba(99,102,241,0.2))' : 'var(--surface-hover, rgba(255,255,255,0.05))',
            border: `1px solid ${isGroupActive ? 'var(--primary-40, rgba(99,102,241,0.4))' : 'transparent'}`,
          }}
        >
          <group.icon className="w-3.5 h-3.5" style={{ color: isGroupActive ? 'var(--primary)' : 'var(--text-dim, rgba(156,163,175,0.8))' }} />
        </div>
        <span className="flex-1 text-start">{group.label[lang] || group.label.en}</span>
        <ChevronDown
          className="w-3.5 h-3.5 flex-shrink-0 transition-transform duration-250"
          style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
        />
      </button>

      {/* Sub-items — animated expand/collapse
          NOTE: overflow-visible is required so box-shadow on active items is not clipped.
          We use maxHeight for the animation and add extra height for shadow bleed. */}
      <div
        className="transition-all duration-250"
        style={{
          maxHeight: isOpen ? `${subMenuHeight}px` : '0px',
          opacity: isOpen ? 1 : 0,
          overflow: isOpen ? 'visible' : 'hidden',
        }}
      >
        {/* Indented sub-items with left border */}
        <div
          className="ms-3 mt-1 pb-3 ps-3 space-y-0.5"
          style={{ borderInlineStart: '1px solid var(--border-soft, rgba(255,255,255,0.07))' }}
        >
          {group.items.map(item => (
            <NavItem key={item.to} item={item} collapsed={false} lang={lang} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main Sidebar ──
export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { lang, setLang } = useApp()
  const [collapsed, setCollapsed] = useState(false)
  const [brand, setBrand] = useState(null)

  // لوگو و نام برند سفارشی از تنظیمات پنل
  useEffect(() => {
    api.get('/brand').then(r => setBrand(r.data)).catch(() => {})
  }, [])
  const [showAccount, setShowAccount] = useState(false)
  const [langMenu, setLangMenu] = useState(false)
  const adminInfo = getAdminInfo()

  // Only show sections this admin has permission to access
  const visibleGroups = navGroups
    .map(group => ({ ...group, items: group.items.filter(item => pathAllowed(item.to)) }))
    .filter(group => group.items.length > 0)

  // Find which group contains the current active route — open it by default
  const getDefaultOpenKey = () => {
    for (const group of visibleGroups) {
      if (group.items.length > 1 || group.icon) {
        const hasActive = group.items.some(item =>
          item.exact ? location.pathname === item.to : location.pathname.startsWith(item.to)
        )
        if (hasActive) return group.key
      }
    }
    return null
  }

  const [openKey, setOpenKey] = useState(getDefaultOpenKey)

  // Keep the open accordion group in sync with the current route
  useEffect(() => {
    const key = getDefaultOpenKey()
    if (key) setOpenKey(key)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

  const handleToggle = (key) => {
    // If clicking the already-open group, close it; otherwise open the new one
    setOpenKey(prev => prev === key ? null : key)
  }

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  // Keep the sidebar width available to the Layout (App.jsx) so <main> can
  // offset itself correctly, and expose it as a CSS var instead of prop
  // drilling through the router tree.
  useEffect(() => {
    document.documentElement.style.setProperty('--sidebar-width', collapsed ? '64px' : '220px')
  }, [collapsed])

  return (
    <aside
      className="flex flex-col flex-shrink-0 transition-all duration-300"
      style={{
        width: collapsed ? '64px' : '220px',
        height: '100vh',
        position: 'fixed',
        insetInlineStart: 0,
        top: 0,
        zIndex: 40,
        background: 'var(--sidebar-bg, linear-gradient(180deg, #0d0d1f 0%, #111128 100%))',
        borderInlineEnd: '1px solid var(--primary-15, rgba(99,102,241,0.15))',
      }}
    >
      {/* Logo + collapse toggle */}
      <div
        className="flex items-center px-3 py-4"
        style={{
          borderBottom: '1px solid var(--border-soft, rgba(255,255,255,0.06))',
          justifyContent: collapsed ? 'center' : 'space-between',
          flexDirection: collapsed ? 'column' : 'row',
          gap: collapsed ? '10px' : 0,
        }}
      >
        {!collapsed && (
          <div className="flex items-center gap-2.5 min-w-0">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{
                background: 'linear-gradient(135deg, var(--primary), var(--accent))',
                boxShadow: '0 4px 12px var(--primary-40, rgba(99,102,241,0.4))',
              }}
            >
              {brand && brand.logo ? <img src={brand.logo} alt="" className="w-full h-full rounded-xl object-cover" /> : <Bot className="w-4 h-4 text-white" />}
            </div>
            <div className="min-w-0">
              <div className="font-bold text-sm leading-tight truncate" style={{ color: 'var(--text-strong, white)' }}>{(brand && brand.title) || 'Shop Bot'}</div>
              <div className="text-xs truncate" style={{ color: 'var(--primary)' }}>
                {lang === 'fa' ? 'پنل مدیریت' : 'Admin Panel'}
              </div>
            </div>
          </div>
        )}

        {collapsed && (
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, var(--primary), var(--accent))' }}
          >
            {brand && brand.logo ? <img src={brand.logo} alt="" className="w-full h-full rounded-xl object-cover" /> : <Bot className="w-4 h-4 text-white" />}
          </div>
        )}

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
          style={{
            background: 'var(--surface-hover, rgba(255,255,255,0.05))',
            border: '1px solid var(--border-soft, rgba(255,255,255,0.06))',
            color: 'var(--text-dim, #6b7280)',
            marginInlineStart: collapsed ? 0 : '4px',
          }}
          title={collapsed
            ? (lang === 'fa' ? 'باز کردن' : 'Expand')
            : (lang === 'fa' ? 'جمع کردن' : 'Collapse')
          }
        >
          {collapsed
            ? <ChevronRight className="w-3.5 h-3.5 rtl-flip" />
            : <ChevronLeft className="w-3.5 h-3.5 rtl-flip" />
          }
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto overflow-x-hidden">
        {visibleGroups.map(group => (
          <NavGroup
            key={group.key}
            group={group}
            collapsed={collapsed}
            lang={lang}
            openKey={openKey}
            onToggle={handleToggle}
          />
        ))}
      </nav>

      {/* Bottom controls */}
      <div className="px-2 py-3 space-y-2" style={{ borderTop: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
        {/* Docs + Language — two columns */}
        <div className={`relative ${collapsed ? 'flex flex-col gap-1 items-center' : 'grid grid-cols-2 gap-1.5'}`}>
          {/* API docs — opens in a new tab */}
          <button
            onClick={() => window.open('/api-docs', '_blank', 'noopener')}
            title={t('nav_apidocs', lang)}
            className={`flex items-center justify-center gap-1.5 py-2 rounded-xl text-[11px] font-medium transition-all duration-200 hover:brightness-125 ${collapsed ? 'w-9' : ''}`}
            style={{ color: 'var(--text-dim, #9ca3af)', background: 'var(--surface-hover, rgba(255,255,255,0.05))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}
          >
            <FileCode2 className="w-3.5 h-3.5 flex-shrink-0" />
            {!collapsed && <span className="truncate">{lang === 'fa' ? 'مستندات' : 'Docs'}</span>}
          </button>

          {/* Language selector — opens a dropdown */}
          <button
            onClick={() => setLangMenu(v => !v)}
            title={lang === 'fa' ? 'انتخاب زبان' : 'Select language'}
            className={`flex items-center justify-center gap-1 py-2 rounded-xl text-[11px] font-medium transition-all duration-200 hover:brightness-125 ${collapsed ? 'w-9' : ''}`}
            style={{ color: 'var(--text-dim, #9ca3af)', background: langMenu ? 'rgba(255,255,255,0.1)' : 'var(--surface-hover, rgba(255,255,255,0.05))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}
          >
            <Languages className="w-3.5 h-3.5 flex-shrink-0" />
            {!collapsed && <span className="truncate">{lang === 'fa' ? 'فارسی' : 'English'}</span>}
            {!collapsed && <ChevronDown className={`w-3 h-3 flex-shrink-0 transition-transform duration-200 ${langMenu ? 'rotate-180' : ''}`} />}
          </button>

          {/* Language dropdown menu */}
          {langMenu && (
            <div
              className="absolute bottom-full mb-1.5 rounded-xl overflow-hidden shadow-2xl z-50"
              style={{
                insetInlineEnd: 0,
                width: collapsed ? '140px' : 'calc(50% - 3px)',
                minWidth: '120px',
                background: 'var(--surface, #131c2e)',
                border: '1px solid var(--border-soft, rgba(255,255,255,0.1))',
              }}
            >
              {[
                { code: 'fa', label: '🇮🇷 فارسی' },
                { code: 'en', label: '🇬🇧 English' },
              ].map(o => (
                <button
                  key={o.code}
                  onClick={() => { setLang(o.code); setLangMenu(false) }}
                  className="w-full flex items-center justify-between px-3 py-2 text-[11px] font-medium transition-colors hover:bg-white/5"
                  style={{
                    color: lang === o.code ? 'var(--accent, #10b981)' : 'var(--text-dim, #9ca3af)',
                    background: lang === o.code ? 'var(--surface-hover, rgba(255,255,255,0.05))' : 'transparent',
                  }}
                >
                  <span>{o.label}</span>
                  {lang === o.code && <span>✓</span>}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Account card — avatar + name + logout icon */}
        <div
          className={`flex items-center rounded-xl transition-all duration-200 ${collapsed ? 'flex-col gap-1.5 py-2 px-1' : 'gap-2 p-2'}`}
          style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}
        >
          <button
            onClick={() => setShowAccount(true)}
            title={lang === 'fa' ? 'حساب کاربری و امنیت' : 'Account & Security'}
            className={`flex items-center min-w-0 ${collapsed ? 'flex-col' : 'flex-1 gap-2 text-start'}`}
          >
            {/* Avatar */}
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-gradient-to-br from-emerald-400 to-teal-600 text-white text-xs font-bold uppercase shadow-lg">
              {(adminInfo?.username || 'A').slice(0, 1)}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold truncate" style={{ color: 'var(--text-main, #e5e7eb)' }}>
                  {adminInfo?.username || (lang === 'fa' ? 'حساب کاربری' : 'Account')}
                </div>
                <div className="text-[10px] truncate" style={{ color: 'var(--text-dim, #9ca3af)' }}>
                  {lang === 'fa' ? 'مدیر پنل' : 'Panel admin'}
                </div>
              </div>
            )}
          </button>

          {/* Logout icon */}
          <button
            onClick={handleLogout}
            title={t('nav_logout', lang)}
            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-200 hover:bg-red-900/30"
            style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}
          >
            <LogOut className="w-3.5 h-3.5" style={{ color: '#ef4444' }} />
          </button>
        </div>
      </div>

      {showAccount && <AccountModal lang={lang} onClose={() => setShowAccount(false)} />}
    </aside>
  )
}
