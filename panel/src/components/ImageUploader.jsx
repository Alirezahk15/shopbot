import { useState, useCallback, useId } from 'react'
import api from '../api/client.js'
import { Upload, X, Image as ImageIcon, Link2, Loader2, AlertCircle } from 'lucide-react'

/**
 * ImageUploader - فیلد آپلود تصویر امن
 *
 * از label/htmlFor استفاده می‌کند (نه inputRef.click) تا:
 *   - داخل <form> باعث submit نشود
 *   - با همه مرورگرها سازگار باشد
 *   - drag & drop نیز پشتیبانی شود
 *
 * Props:
 *   value      string    URL یا Telegram file_id
 *   onChange   fn(str)   کال‌بک با مقدار جدید
 *   lang       'fa'|'en'
 *   placeholder string
 *   maxSizeMB  number    (default: 5)
 *   disabled   bool
 */
export default function ImageUploader({
  value = '',
  onChange,
  lang = 'fa',
  placeholder = '',
  maxSizeMB = 5,
  disabled = false,
}) {
  const inputId  = useId()
  const [tab,       setTab]      = useState('url')
  const [uploading, setUploading]= useState(false)
  const [progress,  setProgress] = useState(0)
  const [error,     setError]    = useState('')
  const [dragOver,  setDragOver] = useState(false)

  // آیا مقدار یک Telegram file_id است (نه URL)
  const isTgId     = Boolean(value && !value.startsWith('http') && value.length > 30)
  const previewSrc = isTgId ? `/api/tg-file/${value}` : value

  // ── آپلود فایل ──────────────────────────────────────────────────────────
  const doUpload = useCallback(async (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError(lang === 'fa' ? 'فقط فایل تصویری مجاز است (JPG، PNG، WebP)' : 'Only images are allowed (JPG, PNG, WebP)')
      return
    }
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(lang === 'fa' ? `حداکثر حجم ${maxSizeMB}MB است` : `Max size is ${maxSizeMB}MB`)
      return
    }
    setError('')
    setUploading(true)
    setProgress(10)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post('/upload-media', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (ev) => {
          if (ev.total) setProgress(Math.round((ev.loaded / ev.total) * 85))
        },
      })
      setProgress(100)
      onChange(res.data.file_id)
      setTab('url')
    } catch (err) {
      setError(err?.response?.data?.detail || (lang === 'fa' ? 'آپلود ناموفق بود' : 'Upload failed'))
    } finally {
      setUploading(false)
      setTimeout(() => setProgress(0), 700)
    }
  }, [lang, maxSizeMB, onChange])

  const onFileInputChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      e.target.value = ''   // reset برای انتخاب مجدد همان فایل
      doUpload(file)
    }
  }

  // drag & drop handlers
  const onDragOver  = (e) => { e.preventDefault(); e.stopPropagation(); setDragOver(true)  }
  const onDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setDragOver(false) }
  const onDrop      = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) doUpload(file)
  }

  // حذف تصویر - stopPropagation برای جلوگیری از submit فرم
  const handleClear = (e) => {
    e.preventDefault()
    e.stopPropagation()
    onChange('')
    setError('')
  }

  // تغییر tab - stopPropagation برای جلوگیری از submit فرم
  const handleTabChange = (e, id) => {
    e.preventDefault()
    e.stopPropagation()
    setTab(id)
    setError('')
  }

  // ── حالت آپلود در جریان ─────────────────────────────────────────────────
  if (uploading) {
    return (
      <div
        className="rounded-xl p-4 flex flex-col items-center gap-2.5"
        style={{
          border: '1px dashed var(--primary-40, rgba(99,102,241,0.4))',
          background: 'var(--primary-15, rgba(99,102,241,0.06))',
        }}
      >
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--primary)' }} />
        <p className="text-xs text-gray-400">
          {lang === 'fa' ? 'در حال آپلود به تلگرام...' : 'Uploading to Telegram...'}
        </p>
        {progress > 0 && (
          <div
            className="w-full rounded-full h-1 overflow-hidden"
            style={{ background: 'rgba(255,255,255,0.08)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{ width: `${progress}%`, background: 'var(--primary)' }}
            />
          </div>
        )}
        <p className="text-[10px] text-gray-600">{progress}%</p>
      </div>
    )
  }

  // ── پیش‌نمایش (وقتی مقدار دارد) ─────────────────────────────────────────
  if (value) {
    return (
      <div className="space-y-1.5">
        {/* تصویر + hover overlay */}
        <div
          className="relative inline-flex group rounded-xl overflow-hidden"
          style={{
            border: '1px solid var(--border-soft, rgba(255,255,255,0.1))',
            background: 'var(--surface-hover, rgba(255,255,255,0.03))',
          }}
        >
          <img
            src={previewSrc}
            alt=""
            className="block object-contain"
            style={{ maxHeight: '120px', minWidth: '80px', minHeight: '60px', width: 'auto' }}
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
          {/* overlay */}
          <div
            className="absolute inset-0 flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-150"
            style={{ background: 'rgba(0,0,0,0.6)' }}
          >
            {/* label برای تغییر — هرگز submit نمی‌کند */}
            <label
              htmlFor={`${inputId}-preview`}
              className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-white cursor-pointer select-none"
              style={{ background: 'var(--primary)' }}
              onClick={(e) => e.stopPropagation()}
            >
              <Upload className="w-3.5 h-3.5" />
              {lang === 'fa' ? 'تغییر' : 'Change'}
            </label>
            <button
              type="button"
              onClick={handleClear}
              disabled={disabled}
              className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-white"
              style={{ background: 'rgba(239,68,68,0.85)' }}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* نمایش مقدار */}
        <p className="text-[10px] text-gray-600 truncate max-w-xs font-mono" dir="ltr">
          {isTgId ? 'Telegram file_id ✓' : value.slice(0, 60)}
        </p>

        {/* input مخفی برای تغییر */}
        <input
          id={`${inputId}-preview`}
          type="file"
          accept="image/*"
          className="sr-only"
          onChange={onFileInputChange}
          disabled={disabled}
        />
      </div>
    )
  }

  // ── حالت خالی ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-2">

      {/* Tab switcher */}
      <div
        className="inline-flex rounded-lg overflow-hidden"
        style={{ border: '1px solid var(--border-soft, rgba(255,255,255,0.08))' }}
      >
        {[
          { id: 'url',    Icon: Link2,  fa: 'آدرس URL',   en: 'URL'    },
          { id: 'upload', Icon: Upload, fa: 'آپلود فایل',  en: 'Upload' },
        ].map(({ id, Icon, fa, en }) => {
          const active = tab === id
          return (
            <button
              key={id}
              type="button"
              onClick={(e) => handleTabChange(e, id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all duration-150"
              style={{
                background: active ? 'var(--primary)' : 'transparent',
                color: active ? '#fff' : 'var(--text-dim, #9ca3af)',
              }}
            >
              <Icon className="w-3 h-3" />
              {lang === 'fa' ? fa : en}
            </button>
          )
        })}
      </div>

      {/* URL input */}
      {tab === 'url' && (
        <input
          type="text"
          className="input w-full"
          dir="ltr"
          value={value}
          onChange={(e) => { onChange(e.target.value); setError('') }}
          placeholder={placeholder || 'https://example.com/image.jpg'}
          disabled={disabled}
        />
      )}

      {/* Drop zone — label/htmlFor بدون هیچ onClick JS */}
      {tab === 'upload' && (
        <label
          htmlFor={inputId}
          className="block rounded-xl transition-all duration-150 cursor-pointer"
          style={{
            border: `2px dashed ${dragOver ? 'var(--primary)' : 'var(--border-soft, rgba(255,255,255,0.12))'}`,
            background: dragOver
              ? 'var(--primary-15, rgba(99,102,241,0.08))'
              : 'var(--surface-hover, rgba(255,255,255,0.03))',
          }}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex flex-col items-center gap-2.5 py-8 px-4 select-none pointer-events-none">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'var(--primary-15, rgba(99,102,241,0.15))' }}
            >
              <ImageIcon className="w-5 h-5" style={{ color: 'var(--primary)' }} />
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-300 font-medium">
                {lang === 'fa' ? 'کلیک کنید یا تصویر را اینجا بکشید' : 'Click or drag & drop an image'}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {lang === 'fa'
                  ? `JPG، PNG، WebP — حداکثر ${maxSizeMB}MB`
                  : `JPG, PNG, WebP — max ${maxSizeMB}MB`}
              </p>
            </div>
            <span
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium"
              style={{ background: 'var(--primary)', color: '#fff' }}
            >
              <Upload className="w-3.5 h-3.5" />
              {lang === 'fa' ? 'انتخاب فایل' : 'Browse file'}
            </span>
          </div>
        </label>
      )}

      {/* خطا */}
      {error && (
        <div
          className="flex items-center gap-1.5 text-xs rounded-lg px-2.5 py-1.5"
          style={{
            color: '#f87171',
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.2)',
          }}
        >
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* input مخفی — sr-only نه hidden تا مرورگر آن را کاملاً نادیده نگیرد */}
      <input
        id={inputId}
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={onFileInputChange}
        disabled={disabled}
      />
    </div>
  )
}