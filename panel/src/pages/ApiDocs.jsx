import { useState } from 'react'
import { useApp } from '../context/AppContext.jsx'
import { FileCode2, ChevronDown, Search } from 'lucide-react'

const METHOD_COLORS = {
  GET: { bg: 'rgba(16,185,129,0.15)', color: '#34d399', border: 'rgba(16,185,129,0.3)' },
  POST: { bg: 'rgba(99,102,241,0.15)', color: '#818cf8', border: 'rgba(99,102,241,0.3)' },
  PUT: { bg: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: 'rgba(245,158,11,0.3)' },
  DELETE: { bg: 'rgba(239,68,68,0.15)', color: '#f87171', border: 'rgba(239,68,68,0.3)' },
}

// Static endpoint reference — mirrors the FastAPI routers under api/routers/*.py
const API_GROUPS = [
  {
    key: 'dashboard', title: { fa: 'داشبورد', en: 'Dashboard' }, base: '/api/dashboard',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'آمار کلی: کاربران، سفارش، درآمد، تیکت‌ها', en: 'Aggregate stats: users, orders, revenue, tickets' } },
      { method: 'GET', path: '/chart?days=7|30|90', desc: { fa: 'داده نمودار سفارش/درآمد بر اساس بازه زمانی', en: 'Orders/revenue chart data for the given day range' } },
    ],
  },
  {
    key: 'users', title: { fa: 'کاربران', en: 'Users' }, base: '/api/users',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست کاربران', en: 'List users' } },
      { method: 'GET', path: '/stats', desc: { fa: 'آمار کاربران', en: 'User stats' } },
      { method: 'GET', path: '/export.csv', desc: { fa: 'خروجی CSV', en: 'CSV export' } },
      { method: 'GET', path: '/{uid}', desc: { fa: 'جزئیات یک کاربر', en: 'Single user detail' } },
      { method: 'POST', path: '/{uid}/balance', desc: { fa: 'تنظیم موجودی', en: 'Adjust balance' } },
      { method: 'POST', path: '/{uid}/block', desc: { fa: 'مسدود/رفع مسدودی', en: 'Block / unblock' } },
      { method: 'POST', path: '/{uid}/note', desc: { fa: 'افزودن یادداشت', en: 'Add admin note' } },
      { method: 'POST', path: '/{uid}/message', desc: { fa: 'ارسال مستقیم', en: 'Send direct message' } },
      { method: 'GET', path: '/search/{query}', desc: { fa: 'جستجوی کاربر', en: 'Search users' } },
    ],
  },
  {
    key: 'products', title: { fa: 'محصولات', en: 'Products' }, base: '/api/products',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست محصولات', en: 'List products' } },
      { method: 'GET', path: '/stats', desc: { fa: 'آمار محصولات', en: 'Product stats' } },
      { method: 'POST', path: '', desc: { fa: 'ایجاد محصول', en: 'Create product' } },
      { method: 'PUT', path: '/{id}', desc: { fa: 'ویرایش محصول', en: 'Update product' } },
      { method: 'DELETE', path: '/{id}', desc: { fa: 'حذف محصول', en: 'Delete product' } },
      { method: 'POST', path: '/{id}/duplicate', desc: { fa: 'کپی محصول', en: 'Duplicate product' } },
      { method: 'POST', path: '/{id}/toggle', desc: { fa: 'فعال/غیرفعال‌سازی', en: 'Toggle active status' } },
      { method: 'GET', path: '/{id}/stock', desc: { fa: 'موجودی محصول', en: 'Product stock' } },
      { method: 'POST', path: '/{id}/stock', desc: { fa: 'افزودن موجودی', en: 'Add stock' } },
      { method: 'GET', path: '/categories', desc: { fa: 'دسته‌بندی‌ها', en: 'Categories' } },
    ],
  },
  {
    key: 'orders', title: { fa: 'سفارش‌ها', en: 'Orders' }, base: '/api/orders',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست سفارش‌ها', en: 'List orders' } },
      { method: 'GET', path: '/stats', desc: { fa: 'آمار سفارش‌ها', en: 'Order stats' } },
      { method: 'GET', path: '/export.csv', desc: { fa: 'خروجی CSV', en: 'CSV export' } },
      { method: 'GET', path: '/{oid}', desc: { fa: 'جزئیات سفارش', en: 'Order detail' } },
      { method: 'POST', path: '/{oid}/resend', desc: { fa: 'ارسال مجدد محصول', en: 'Resend delivered content' } },
    ],
  },
  {
    key: 'payments', title: { fa: 'پرداخت‌ها', en: 'Payments' }, base: '/api/payments',
    endpoints: [
      { method: 'GET', path: '/pending', desc: { fa: 'پرداخت‌های معلق', en: 'Pending payments' } },
      { method: 'GET', path: '/all', desc: { fa: 'همه پرداخت‌ها', en: 'All payments' } },
      { method: 'GET', path: '/stats', desc: { fa: 'آمار پرداخت‌ها', en: 'Payment stats' } },
      { method: 'POST', path: '/{id}/approve', desc: { fa: 'تأیید پرداخت', en: 'Approve payment' } },
      { method: 'POST', path: '/{id}/reject', desc: { fa: 'رد پرداخت', en: 'Reject payment' } },
      { method: 'POST', path: '/bulk-action', desc: { fa: 'عملیات گروهی', en: 'Bulk approve/reject' } },
    ],
  },
  {
    key: 'tickets', title: { fa: 'تیکت‌ها', en: 'Tickets' }, base: '/api/tickets',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست تیکت‌ها', en: 'List tickets' } },
      { method: 'GET', path: '/{tid}', desc: { fa: 'جزئیات تیکت', en: 'Ticket detail' } },
      { method: 'POST', path: '/{tid}/reply', desc: { fa: 'ارسال پاسخ', en: 'Reply to ticket' } },
      { method: 'POST', path: '/{tid}/close', desc: { fa: 'بستن تیکت', en: 'Close ticket' } },
      { method: 'POST', path: '/{tid}/transfer', desc: { fa: 'انتقال به ادمین دیگر', en: 'Transfer to another admin' } },
      { method: 'GET', path: '/quick-replies', desc: { fa: 'پاسخ‌های سریع', en: 'Quick reply templates' } },
    ],
  },
  {
    key: 'discounts', title: { fa: 'کدهای تخفیف', en: 'Discounts' }, base: '/api/discounts',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست کدها', en: 'List codes' } },
      { method: 'POST', path: '', desc: { fa: 'ایجاد کد', en: 'Create code' } },
      { method: 'PUT', path: '/{code}', desc: { fa: 'ویرایش کد', en: 'Update code' } },
      { method: 'POST', path: '/{code}/toggle', desc: { fa: 'فعال/غیرفعال‌سازی', en: 'Toggle active' } },
      { method: 'DELETE', path: '/{code}', desc: { fa: 'حذف کد', en: 'Delete code' } },
    ],
  },
  {
    key: 'warranty', title: { fa: 'گارانتی', en: 'Warranty' }, base: '/api/warranty',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست درخواست‌ها', en: 'List claims' } },
      { method: 'GET', path: '/{claim_id}', desc: { fa: 'جزئیات درخواست', en: 'Claim detail' } },
      { method: 'POST', path: '/{claim_id}', desc: { fa: 'تأیید/رد درخواست', en: 'Approve / reject claim' } },
    ],
  },
  {
    key: 'lock', title: { fa: 'قفل کانال/گروه', en: 'Lock' }, base: '/api/lock',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست موارد قفل‌شده', en: 'List locked items' } },
      { method: 'POST', path: '/channel', desc: { fa: 'قفل کانال', en: 'Lock channel' } },
      { method: 'POST', path: '/group', desc: { fa: 'قفل گروه', en: 'Lock group' } },
      { method: 'DELETE', path: '/channel/{id}', desc: { fa: 'رفع قفل کانال', en: 'Unlock channel' } },
      { method: 'DELETE', path: '/group/{id}', desc: { fa: 'رفع قفل گروه', en: 'Unlock group' } },
    ],
  },
  {
    key: 'admins', title: { fa: 'ادمین‌ها', en: 'Admins' }, base: '/api/admins',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست ادمین‌ها', en: 'List admins' } },
      { method: 'GET', path: '/logs', desc: { fa: 'لاگ عملیات', en: 'Activity logs' } },
      { method: 'POST', path: '', desc: { fa: 'افزودن ادمین', en: 'Add admin' } },
      { method: 'PUT', path: '/{user_id}', desc: { fa: 'ویرایش دسترسی‌ها', en: 'Update permissions' } },
      { method: 'DELETE', path: '/{user_id}', desc: { fa: 'حذف ادمین', en: 'Remove admin' } },
    ],
  },
  {
    key: 'methods', title: { fa: 'روش‌های پرداخت', en: 'Payment Methods' }, base: '/api/methods',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'لیست روش‌ها', en: 'List methods' } },
      { method: 'POST', path: '', desc: { fa: 'ایجاد روش', en: 'Add method' } },
      { method: 'PUT', path: '/{id}', desc: { fa: 'ویرایش روش', en: 'Update method' } },
      { method: 'POST', path: '/reorder', desc: { fa: 'ترتیب مجدد', en: 'Reorder methods' } },
      { method: 'DELETE', path: '/{id}', desc: { fa: 'حذف روش', en: 'Delete method' } },
    ],
  },
  {
    key: 'broadcast', title: { fa: 'پیام همگانی', en: 'Broadcast' }, base: '/api/broadcast',
    endpoints: [
      { method: 'GET', path: '/history', desc: { fa: 'تاریخچه پیام‌ها', en: 'Broadcast history' } },
      { method: 'POST', path: '', desc: { fa: 'ارسال پیام همگانی', en: 'Send broadcast' } },
      { method: 'POST', path: '/{bid}/cancel', desc: { fa: 'لغو ارسال', en: 'Cancel broadcast' } },
      { method: 'GET', path: '/templates', desc: { fa: 'قالب‌ها', en: 'Templates' } },
    ],
  },
  {
    key: 'settings', title: { fa: 'تنظیمات', en: 'Settings' }, base: '/api/settings',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'دریافت تنظیمات', en: 'Get settings' } },
      { method: 'POST', path: '/feature', desc: { fa: 'فعال/غیرفعال یک قابلیت', en: 'Toggle a feature' } },
      { method: 'POST', path: '/card', desc: { fa: 'تنظیمات کارت', en: 'Card settings' } },
      { method: 'GET', path: '/system-info', desc: { fa: 'اطلاعات سیستم', en: 'System info' } },
      { method: 'GET', path: '/backup', desc: { fa: 'دریافت بکاپ', en: 'Get backup' } },
    ],
  },
  {
    key: 'buttons', title: { fa: 'چیدمان دکمه‌ها', en: 'Button Layout' }, base: '/api/buttons',
    endpoints: [
      { method: 'GET', path: '', desc: { fa: 'دریافت چیدمان فعلی', en: 'Get current layout' } },
      { method: 'POST', path: '/{menu_key}', desc: { fa: 'ذخیره چیدمان منو', en: 'Save menu layout' } },
      { method: 'POST', path: '/{menu_key}/reset', desc: { fa: 'بازنشانی به حالت پیش‌فرض', en: 'Reset to default' } },
    ],
  },
]

function Endpoint({ ep, base, lang }) {
  const mc = METHOD_COLORS[ep.method]
  return (
    <div className="flex items-start gap-3 py-2.5 px-1 border-b border-white/5 last:border-0">
      <span
        className="text-xs font-bold px-2 py-1 rounded-lg flex-shrink-0 w-16 text-center"
        style={{ background: mc.bg, color: mc.color, border: `1px solid ${mc.border}` }}
      >
        {ep.method}
      </span>
      <div className="min-w-0">
        <code className="text-xs text-gray-200 break-all">{base}{ep.path}</code>
        <p className="text-xs text-gray-500 mt-0.5">{ep.desc[lang] || ep.desc.en}</p>
      </div>
    </div>
  )
}

function GroupCard({ group, lang, index }) {
  const [open, setOpen] = useState(index === 0)
  return (
    <div className="card stagger-item" style={{ animationDelay: `${index * 0.04}s` }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <span className="badge-purple">{group.endpoints.length}</span>
          <h3 className="text-sm font-semibold text-white">{group.title[lang] || group.title.en}</h3>
          <code className="text-xs text-gray-500">{group.base}</code>
        </div>
        <ChevronDown className="w-4 h-4 text-gray-400 transition-transform duration-200" style={{ transform: open ? 'rotate(180deg)' : 'none' }} />
      </button>
      {open && (
        <div className="mt-3 accordion-content">
          {group.endpoints.map((ep, i) => (
            <Endpoint key={i} ep={ep} base={group.base} lang={lang} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function ApiDocs() {
  const { lang } = useApp()
  const [query, setQuery] = useState('')

  const filtered = API_GROUPS
    .map(g => ({
      ...g,
      endpoints: g.endpoints.filter(ep =>
        !query ||
        (g.base + ep.path).toLowerCase().includes(query.toLowerCase()) ||
        (ep.desc.fa + ep.desc.en).toLowerCase().includes(query.toLowerCase())
      ),
    }))
    .filter(g => g.endpoints.length > 0)

  return (
    <div className="page-enter">
      <div className="flex items-center gap-3 mb-6">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, var(--primary), var(--accent))', boxShadow: '0 4px 15px var(--primary-35, rgba(99,102,241,0.35))' }}
        >
          <FileCode2 className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="section-title mb-0">{lang === 'fa' ? 'مستندات API' : 'API Docs'}</h1>
          <p className="text-sm text-gray-400">
            {lang === 'fa' ? 'فهرست کامل مسیرهای بکند API پنل' : 'Full reference of the panel\'s backend API endpoints'}
          </p>
        </div>
      </div>

      <div className="relative mb-6">
        <Search className="w-4 h-4 text-gray-500 absolute top-1/2 -translate-y-1/2" style={{ insetInlineStart: '14px' }} />
        <input
          className="input"
          style={{ paddingInlineStart: '38px' }}
          placeholder={lang === 'fa' ? 'جستجو در مسیرها یا توضیحات...' : 'Search paths or descriptions...'}
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
      </div>

      <div className="space-y-3">
        {filtered.map((g, i) => (
          <GroupCard key={g.key} group={g} lang={lang} index={i} />
        ))}
        {filtered.length === 0 && (
          <p className="text-center text-gray-500 text-sm py-10">{lang === 'fa' ? 'نتیجه‌ای یافت نشد' : 'No results found'}</p>
        )}
      </div>
    </div>
  )
}
