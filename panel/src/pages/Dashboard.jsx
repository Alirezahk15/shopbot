import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import api from '../api/client.js'
import {
  Users, ShoppingCart, DollarSign, Ticket, CreditCard, Shield,
  RefreshCw, TrendingUp, Package, ArrowUpRight, Clock
} from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts'

function StatCard({ icon: Icon, label, value, sub, gradient, iconColor, trend }) {
  return (
    <div className="stat-card animate-fade-in">
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: gradient, boxShadow: `0 4px 15px ${iconColor}30` }}
      >
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-2xl font-bold text-white">{value ?? '—'}</div>
        <div className="text-xs text-gray-400 truncate mt-0.5">{label}</div>
        {sub && (
          <div className="flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" style={{ color: iconColor }} />
            <span className="text-xs" style={{ color: iconColor }}>{sub}</span>
          </div>
        )}
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label, lang }) => {
  if (active && payload && payload.length) {
    return (
      <div
        className="rounded-xl px-3 py-2 text-xs"
        style={{
          background: 'var(--surface-strong, #1a1a2e)',
          border: '1px solid var(--primary-30, rgba(99,102,241,0.3))',
          boxShadow: 'var(--shadow-elevated, 0 8px 25px rgba(0,0,0,0.4))',
        }}
      >
        <p className="text-gray-400 mb-1">{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color }} className="font-semibold">
            {p.name}: {p.name === 'revenue' ? `$${p.value}` : p.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function Dashboard() {
  const { lang } = useApp()
  const [days, setDays] = useState(7)
  // شخصی‌سازی چیدمان داشبورد — ذخیره در مرورگر هر ادمین
  const [hiddenSections, setHiddenSections] = useState(() => {
    try { return JSON.parse(localStorage.getItem('dash_hidden') || '[]') } catch { return [] }
  })
  const toggleSection = (k) => setHiddenSections((prev) => {
    const next = prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k]
    localStorage.setItem('dash_hidden', JSON.stringify(next))
    return next
  })
  const show = (k) => !hiddenSections.includes(k)

  const { data: stats, isLoading: statsLoading, refetch, isFetching } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard').then(r => r.data),
    refetchInterval: 30000,
  })

  const { data: chartData, isLoading: chartLoading } = useQuery({
    queryKey: ['dashboard-chart', days],
    queryFn: () => api.get(`/dashboard/chart?days=${days}`).then(r => r.data),
    refetchInterval: 60000,
  })

  const { data: funnel } = useQuery({
    queryKey: ['insights-funnel'],
    queryFn: () => api.get('/insights/funnel?days=30').then(r => r.data),
    refetchInterval: 60000,
  })

  const { data: forecast } = useQuery({
    queryKey: ['insights-forecast'],
    queryFn: () => api.get('/insights/stock-forecast').then(r => r.data),
    refetchInterval: 60000,
  })

  if (statsLoading) return (
    <div className="flex items-center justify-center py-20">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        <span className="text-gray-400 text-sm">{t('loading', lang)}</span>
      </div>
    </div>
  )

  const s = stats
  const daily = chartData?.daily || []
  const topProducts = chartData?.top_products || []
  const recentTx = chartData?.recent_transactions || []

  // Format day labels
  const formattedDaily = daily.map(d => ({
    ...d,
    label: d.day?.slice(5), // MM-DD
  }))

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('dash_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {lang === 'fa' ? 'خلاصه وضعیت فروشگاه' : 'Store overview'}
          </p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary py-2 px-3 relative">
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          <span className="absolute -top-1 -end-1 w-2 h-2 rounded-full" style={{ background: 'var(--success)', animation: 'pulse-glow 2s ease-in-out infinite' }} />
        </button>
      </div>

      {/* چیدمان داشبورد: نمایش/مخفی کردن بخش‌ها */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="text-xs text-gray-500">{lang === 'fa' ? 'چیدمان:' : 'Layout:'}</span>
        {[
          { key: 'stats', fa: 'آمار کلی', en: 'Stats' },
          { key: 'charts', fa: 'نمودارها', en: 'Charts' },
          { key: 'lists', fa: 'لیست‌ها', en: 'Lists' },
          { key: 'insights', fa: 'قیف و پیش‌بینی', en: 'Insights' },
        ].map((sec) => (
          <button
            key={sec.key}
            onClick={() => toggleSection(sec.key)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: show(sec.key) ? 'var(--primary-15, rgba(99,102,241,0.15))' : 'var(--surface-hover, rgba(255,255,255,0.04))',
              border: show(sec.key) ? '1px solid var(--primary-40, rgba(99,102,241,0.4))' : '1px solid var(--border-soft, rgba(255,255,255,0.08))',
              color: show(sec.key) ? 'var(--primary)' : 'var(--text-dim, #9ca3af)',
            }}
          >
            {lang === 'fa' ? sec.fa : sec.en}
          </button>
        ))}
      </div>

      {/* Main stats */}
      {show('stats') && (<>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          label={t('dash_users', lang)}
          value={s.users?.toLocaleString()}
          gradient="linear-gradient(135deg, #6366f1, #4f46e5)"
          iconColor="#6366f1"
          sub={`${s.blocked_users} ${t('dash_blocked', lang)}`}
        />
        <StatCard
          icon={ShoppingCart}
          label={t('dash_orders', lang)}
          value={s.orders?.toLocaleString()}
          gradient="linear-gradient(135deg, #10b981, #059669)"
          iconColor="#10b981"
          sub={`+${s.today_orders} ${t('dash_today', lang)}`}
        />
        <StatCard
          icon={TrendingUp}
          label={t('dash_revenue', lang)}
          value={`$${s.revenue?.toFixed(2)}`}
          gradient="linear-gradient(135deg, #8b5cf6, #7c3aed)"
          iconColor="#8b5cf6"
          sub={`+$${s.today_revenue?.toFixed(2)} ${t('dash_today', lang)}`}
        />
        <StatCard
          icon={DollarSign}
          label={t('dash_deposits', lang)}
          value={`$${s.deposits?.toFixed(2)}`}
          gradient="linear-gradient(135deg, #3b82f6, #2563eb)"
          iconColor="#3b82f6"
        />
      </div>

      {/* Secondary stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          icon={Ticket}
          label={t('dash_tickets', lang)}
          value={s.pending_tickets}
          gradient="linear-gradient(135deg, #f59e0b, #d97706)"
          iconColor="#f59e0b"
        />
        <StatCard
          icon={CreditCard}
          label={t('dash_pending_pay', lang)}
          value={s.pending_cards}
          gradient="linear-gradient(135deg, #ec4899, #db2777)"
          iconColor="#ec4899"
        />
        <StatCard
          icon={Shield}
          label={t('dash_warranty', lang)}
          value={s.pending_warranty}
          gradient="linear-gradient(135deg, #ef4444, #dc2626)"
          iconColor="#ef4444"
        />
      </div>

      </>)}

      {/* Charts row */}
      {show('charts') && (<>
      {!chartLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Orders area chart */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white text-sm">
                {lang === 'fa' ? 'روند سفارش‌ها' : 'Orders trend'}
              </h3>
              <div className="flex items-center gap-1">
                {[7, 30, 90].map(d => (
                  <button
                    key={d}
                    onClick={() => setDays(d)}
                    className="text-xs px-2 py-1 rounded-lg transition-all duration-150"
                    style={days === d ? {
                      background: 'var(--primary-20, rgba(99,102,241,0.20))',
                      color: 'var(--primary)',
                      border: '1px solid var(--primary-35, rgba(99,102,241,0.35))',
                    } : { color: '#6b7280', border: '1px solid transparent' }}
                  >
                    {t(`chart_${d}d`, lang)}
                  </button>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={formattedDaily}>
                <defs>
                  <linearGradient id="ordersGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="label" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip lang={lang} />} />
                <Area
                  type="monotone"
                  dataKey="orders"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fill="url(#ordersGrad)"
                  dot={{ fill: '#6366f1', r: 3 }}
                  activeDot={{ r: 5, fill: '#818cf8' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Revenue bar chart */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white text-sm">
                {lang === 'fa' ? `درآمد (دلار) — ${t(`chart_${days}d`, lang)}` : `Revenue ($) — ${t(`chart_${days}d`, lang)}`}
              </h3>
              <span className="badge-purple text-xs">{lang === 'fa' ? 'دلار' : 'USD'}</span>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={formattedDaily}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="label" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip lang={lang} />} />
                <Bar dataKey="revenue" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      </>)}

      {/* Bottom row */}
      {show('lists') && (<>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top products */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Package className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-white text-sm">
              {lang === 'fa' ? 'پرفروش‌ترین محصولات' : 'Top Products'}
            </h3>
          </div>
          {topProducts.length === 0 ? (
            <p className="text-gray-500 text-sm">{t('no_data', lang)}</p>
          ) : (
            <div className="space-y-3">
              {topProducts.map((p, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{
                      background: i === 0 ? 'rgba(245,158,11,0.2)' : i === 1 ? 'rgba(156,163,175,0.15)' : 'rgba(180,120,60,0.15)',
                      color: i === 0 ? '#f59e0b' : i === 1 ? '#9ca3af' : '#b47c3c',
                    }}
                  >
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200 truncate">{p.name}</p>
                    <p className="text-xs text-gray-500">{p.order_count} {lang === 'fa' ? 'سفارش' : 'orders'}</p>
                  </div>
                  <span className="text-sm font-semibold text-green-400">${p.revenue?.toFixed(0)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent transactions */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-4 h-4 text-blue-400" />
            <h3 className="font-semibold text-white text-sm">
              {lang === 'fa' ? 'آخرین واریزی‌ها' : 'Recent Deposits'}
            </h3>
          </div>
          {recentTx.length === 0 ? (
            <p className="text-gray-500 text-sm">{t('no_data', lang)}</p>
          ) : (
            <div className="space-y-3">
              {recentTx.map((tx, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{
                      background: tx.method === 'usdt' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                      border: `1px solid ${tx.method === 'usdt' ? 'rgba(16,185,129,0.25)' : 'rgba(245,158,11,0.25)'}`,
                    }}
                  >
                    <DollarSign
                      className="w-4 h-4"
                      style={{ color: tx.method === 'usdt' ? '#10b981' : '#f59e0b' }}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200">
                      @{tx.username || tx.user_id}
                    </p>
                    <p className="text-xs text-gray-500">{tx.created_at?.slice(0, 10)} · {tx.method?.toUpperCase()}</p>
                  </div>
                  <span className="text-sm font-bold text-green-400">+${tx.amount}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      </>)}

      {/* Funnel & stock forecast */}
      {show('insights') && (<>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h3 className="font-semibold text-white text-sm">
              {lang === 'fa' ? 'قیف فروش (۳۰ روز اخیر)' : 'Sales Funnel (last 30 days)'}
            </h3>
          </div>
          {!funnel ? (
            <p className="text-gray-500 text-sm">{t('no_data', lang)}</p>
          ) : (
            <div className="space-y-3">
              {[
                { key: 'start', label: lang === 'fa' ? 'ورود به ربات' : 'Bot starts', color: '#6366f1' },
                { key: 'view_product', label: lang === 'fa' ? 'مشاهده محصول' : 'Viewed product', color: '#8b5cf6' },
                { key: 'buy_click', label: lang === 'fa' ? 'کلیک روی خرید' : 'Buy clicked', color: '#f59e0b' },
                { key: 'purchase', label: lang === 'fa' ? 'خرید موفق' : 'Purchased', color: '#10b981' },
              ].map((st) => {
                const max = funnel.start || 1
                const val = funnel[st.key] || 0
                const pct = Math.round((val / max) * 100)
                return (
                  <div key={st.key}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-gray-300">{st.label}</span>
                      <span className="text-gray-400">{val} · {pct}%</span>
                    </div>
                    <div className="h-2.5 rounded-full w-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.max(pct, 2)}%`, background: st.color }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Package className="w-4 h-4 text-amber-400" />
            <h3 className="font-semibold text-white text-sm">
              {lang === 'fa' ? 'پیش‌بینی اتمام موجودی' : 'Stock Forecast'}
            </h3>
          </div>
          {(forecast?.forecast || []).length === 0 ? (
            <p className="text-gray-500 text-sm">{t('no_data', lang)}</p>
          ) : (
            <div className="space-y-3">
              {(forecast?.forecast || []).slice(0, 6).map((p) => (
                <div key={p.id} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200 truncate">{p.name}</p>
                    <p className="text-xs text-gray-500">
                      {lang === 'fa' ? `موجودی: ${p.stock} · فروش ۷ روز: ${p.sold_7d}` : `stock: ${p.stock} · sold 7d: ${p.sold_7d}`}
                    </p>
                  </div>
                  {p.days_left === null ? (
                    <span className="badge-purple text-xs">{lang === 'fa' ? 'بدون فروش اخیر' : 'no recent sales'}</span>
                  ) : (
                    <span className="text-xs font-bold px-2 py-1 rounded-lg" style={{
                      background: p.days_left <= 3 ? 'rgba(239,68,68,0.15)' : p.days_left <= 7 ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)',
                      color: p.days_left <= 3 ? '#ef4444' : p.days_left <= 7 ? '#f59e0b' : '#10b981',
                    }}>
                      {lang === 'fa' ? `~${p.days_left} روز` : `~${p.days_left}d`}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      </>)}
    </div>
  )
}
