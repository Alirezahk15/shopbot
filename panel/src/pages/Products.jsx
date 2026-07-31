import ImageUploader from '../components/ImageUploader.jsx'
import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'
import api from '../api/client.js'
import {
  Plus, Trash2, Package, ToggleLeft, ToggleRight, X, Shield,
  Search, Filter, Copy, BarChart2, DollarSign, Eye, EyeOff,
  Upload, List, ChevronLeft, ChevronRight, Edit, FolderPlus,
  TrendingUp, ShoppingCart, Percent, ArrowUpDown, Image
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area
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

// ── Stock Viewer Modal ──
function StockModal({ product, lang, onClose }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [page, setPage] = useState(0)
  const [stockItems, setStockItems] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [confirmModal, setConfirmModal] = useState(null)
  const fileInputRef = useRef()
  const limit = 20

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['stock', product.id, page],
    queryFn: () => api.get(`/products/${product.id}/stock?page=${page}&limit=${limit}`).then(r => r.data),
  })

  const addMutation = useMutation({
    mutationFn: (items) => api.post(`/products/${product.id}/stock`, { items }),
    onSuccess: (res) => {
      refetch()
      qc.invalidateQueries({ queryKey: ['products'] })
      setStockItems('')
      setShowAdd(false)
      toast(lang === 'fa' ? `${res.data.stock_count} آیتم در موجودی` : `Stock: ${res.data.stock_count} items`, 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const deleteItemMutation = useMutation({
    mutationFn: (itemId) => api.delete(`/products/${product.id}/stock/${itemId}`),
    onSuccess: () => { refetch(); qc.invalidateQueries({ queryKey: ['products'] }); toast(lang === 'fa' ? 'آیتم حذف شد' : 'Item deleted', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const clearAllMutation = useMutation({
    mutationFn: () => api.delete(`/products/${product.id}/stock`),
    onSuccess: (res) => {
      refetch()
      qc.invalidateQueries({ queryKey: ['products'] })
      toast(lang === 'fa' ? `${res.data.deleted} آیتم حذف شد` : `${res.data.deleted} items deleted`, 'warning')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const handleFileImport = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const content = ev.target.result
      const items = content.split('\n').map(l => l.trim()).filter(Boolean)
      api.post(`/products/${product.id}/stock/import-csv`, { items })
        .then(res => {
          refetch()
          qc.invalidateQueries({ queryKey: ['products'] })
          toast(lang === 'fa' ? `${res.data.added} آیتم اضافه شد` : `${res.data.added} items imported`, 'success')
        })
        .catch(() => toast(t('error', lang), 'error'))
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const items = data?.items || []
  const total = data?.total || 0

  return (
    <Modal title={`${lang === 'fa' ? 'موجودی' : 'Stock'}: ${product.name}`} onClose={onClose} maxWidth="max-w-2xl">
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}

      {/* Header stats */}
      <div className="flex items-center gap-3 mb-4">
        <div className="rounded-xl px-4 py-2 flex-1 text-center" style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
          <div className="text-xl font-bold text-green-400">{total}</div>
          <div className="text-xs text-gray-400">{lang === 'fa' ? 'موجود' : 'Available'}</div>
        </div>
        <div className="rounded-xl px-4 py-2 flex-1 text-center" style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}>
          <div className="text-xl font-bold text-indigo-400">{product.sold || 0}</div>
          <div className="text-xs text-gray-400">{lang === 'fa' ? 'فروخته شده' : 'Sold'}</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 mb-4">
        <button onClick={() => setShowAdd(!showAdd)} className="btn-primary flex-1">
          <Plus className="w-4 h-4" /> {lang === 'fa' ? 'افزودن' : 'Add'}
        </button>
        <button onClick={() => fileInputRef.current?.click()} className="btn-secondary flex-1">
          <Upload className="w-4 h-4" /> {lang === 'fa' ? 'Import CSV' : 'Import CSV'}
        </button>
        <input ref={fileInputRef} type="file" accept=".csv,.txt" className="hidden" onChange={handleFileImport} />
        {total > 0 && (
          <button
            onClick={() => setConfirmModal({
              title: lang === 'fa' ? 'پاک کردن موجودی' : 'Clear All Stock',
              message: lang === 'fa' ? `تمام ${total} آیتم موجودی حذف شود؟` : `Delete all ${total} stock items?`,
              type: 'danger',
              onConfirm: () => clearAllMutation.mutate(),
            })}
            className="btn-danger px-3"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Add stock textarea */}
      {showAdd && (
        <div className="mb-4 animate-slide-up">
          <label className="form-label">{lang === 'fa' ? 'هر آیتم در یک خط' : 'One item per line'}</label>
          <textarea
            value={stockItems}
            onChange={(e) => setStockItems(e.target.value)}
            className="input mb-2"
            rows={5}
            placeholder={lang === 'fa' ? 'آیتم ۱\nآیتم ۲\nآیتم ۳' : 'item1\nitem2\nitem3'}
            autoFocus
            dir="ltr"
          />
          <div className="flex gap-2">
            <button
              onClick={() => addMutation.mutate(stockItems.split('\n').filter(l => l.trim()))}
              disabled={!stockItems.trim() || addMutation.isPending}
              className="btn-success flex-1"
            >
              {addMutation.isPending ? t('loading', lang) : t('add', lang)}
            </button>
            <button onClick={() => setShowAdd(false)} className="btn-secondary flex-1">{t('cancel', lang)}</button>
          </div>
        </div>
      )}

      {/* Stock list */}
      {isLoading ? (
        <div className="flex justify-center py-6">
          <div className="w-6 h-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-8 text-gray-500 text-sm">{t('no_data', lang)}</div>
      ) : (
        <>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {items.map(item => (
              <div key={item.id} className="flex items-center gap-2 rounded-lg px-3 py-2" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                <span className="text-xs font-mono text-gray-300 flex-1 truncate">{item.content}</span>
                <button
                  onClick={() => setConfirmModal({
                    title: lang === 'fa' ? 'حذف آیتم' : 'Delete Item',
                    message: lang === 'fa' ? 'این آیتم از موجودی حذف شود؟' : 'Delete this stock item?',
                    type: 'danger',
                    onConfirm: () => deleteItemMutation.mutate(item.id),
                  })}
                  className="action-btn action-danger flex-shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
          {total > limit && (
            <div className="flex items-center justify-between mt-3">
              <span className="text-xs text-gray-500">{page * limit + 1}–{Math.min((page + 1) * limit, total)} / {total}</span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="btn-secondary py-1 px-2 disabled:opacity-30">
                  <ChevronLeft className="w-3.5 h-3.5 rtl-flip" />
                </button>
                <button onClick={() => setPage(p => p + 1)} disabled={(page + 1) * limit >= total} className="btn-secondary py-1 px-2 disabled:opacity-30">
                  <ChevronRight className="w-3.5 h-3.5 rtl-flip" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </Modal>
  )
}

// ── Product Form Modal (Add/Edit) ──
function ProductFormModal({ product, categories, lang, onClose, onSave }) {
  const [form, setForm] = useState({
    category_id: product?.category_id || categories[0]?.id || '',
    name: product?.name || '',
    price: product?.price || '',
    description: product?.description || '',
    features: product?.features || '',
    has_warranty: product?.has_warranty || 0,
    banner_url: product?.banner_url || '',
  })
  const [loading, setLoading] = useState(false)
  const [showBanner, setShowBanner] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await onSave({ ...form, category_id: parseInt(form.category_id), price: parseFloat(form.price), has_warranty: form.has_warranty ? 1 : 0 })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  const isEdit = !!product

  return (
    <Modal title={isEdit ? (lang === 'fa' ? 'ویرایش محصول' : 'Edit Product') : t('prod_add', lang)} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="form-label">{t('category', lang)}</label>
          <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })} className="input" required>
            <option value="">{lang === 'fa' ? 'انتخاب دسته...' : 'Select category...'}</option>
            {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="form-label">{t('name', lang)}</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input" required />
        </div>
        <div>
          <label className="form-label">{t('price', lang)} (USD)</label>
          <input type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="input" required dir="ltr" />
        </div>
        <div>
          <label className="form-label">{t('description', lang)}</label>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="input" rows={3} required />
        </div>
        <div>
          <label className="form-label">{t('features', lang)} ({lang === 'fa' ? 'اختیاری' : 'optional'})</label>
          <textarea value={form.features} onChange={(e) => setForm({ ...form, features: e.target.value })} className="input" rows={2} />
        </div>
        <div>
          <label className="form-label">{t('prod_banner', lang)} ({lang === 'fa' ? 'اختیاری' : 'optional'})</label>
          <ImageUploader
            value={form.banner_url}
            onChange={(v) => setForm({ ...form, banner_url: v })}
            lang={lang}
            placeholder="https://example.com/banner.jpg"
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setForm({ ...form, has_warranty: form.has_warranty ? 0 : 1 })}
            className={`toggle-switch ${form.has_warranty ? 'on' : ''}`}
          >
            <span className="toggle-knob" />
          </button>
          <span className="text-sm text-gray-300 flex items-center gap-1">
            <Shield className="w-4 h-4 text-green-400" /> {t('prod_has_warranty', lang)}
          </span>
        </div>
        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={loading} className="btn-primary flex-1">
            {loading ? t('loading', lang) : (isEdit ? t('save', lang) : t('add', lang))}
          </button>
          <button type="button" onClick={onClose} className="btn-secondary flex-1">{t('cancel', lang)}</button>
        </div>
      </form>
    </Modal>
  )
}

// ── Bulk Price Modal ──
function BulkPriceModal({ selectedIds, lang, onClose, onSave }) {
  const [op, setOp] = useState('increase_pct')
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)

  const ops = [
    { key: 'increase_pct', label: lang === 'fa' ? 'افزایش درصدی' : 'Increase %', icon: '📈' },
    { key: 'decrease_pct', label: lang === 'fa' ? 'کاهش درصدی' : 'Decrease %', icon: '📉' },
    { key: 'increase_abs', label: lang === 'fa' ? 'افزایش مقدار' : 'Increase $', icon: '➕' },
    { key: 'decrease_abs', label: lang === 'fa' ? 'کاهش مقدار' : 'Decrease $', icon: '➖' },
    { key: 'set', label: lang === 'fa' ? 'تنظیم قیمت' : 'Set Price', icon: '💲' },
  ]

  const handleSave = async () => {
    setLoading(true)
    try {
      await onSave({ product_ids: selectedIds, operation: op, value: parseFloat(value) })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title={lang === 'fa' ? `تغییر قیمت گروهی (${selectedIds.length} محصول)` : `Bulk Price Update (${selectedIds.length} products)`} onClose={onClose}>
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-2">
          {ops.map(o => (
            <button
              key={o.key}
              onClick={() => setOp(o.key)}
              className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all"
              style={{
                background: op === o.key ? 'rgba(99,102,241,0.15)' : 'var(--surface-hover, rgba(255,255,255,0.04))',
                border: `1px solid ${op === o.key ? 'rgba(99,102,241,0.4)' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
                color: op === o.key ? '#818cf8' : 'rgba(156,163,175,0.8)',
              }}
            >
              <span>{o.icon}</span>
              <span>{o.label}</span>
            </button>
          ))}
        </div>
        <div>
          <label className="form-label">{op.includes('pct') ? (lang === 'fa' ? 'درصد' : 'Percent (%)') : (lang === 'fa' ? 'مقدار ($)' : 'Amount ($)')}</label>
          <input
            type="number" dir="ltr" step="0.01" min="0"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="input"
            placeholder={op.includes('pct') ? '10' : '5.00'}
            autoFocus
            dir="ltr"
          />
        </div>
        <div className="flex gap-2">
          <button onClick={handleSave} disabled={!value || loading} className="btn-primary flex-1">
            {loading ? t('loading', lang) : t('save', lang)}
          </button>
          <button onClick={onClose} className="btn-secondary flex-1">{t('cancel', lang)}</button>
        </div>
      </div>
    </Modal>
  )
}

// ── Stats Modal ──
function StatsModal({ lang, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['product-stats'],
    queryFn: () => api.get('/products/stats').then(r => r.data),
  })

  return (
    <Modal title={lang === 'fa' ? 'آمار فروش محصولات' : 'Product Sales Stats'} onClose={onClose} maxWidth="max-w-2xl">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Daily sales chart */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {lang === 'fa' ? 'فروش ۱۴ روز اخیر' : 'Sales — Last 14 Days'}
            </h4>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={data?.daily_sales || []}>
                <defs>
                  <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-soft, rgba(255,255,255,0.05))" />
                <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v?.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface-strong, #1a1a2e)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px' }} />
                <Area type="monotone" dataKey="orders" stroke="#8b5cf6" strokeWidth={2} fill="url(#salesGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Top products */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {lang === 'fa' ? 'پرفروش‌ترین محصولات' : 'Top Products by Revenue'}
            </h4>
            <div className="space-y-2">
              {(data?.top_products || []).slice(0, 8).map((p, i) => (
                <div key={p.id} className="flex items-center gap-3">
                  <span className="text-xs font-bold w-5 text-center" style={{ color: i < 3 ? '#f59e0b' : '#6b7280' }}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-xs text-gray-300 truncate">{p.name}</span>
                      <span className="text-xs font-semibold text-green-400 ms-2">${p.revenue?.toFixed(0)}</span>
                    </div>
                    <div className="h-1.5 rounded-full" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.08))' }}>
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(100, (p.revenue / (data.top_products[0]?.revenue || 1)) * 100)}%`,
                          background: 'linear-gradient(90deg, #8b5cf6, #6366f1)',
                        }}
                      />
                    </div>
                  </div>
                  <span className="text-xs text-gray-500 flex-shrink-0">{p.sold} {lang === 'fa' ? 'فروش' : 'sold'}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Modal>
  )
}

// ── Category Manager Modal ──
function CategoryModal({ categories, lang, onClose }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [newName, setNewName] = useState('')
  const [editId, setEditId] = useState(null)
  const [editName, setEditName] = useState('')
  const [confirmModal, setConfirmModal] = useState(null)

  const addMutation = useMutation({
    mutationFn: (name) => api.post('/products/categories', { name }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['categories'] }); setNewName(''); toast(lang === 'fa' ? 'دسته اضافه شد' : 'Category added', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, name }) => api.put(`/products/categories/${id}`, { name }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['categories'] }); setEditId(null); toast(lang === 'fa' ? 'دسته بروزرسانی شد' : 'Category updated', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/products/categories/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['categories'] }); qc.invalidateQueries({ queryKey: ['products'] }); toast(lang === 'fa' ? 'دسته حذف شد' : 'Category deleted', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  return (
    <Modal title={lang === 'fa' ? 'مدیریت دسته‌بندی‌ها' : 'Category Management'} onClose={onClose}>
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}

      {/* Add new */}
      <div className="flex gap-2 mb-4">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={lang === 'fa' ? 'نام دسته جدید...' : 'New category name...'}
          className="input flex-1"
          onKeyDown={(e) => e.key === 'Enter' && newName.trim() && addMutation.mutate(newName.trim())}
        />
        <button
          onClick={() => newName.trim() && addMutation.mutate(newName.trim())}
          disabled={!newName.trim() || addMutation.isPending}
          className="btn-primary px-4"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* List */}
      <div className="space-y-2">
        {categories.map(c => (
          <div key={c.id} className="flex items-center gap-2 rounded-xl px-3 py-2" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
            {editId === c.id ? (
              <>
                <input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="input flex-1 py-1 text-sm"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && updateMutation.mutate({ id: c.id, name: editName })}
                />
                <button onClick={() => updateMutation.mutate({ id: c.id, name: editName })} className="btn-success py-1 px-2 text-xs">{t('save', lang)}</button>
                <button onClick={() => setEditId(null)} className="btn-secondary py-1 px-2 text-xs">{t('cancel', lang)}</button>
              </>
            ) : (
              <>
                <span className="text-sm text-gray-200 flex-1">{c.name}</span>
                <button onClick={() => { setEditId(c.id); setEditName(c.name) }} className="action-btn action-warning">
                  <Edit className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setConfirmModal({
                    title: lang === 'fa' ? 'حذف دسته' : 'Delete Category',
                    message: lang === 'fa' ? `دسته "${c.name}" و تمام محصولاتش حذف شود؟` : `Delete "${c.name}" and all its products?`,
                    type: 'danger',
                    onConfirm: () => deleteMutation.mutate(c.id),
                  })}
                  className="action-btn action-danger"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        ))}
      </div>
    </Modal>
  )
}

// ── Main Products Page ──
export default function Products() {
  const { lang } = useApp()
  const { toast } = useToast()
  const qc = useQueryClient()

  // Filters
  const [search, setSearch] = useState('')
  const [filterCat, setFilterCat] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [sortBy, setSortBy] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  // Selection for bulk operations
  const [selected, setSelected] = useState(new Set())

  // Modals
  const [showAddProduct, setShowAddProduct] = useState(false)
  const [editProduct, setEditProduct] = useState(null)
  const [stockProduct, setStockProduct] = useState(null)
  const [showStats, setShowStats] = useState(false)
  const [showCategories, setShowCategories] = useState(false)
  const [showBulkPrice, setShowBulkPrice] = useState(false)
  const [confirmModal, setConfirmModal] = useState(null)

  const { data: catData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => api.get('/products/categories').then(r => r.data),
  })

  const { data: prodData, isLoading } = useQuery({
    queryKey: ['products', search, filterCat, filterStatus, sortBy],
    queryFn: () => {
      const params = new URLSearchParams({
        ...(search && { search }),
        ...(filterCat && { category_id: filterCat }),
        ...(filterStatus && { status: filterStatus }),
        ...(sortBy && { sort: sortBy }),
      })
      return api.get(`/products?${params}`).then(r => r.data)
    },
  })

  const addProductMutation = useMutation({
    mutationFn: (body) => api.post('/products', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['products'] }); toast(lang === 'fa' ? 'محصول اضافه شد' : 'Product added', 'success') },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const updateProductMutation = useMutation({
    mutationFn: ({ pid, ...body }) => api.put(`/products/${pid}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['products'] }); toast(lang === 'fa' ? 'محصول بروزرسانی شد' : 'Product updated', 'success') },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const deleteProductMutation = useMutation({
    mutationFn: (pid) => api.delete(`/products/${pid}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['products'] }); toast(lang === 'fa' ? 'محصول حذف شد' : 'Product deleted', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const toggleMutation = useMutation({
    mutationFn: (pid) => api.post(`/products/${pid}/toggle`),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['products'] })
      toast(res.data.active ? (lang === 'fa' ? 'محصول فعال شد' : 'Product activated') : (lang === 'fa' ? 'محصول غیرفعال شد' : 'Product deactivated'), res.data.active ? 'success' : 'warning')
    },
  })

  const duplicateMutation = useMutation({
    mutationFn: (pid) => api.post(`/products/${pid}/duplicate`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['products'] }); toast(lang === 'fa' ? 'محصول کپی شد' : 'Product duplicated', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const bulkPriceMutation = useMutation({
    mutationFn: (body) => api.post('/products/bulk-price', body),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['products'] })
      setSelected(new Set())
      toast(lang === 'fa' ? `قیمت ${res.data.updated?.length} محصول بروزرسانی شد` : `${res.data.updated?.length} products updated`, 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids) => api.post('/products/bulk-delete', { product_ids: ids }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['products'] })
      setSelected(new Set())
      toast(lang === 'fa' ? `${res.data.count} محصول حذف شد` : `${res.data.count} products deleted`, 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const categories = catData?.categories || []
  const products = prodData?.products || []

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === products.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(products.map(p => p.id)))
    }
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('prod_title', lang)}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{products.length} {lang === 'fa' ? 'محصول' : 'products'}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => setShowStats(true)} className="btn-secondary py-2 px-3" title={lang === 'fa' ? 'آمار فروش' : 'Sales Stats'}>
            <BarChart2 className="w-4 h-4" />
          </button>
          <button onClick={() => setShowCategories(true)} className="btn-secondary py-2 px-3">
            <FolderPlus className="w-4 h-4" />
            <span className="text-xs">{lang === 'fa' ? 'دسته‌ها' : 'Categories'}</span>
          </button>
          {selected.size > 0 && (
            <button onClick={() => setShowBulkPrice(true)} className="btn-warning py-2 px-3">
              <Percent className="w-4 h-4" />
              <span className="text-xs">{selected.size}</span>
            </button>
          )}
          <button onClick={() => setShowFilters(!showFilters)} className={`btn-secondary py-2 px-3 ${showFilters ? 'text-indigo-400' : ''}`}>
            <Filter className="w-4 h-4" />
          </button>
          <button onClick={() => setShowAddProduct(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> {t('prod_add', lang)}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-3">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" style={{ insetInlineStart: '12px' }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={lang === 'fa' ? 'جستجو در محصولات...' : 'Search products...'}
            className="input"
            style={{ paddingInlineStart: '36px' }}
          />
        </div>
        {search && (
          <button onClick={() => setSearch('')} className="btn-secondary px-3">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="card mb-3 animate-slide-up" style={{ borderColor: 'rgba(99,102,241,0.2)' }}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="form-label">{t('category', lang)}</label>
              <select value={filterCat} onChange={(e) => setFilterCat(e.target.value)} className="input">
                <option value="">{lang === 'fa' ? 'همه دسته‌ها' : 'All Categories'}</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="form-label">{t('status', lang)}</label>
              <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="input">
                <option value="">{lang === 'fa' ? 'همه' : 'All'}</option>
                <option value="active">{t('active', lang)}</option>
                <option value="inactive">{t('inactive', lang)}</option>
              </select>
            </div>
            <div>
              <label className="form-label">{lang === 'fa' ? 'مرتب‌سازی' : 'Sort By'}</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="input">
                <option value="">{lang === 'fa' ? 'پیش‌فرض' : 'Default'}</option>
                <option value="price">{t('price', lang)}</option>
                <option value="sold">{lang === 'fa' ? 'بیشترین فروش' : 'Most Sold'}</option>
                <option value="stock">{lang === 'fa' ? 'بیشترین موجودی' : 'Most Stock'}</option>
                <option value="name">{t('name', lang)}</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {confirmModal && <ConfirmModal {...confirmModal} onClose={() => setConfirmModal(null)} />}
      {showAddProduct && (
        <ProductFormModal
          categories={categories}
          lang={lang}
          onClose={() => setShowAddProduct(false)}
          onSave={(body) => addProductMutation.mutateAsync(body)}
        />
      )}
      {editProduct && (
        <ProductFormModal
          product={editProduct}
          categories={categories}
          lang={lang}
          onClose={() => setEditProduct(null)}
          onSave={(body) => updateProductMutation.mutateAsync({ pid: editProduct.id, ...body })}
        />
      )}
      {stockProduct && <StockModal product={stockProduct} lang={lang} onClose={() => setStockProduct(null)} />}
      {showStats && <StatsModal lang={lang} onClose={() => setShowStats(false)} />}
      {showCategories && <CategoryModal categories={categories} lang={lang} onClose={() => { setShowCategories(false); qc.invalidateQueries({ queryKey: ['categories'] }) }} />}
      {showBulkPrice && (
        <BulkPriceModal
          selectedIds={[...selected]}
          lang={lang}
          onClose={() => setShowBulkPrice(false)}
          onSave={(body) => bulkPriceMutation.mutateAsync(body)}
        />
      )}

      {/* Products table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
        </div>
      ) : products.length === 0 ? (
        <div className="card text-center py-16">
          <Package className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-white font-semibold">{t('no_data', lang)}</p>
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-soft, rgba(255,255,255,0.06))', background: 'var(--surface-hover, rgba(255,255,255,0.02))' }}>
                  <th className="table-header w-8">
                    <input
                      type="checkbox"
                      checked={selected.size === products.length && products.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="table-header">{t('name', lang)}</th>
                  <th className="table-header">{t('category', lang)}</th>
                  <th className="table-header">{t('price', lang)}</th>
                  <th className="table-header">{t('stock', lang)}</th>
                  <th className="table-header">{t('sold', lang)}</th>
                  <th className="table-header">{t('status', lang)}</th>
                  <th className="table-header">{t('actions', lang)}</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className={`table-row ${selected.has(p.id) ? 'bg-indigo-900/10' : ''}`}>
                    <td className="table-cell">
                      <input
                        type="checkbox"
                        checked={selected.has(p.id)}
                        onChange={() => toggleSelect(p.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        {p.banner_url && (
                          <img src={p.banner_url} alt="" className="w-8 h-8 rounded-lg object-cover flex-shrink-0" onError={(e) => e.target.style.display = 'none'} />
                        )}
                        <div>
                          <div className="font-medium text-gray-200 text-sm">{p.name}</div>
                          {p.has_warranty ? <span className="text-xs text-green-400 flex items-center gap-0.5"><Shield className="w-3 h-3" />{lang === 'fa' ? 'گارانتی' : 'Warranty'}</span> : null}
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <span className="badge-gray text-xs">{p.category_name || '—'}</span>
                    </td>
                    <td className="table-cell font-semibold text-white">${p.price}</td>
                    <td className="table-cell">
                      <span className="font-bold" style={{ color: p.stock_count > 0 ? '#34d399' : '#f87171' }}>
                        {p.stock_count}
                      </span>
                    </td>
                    <td className="table-cell text-gray-400">{p.sold}</td>
                    <td className="table-cell">
                      {p.active ? <span className="badge-green">{t('active', lang)}</span> : <span className="badge-red">{t('inactive', lang)}</span>}
                    </td>
                    <td className="table-cell">
                      <div className="flex gap-1">
                        <button onClick={() => setStockProduct(p)} className="action-btn action-info" title={t('prod_add_stock', lang)}>
                          <List className="w-4 h-4" />
                        </button>
                        <button onClick={() => setEditProduct(p)} className="action-btn action-warning" title={t('edit', lang)}>
                          <Edit className="w-4 h-4" />
                        </button>
                        <button onClick={() => duplicateMutation.mutate(p.id)} className="action-btn action-view" title={lang === 'fa' ? 'کپی محصول' : 'Duplicate'}>
                          <Copy className="w-4 h-4" />
                        </button>
                        <button onClick={() => toggleMutation.mutate(p.id)} className="action-btn action-neutral" title={t('prod_toggle', lang)}>
                          {p.active ? <ToggleRight className="w-4 h-4 text-green-400" /> : <ToggleLeft className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => setConfirmModal({
                            title: lang === 'fa' ? 'حذف محصول' : 'Delete Product',
                            message: lang === 'fa' ? `محصول "${p.name}" و تمام موجودی آن حذف شود؟` : `Delete "${p.name}" and all its stock?`,
                            type: 'danger',
                            onConfirm: () => deleteProductMutation.mutate(p.id),
                          })}
                          className="action-btn action-danger"
                          title={t('delete', lang)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Bulk action bar */}
          {selected.size > 0 && (
            <div
              className="flex items-center justify-between px-4 py-3 animate-slide-up"
              style={{ borderTop: '1px solid rgba(99,102,241,0.2)', background: 'rgba(99,102,241,0.08)' }}
            >
              <span className="text-sm text-indigo-300">
                {selected.size} {lang === 'fa' ? 'محصول انتخاب شده' : 'products selected'}
              </span>
              <div className="flex gap-2">
                <button onClick={() => setShowBulkPrice(true)} className="btn-warning py-1.5 px-3 text-sm">
                  <Percent className="w-3.5 h-3.5" /> {lang === 'fa' ? 'تغییر قیمت' : 'Bulk Price'}
                </button>
                <button
                  onClick={() => setConfirmModal({
                    title: lang === 'fa' ? 'حذف گروهی' : 'Bulk Delete',
                    message: lang === 'fa'
                      ? `${selected.size} محصول انتخاب‌شده حذف شود؟ این عمل قابل بازگشت نیست.`
                      : `Delete ${selected.size} selected products? This cannot be undone.`,
                    type: 'danger',
                    confirmText: lang === 'fa' ? 'بله، همه را حذف کن' : 'Yes, delete all',
                    onConfirm: () => bulkDeleteMutation.mutate([...selected]),
                  })}
                  className="btn-danger py-1.5 px-3 text-sm"
                >
                  <Trash2 className="w-3.5 h-3.5" /> {lang === 'fa' ? 'حذف گروهی' : 'Bulk Delete'}
                </button>
                <button onClick={() => setSelected(new Set())} className="btn-secondary py-1.5 px-3 text-sm">
                  <X className="w-3.5 h-3.5" /> {t('cancel', lang)}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
