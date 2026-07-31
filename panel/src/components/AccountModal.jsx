import { useState, useEffect } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import api from '../api/client.js'
import { useToast } from './Toast.jsx'
import {
  X, ShieldCheck, ShieldOff, KeyRound, Copy, Check,
  UserCircle2, Eye, EyeOff, AlertCircle, Smartphone,
} from 'lucide-react'

function ErrorNote({ children }) {
  if (!children) return null
  return (
    <div className="login-alert" style={{ padding: '10px 12px' }}>
      <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
      <span>{children}</span>
    </div>
  )
}

export default function AccountModal({ lang, onClose }) {
  const { toast } = useToast()
  const fa = lang === 'fa'

  const [me, setMe] = useState(null)
  // 'main' | 'setup2fa' | 'disable2fa' | 'changepass'
  const [view, setView] = useState('main')
  const [secret, setSecret] = useState('')
  const [otpUri, setOtpUri] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const [passForm, setPassForm] = useState({ current: '', next: '', confirm: '' })
  const [showPass, setShowPass] = useState(false)

  const loadMe = () => api.get('/auth/me').then((r) => setMe(r.data)).catch(() => {})
  useEffect(() => { loadMe() }, [])

  const apiError = (err, fallback) => {
    const detail = String(err.response?.data?.detail || '')
    if (fa) {
      if (detail.includes('Invalid verification code')) return 'کد تأیید نادرست است.'
      if (detail.includes('Current password')) return 'رمز فعلی اشتباه است.'
      if (detail.includes('at least 6')) return 'رمز عبور باید حداقل ۶ کاراکتر باشد.'
      if (detail.includes('No panel credentials')) return 'برای این حساب هنوز نام کاربری/رمز تعریف نشده است.'
      if (detail.includes('no admin ID')) return 'این نشست قدیمی است؛ یک بار خارج و با نام کاربری وارد شوید.'
      return fallback
    }
    return detail || fallback
  }

  // ── 2FA setup ──
  const start2fa = async () => {
    setError('')
    setBusy(true)
    try {
      const res = await api.post('/auth/totp/setup')
      setSecret(res.data.secret)
      setOtpUri(res.data.otpauth_uri)
      setCode('')
      setView('setup2fa')
    } catch (err) {
      setError(apiError(err, fa ? 'شروع فعال‌سازی ناموفق بود.' : 'Failed to start 2FA setup.'))
    } finally {
      setBusy(false)
    }
  }

  const confirm2fa = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.post('/auth/totp/enable', { code })
      toast(fa ? 'تأیید دومرحله‌ای فعال شد ✅' : '2FA enabled ✅', 'success')
      setView('main')
      loadMe()
    } catch (err) {
      setError(apiError(err, fa ? 'کد تأیید نادرست است.' : 'Invalid verification code.'))
    } finally {
      setBusy(false)
    }
  }

  const disable2fa = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.post('/auth/totp/disable', { code })
      toast(fa ? 'تأیید دومرحله‌ای غیرفعال شد' : '2FA disabled', 'success')
      setView('main')
      setCode('')
      loadMe()
    } catch (err) {
      setError(apiError(err, fa ? 'کد تأیید نادرست است.' : 'Invalid verification code.'))
    } finally {
      setBusy(false)
    }
  }

  // ── Change password ──
  const changePassword = async (e) => {
    e.preventDefault()
    if (passForm.next !== passForm.confirm) {
      setError(fa ? 'تکرار رمز عبور یکسان نیست.' : 'Passwords do not match.')
      return
    }
    setError('')
    setBusy(true)
    try {
      await api.post('/auth/change-password', {
        current_password: passForm.current,
        new_password: passForm.next,
      })
      toast(fa ? 'رمز عبور تغییر کرد' : 'Password changed', 'success')
      setPassForm({ current: '', next: '', confirm: '' })
      setView('main')
    } catch (err) {
      setError(apiError(err, fa ? 'تغییر رمز ناموفق بود.' : 'Failed to change password.'))
    } finally {
      setBusy(false)
    }
  }

  const copySecret = () => {
    navigator.clipboard?.writeText(secret)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const infoRow = (label, value) => (
    <div className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
      <span className="text-xs" style={{ color: 'var(--text-dim, #9ca3af)' }}>{label}</span>
      <span className="text-sm font-medium" style={{ color: 'var(--text-strong, #fff)' }}>{value}</span>
    </div>
  )

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)', animation: 'fadeIn 0.15s ease' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-md rounded-2xl p-6 max-h-[90vh] overflow-y-auto"
        style={{
          background: 'var(--surface-strong, #1a1a2e)',
          border: '1px solid var(--primary-25, rgba(99,102,241,0.25))',
          boxShadow: 'var(--shadow-modal, 0 25px 50px rgba(0,0,0,0.5))',
          animation: 'slideUp 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold flex items-center gap-2" style={{ color: 'var(--text-strong, #fff)' }}>
            <UserCircle2 className="w-5 h-5" style={{ color: 'var(--primary)' }} />
            {fa ? 'حساب کاربری و امنیت' : 'Account & Security'}
          </h3>
          <button onClick={onClose} className="action-btn action-neutral">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4">
          <ErrorNote>{error}</ErrorNote>

          {/* ── Main view ── */}
          {view === 'main' && (
            <>
              <div className="rounded-xl px-4 py-1" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.04))' }}>
                {infoRow(fa ? 'نام کاربری' : 'Username', me?.username || '—')}
                {infoRow(fa ? 'آیدی تلگرام' : 'Telegram ID', me?.user_id || '—')}
                {infoRow(fa ? 'نقش' : 'Role', me?.is_super ? (fa ? 'سوپر ادمین' : 'Super admin') : (fa ? 'ادمین' : 'Admin'))}
                <div className="flex items-center justify-between py-2">
                  <span className="text-xs" style={{ color: 'var(--text-dim, #9ca3af)' }}>
                    {fa ? 'تأیید دومرحله‌ای' : 'Two-factor auth'}
                  </span>
                  {me?.totp_enabled
                    ? <span className="badge-green">{fa ? 'فعال' : 'Enabled'}</span>
                    : <span className="badge-red">{fa ? 'غیرفعال' : 'Disabled'}</span>}
                </div>
              </div>

              <div className="space-y-2">
                {me?.totp_enabled ? (
                  <button onClick={() => { setCode(''); setError(''); setView('disable2fa') }} className="btn-secondary w-full">
                    <ShieldOff className="w-4 h-4" />
                    {fa ? 'غیرفعال‌سازی تأیید دومرحله‌ای' : 'Disable two-factor auth'}
                  </button>
                ) : (
                  <button onClick={start2fa} disabled={busy} className="btn-primary w-full">
                    <ShieldCheck className="w-4 h-4" />
                    {fa ? 'فعال‌سازی تأیید دومرحله‌ای (Google Authenticator)' : 'Enable 2FA (Google Authenticator)'}
                  </button>
                )}
                {me?.has_credentials && (
                  <button onClick={() => { setError(''); setView('changepass') }} className="btn-secondary w-full">
                    <KeyRound className="w-4 h-4" />
                    {fa ? 'تغییر رمز عبور' : 'Change password'}
                  </button>
                )}
              </div>

              {!me?.has_credentials && (
                <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-dim, #6b7280)' }}>
                  {fa
                    ? 'برای این حساب هنوز نام کاربری/رمز تعریف نشده. از بخش «ادمین‌ها ← اطلاعات ورود پنل» تعریف کنید.'
                    : 'No panel credentials set yet. Set them from Admins → Panel credentials.'}
                </p>
              )}
            </>
          )}

          {/* ── 2FA setup view ── */}
          {view === 'setup2fa' && (
            <form onSubmit={confirm2fa} className="space-y-4">
              <div className="flex items-start gap-2 text-xs leading-relaxed" style={{ color: 'var(--text-dim, #9ca3af)' }}>
                <Smartphone className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--primary)' }} />
                <span>
                  {fa
                    ? 'این QR را با Google Authenticator یا هر برنامه Authenticator دیگری اسکن کنید، سپس کد ۶ رقمی را وارد کنید.'
                    : 'Scan this QR with Google Authenticator (or similar), then enter the 6-digit code.'}
                </span>
              </div>

              <div className="flex justify-center">
                <div className="p-3 rounded-xl bg-white">
                  <QRCodeSVG value={otpUri} size={168} />
                </div>
              </div>

              <div>
                <label className="form-label">{fa ? 'یا کلید را دستی وارد کنید' : 'Or enter the key manually'}</label>
                <div className="flex items-center gap-2">
                  <code
                    className="flex-1 text-[11px] px-3 py-2 rounded-lg overflow-x-auto whitespace-nowrap"
                    style={{ background: 'var(--surface-hover, rgba(255,255,255,0.05))', color: 'var(--text-strong, #fff)', direction: 'ltr' }}
                  >
                    {secret}
                  </code>
                  <button type="button" onClick={copySecret} className="action-btn action-view" title={fa ? 'کپی' : 'Copy'}>
                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="form-label">{fa ? 'کد ۶ رقمی' : '6-digit code'}</label>
                <input
                  type="text"
                  inputMode="numeric"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="input code-input"
                  placeholder="••••••"
                  autoFocus
                />
              </div>

              <div className="flex gap-2">
                <button type="submit" disabled={busy || code.length !== 6} className="btn-primary flex-1">
                  <ShieldCheck className="w-4 h-4" />
                  {fa ? 'فعال‌سازی' : 'Enable'}
                </button>
                <button type="button" onClick={() => { setView('main'); setError('') }} className="btn-secondary flex-1">
                  {fa ? 'انصراف' : 'Cancel'}
                </button>
              </div>
            </form>
          )}

          {/* ── 2FA disable view ── */}
          {view === 'disable2fa' && (
            <form onSubmit={disable2fa} className="space-y-4">
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-dim, #9ca3af)' }}>
                {fa
                  ? 'برای غیرفعال‌سازی، کد فعلی برنامه Authenticator را وارد کنید.'
                  : 'Enter the current code from your authenticator app to disable 2FA.'}
              </p>
              <input
                type="text"
                inputMode="numeric"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="input code-input"
                placeholder="••••••"
                autoFocus
              />
              <div className="flex gap-2">
                <button type="submit" disabled={busy || code.length !== 6} className="btn-danger flex-1">
                  <ShieldOff className="w-4 h-4" />
                  {fa ? 'غیرفعال‌سازی' : 'Disable'}
                </button>
                <button type="button" onClick={() => { setView('main'); setError('') }} className="btn-secondary flex-1">
                  {fa ? 'انصراف' : 'Cancel'}
                </button>
              </div>
            </form>
          )}

          {/* ── Change password view ── */}
          {view === 'changepass' && (
            <form onSubmit={changePassword} className="space-y-4">
              <div>
                <label className="form-label">{fa ? 'رمز فعلی' : 'Current password'}</label>
                <input
                  type="password"
                  value={passForm.current}
                  onChange={(e) => setPassForm({ ...passForm, current: e.target.value })}
                  className="input"
                  required
                  dir="ltr"
                  autoFocus
                />
              </div>
              <div>
                <label className="form-label">{fa ? 'رمز جدید' : 'New password'}</label>
                <div className="relative">
                  <input
                    type={showPass ? 'text' : 'password'}
                    value={passForm.next}
                    onChange={(e) => setPassForm({ ...passForm, next: e.target.value })}
                    className="input"
                    style={{ paddingInlineEnd: '40px' }}
                    required
                    minLength={6}
                    dir="ltr"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-300"
                    style={{ insetInlineEnd: '12px' }}
                  >
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="form-label">{fa ? 'تکرار رمز جدید' : 'Confirm new password'}</label>
                <input
                  type="password"
                  value={passForm.confirm}
                  onChange={(e) => setPassForm({ ...passForm, confirm: e.target.value })}
                  className="input"
                  required
                  minLength={6}
                  dir="ltr"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" disabled={busy} className="btn-primary flex-1">
                  <KeyRound className="w-4 h-4" />
                  {fa ? 'تغییر رمز' : 'Change'}
                </button>
                <button type="button" onClick={() => { setView('main'); setError('') }} className="btn-secondary flex-1">
                  {fa ? 'انصراف' : 'Cancel'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
