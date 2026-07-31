import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import api from '../api/client.js'
import { setAdminInfo } from '../auth.js'
import {
  Bot, Lock, User, Eye, EyeOff, Languages, AlertCircle, CheckCircle2,
  ShieldCheck, KeyRound, ArrowLeft, ArrowRight, Hash, Send,
} from 'lucide-react'

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

export default function Login() {
  const navigate = useNavigate()
  const { lang, toggleLang } = useApp()
  const fa = lang === 'fa'
  const Back = fa ? ArrowRight : ArrowLeft

  // 'login' | 'totp' | 'forgot' | 'reset'
  const [step, setStep] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [ticket, setTicket] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [resetId, setResetId] = useState('')
  const [resetCode, setResetCode] = useState('')
  const [newPass, setNewPass] = useState('')
  const [confirmPass, setConfirmPass] = useState('')
  const [showNewPass, setShowNewPass] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [shakeKey, setShakeKey] = useState(0)

  const fail = (msg) => {
    setNotice('')
    setError(msg)
    setShakeKey((k) => k + 1)
  }

  const apiError = (err, fallbackFa, fallbackEn) => {
    const status = err.response?.status
    const detail = String(err.response?.data?.detail || '')
    if (status === 429) {
      return fa
        ? 'تلاش بیش از حد مجاز! چند دقیقه بعد دوباره امتحان کنید.'
        : 'Too many attempts. Try again in a few minutes.'
    }
    if (fa) {
      if (detail.includes('account has expired')) return 'این حساب ادمین منقضی شده است.'
      if (detail.includes('Invalid or expired code')) return 'کد نامعتبر یا منقضی شده است.'
      if (detail.includes('at least 6')) return 'رمز عبور باید حداقل ۶ کاراکتر باشد.'
      return fallbackFa
    }
    return detail || fallbackEn
  }

  const finishLogin = (data) => {
    localStorage.setItem('token', data.token)
    setAdminInfo(data.admin || null)
    navigate('/')
  }

  // ── Step 1: username + password ──
  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/login', { username: username.trim() || null, password })
      if (res.data.totp_required) {
        setTicket(res.data.ticket)
        setTotpCode('')
        setNotice('')
        setStep('totp')
      } else {
        finishLogin(res.data)
      }
    } catch (err) {
      fail(apiError(err,
        'نام کاربری یا رمز عبور اشتباه است.',
        'Invalid username or password.'))
    } finally {
      setLoading(false)
    }
  }

  // ── Step 2: two-factor code ──
  const handleTotp = async (codeArg) => {
    const code = typeof codeArg === 'string' ? codeArg : totpCode
    if (loading || code.length !== 6) return
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/totp-verify', { ticket, code })
      finishLogin(res.data)
    } catch (err) {
      setTotpCode('')
      if (err.response?.status === 401 && String(err.response?.data?.detail || '').includes('ticket')) {
        setStep('login')
        fail(fa ? 'مهلت ورود تمام شد؛ دوباره وارد شوید.' : 'Session expired. Log in again.')
      } else {
        fail(apiError(err, 'کد تأیید نادرست است.', 'Invalid verification code.'))
      }
    } finally {
      setLoading(false)
    }
  }

  // ── Forgot password: send code via bot ──
  const handleForgot = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/forgot', { user_id: Number(resetId) })
      setNotice(fa
        ? 'اگر این آیدی ادمین باشد، کد تأیید در ربات برایتان ارسال شد. کد تا ۱۰ دقیقه معتبر است.'
        : 'If this ID belongs to an admin, a code was sent in the bot. It is valid for 10 minutes.')
      setError('')
      setStep('reset')
    } catch (err) {
      fail(apiError(err, 'ارسال کد ناموفق بود.', 'Failed to send the code.'))
    } finally {
      setLoading(false)
    }
  }

  // ── Reset password with the bot code ──
  const handleReset = async (e) => {
    e.preventDefault()
    if (newPass !== confirmPass) {
      fail(fa ? 'تکرار رمز عبور یکسان نیست.' : 'Passwords do not match.')
      return
    }
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/reset-password', {
        user_id: Number(resetId),
        code: resetCode.trim(),
        new_password: newPass,
      })
      setStep('login')
      setPassword('')
      setResetCode('')
      setNewPass('')
      setConfirmPass('')
      setError('')
      setNotice(fa ? 'رمز عبور با موفقیت تغییر کرد. حالا وارد شوید.' : 'Password changed successfully. You can log in now.')
    } catch (err) {
      fail(apiError(err, 'کد نامعتبر یا منقضی شده است.', 'Invalid or expired code.'))
    } finally {
      setLoading(false)
    }
  }

  const goBackToLogin = () => {
    setStep('login')
    setError('')
    setNotice('')
    setTotpCode('')
  }

  const stepMeta = {
    login: {
      icon: Bot,
      title: fa ? 'ورود به پنل مدیریت' : 'Sign in to Admin Panel',
      sub: fa ? 'با نام کاربری و رمز عبور خود وارد شوید' : 'Enter your username and password',
    },
    totp: {
      icon: ShieldCheck,
      title: fa ? 'تأیید دومرحله‌ای' : 'Two-Factor Verification',
      sub: fa ? 'کد ۶ رقمی برنامه Authenticator را وارد کنید' : 'Enter the 6-digit code from your authenticator app',
    },
    forgot: {
      icon: KeyRound,
      title: fa ? 'بازیابی رمز عبور' : 'Reset Password',
      sub: fa ? 'آیدی عددی تلگرام خود را وارد کنید تا کد تأیید در ربات برایتان ارسال شود' : 'Enter your Telegram numeric ID to receive a code in the bot',
    },
    reset: {
      icon: KeyRound,
      title: fa ? 'تغییر رمز عبور' : 'Set New Password',
      sub: fa ? 'کد دریافتی از ربات و رمز جدید را وارد کنید' : 'Enter the code from the bot and your new password',
    },
  }
  const meta = stepMeta[step]
  const MetaIcon = meta.icon

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden login-page"
    >
      {/* Background glow effects */}
      <div
        className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full pointer-events-none login-glow"
        style={{
          background: 'radial-gradient(circle, var(--primary-20, rgba(99,102,241,0.18)) 0%, transparent 70%)',
          filter: 'blur(40px)',
        }}
      />
      <div
        className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full pointer-events-none login-glow"
        style={{
          background: 'radial-gradient(circle, var(--primary-15, rgba(139,92,246,0.12)) 0%, transparent 70%)',
          filter: 'blur(40px)',
        }}
      />
      {/* Subtle grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(var(--primary-10, rgba(99,102,241,0.05)) 1px, transparent 1px), linear-gradient(90deg, var(--primary-10, rgba(99,102,241,0.05)) 1px, transparent 1px)',
          backgroundSize: '44px 44px',
          maskImage: 'radial-gradient(ellipse at center, black 30%, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse at center, black 30%, transparent 75%)',
        }}
      />

      {/* Language toggle */}
      <button
        onClick={toggleLang}
        className="absolute top-4 end-4 btn-secondary py-1.5 px-3 text-xs"
      >
        <Languages className="w-3.5 h-3.5" />
        {fa ? 'EN' : 'FA'}
      </button>

      {/* Card */}
      <div
        className="w-full max-w-sm animate-slide-up relative login-card"
      >
        {/* Top gradient hairline */}
        <div
          className="absolute top-0 inset-x-0 h-px"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(139,92,246,0.8), rgba(99,102,241,0.8), transparent)' }}
        />

        {/* Header */}
        <div className="flex flex-col items-center mb-6">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
            style={{
              background: 'linear-gradient(135deg, var(--primary, #6366f1), var(--accent, #8b5cf6))',
              boxShadow: '0 8px 25px var(--primary-50, rgba(99,102,241,0.5))',
            }}
          >
            <MetaIcon className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text-strong, #ffffff)' }}>{meta.title}</h1>
          <p className="text-xs mt-1.5 text-center" style={{ color: 'var(--text-dim, rgba(148,163,184,0.9))' }}>
            {meta.sub}
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <div key={shakeKey} className="login-alert mb-4">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
        {notice && !error && (
          <div className="login-alert success mb-4">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{notice}</span>
          </div>
        )}

        {/* ── Login form ── */}
        {step === 'login' && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="form-label">{fa ? 'نام کاربری' : 'Username'}</label>
              <div className="relative">
                <User className="w-4 h-4 absolute top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" style={{ insetInlineStart: '12px' }} />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input"
                  style={{ paddingInlineStart: '38px' }}
                  placeholder={fa ? 'نام کاربری شما' : 'your username'}
                  autoFocus
                  dir="ltr"
                />
              </div>
            </div>
            <div>
              <label className="form-label">{fa ? 'رمز عبور' : 'Password'}</label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" style={{ insetInlineStart: '12px' }} />
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  style={{ paddingInlineStart: '38px', paddingInlineEnd: '44px' }}
                  placeholder="••••••••"
                  required
                  dir="ltr"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute top-1/2 -translate-y-1/2 p-1 login-ghost-link transition-colors"
                  style={{ insetInlineEnd: '12px' }}
                >
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full py-3 text-base mt-2">
              {loading ? (
                <span className="flex items-center gap-2">
                  <Spinner />
                  {fa ? 'در حال ورود...' : 'Signing in...'}
                </span>
              ) : (fa ? 'ورود' : 'Sign in')}
            </button>

            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={() => { setStep('forgot'); setError(''); setNotice('') }}
                className="text-xs transition-colors"
                style={{ color: 'var(--primary, rgba(129,140,248,0.9))' }}
              >
                {fa ? 'رمز عبور را فراموش کرده‌اید؟' : 'Forgot password?'}
              </button>
            </div>

            <p className="text-[10px] leading-relaxed text-center pt-1" style={{ color: 'var(--text-dim, rgba(107,114,128,0.8))' }}>
              {fa
                ? 'اگر هنوز نام کاربری تعریف نشده، فقط رمز اولیه پنل را وارد کنید و نام کاربری را خالی بگذارید.'
                : 'First time? Leave username empty and use the initial panel password.'}
            </p>
          </form>
        )}

        {/* ── 2FA form ── */}
        {step === 'totp' && (
          <form onSubmit={(e) => { e.preventDefault(); handleTotp() }} className="space-y-4">
            <div>
              <label className="form-label">{fa ? 'کد تأیید ۶ رقمی' : '6-digit code'}</label>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={totpCode}
                onChange={(e) => {
                  const v = e.target.value.replace(/\D/g, '').slice(0, 6)
                  setTotpCode(v)
                  if (v.length === 6) handleTotp(v)
                }}
                className="input code-input"
                placeholder="••••••"
                autoFocus
              />
            </div>
            <button type="submit" disabled={loading || totpCode.length !== 6} className="btn-primary w-full py-3 text-base">
              {loading ? (
                <span className="flex items-center gap-2">
                  <Spinner />
                  {fa ? 'در حال بررسی...' : 'Verifying...'}
                </span>
              ) : (fa ? 'تأیید و ورود' : 'Verify & sign in')}
            </button>
            <button type="button" onClick={goBackToLogin} className="w-full flex items-center justify-center gap-1.5 text-xs login-ghost-link transition-colors">
              <Back className="w-3.5 h-3.5" />
              {fa ? 'بازگشت به ورود' : 'Back to sign in'}
            </button>
          </form>
        )}

        {/* ── Forgot form ── */}
        {step === 'forgot' && (
          <form onSubmit={handleForgot} className="space-y-4">
            <div>
              <label className="form-label">{fa ? 'آیدی عددی تلگرام' : 'Telegram numeric ID'}</label>
              <div className="relative">
                <Hash className="w-4 h-4 absolute top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" style={{ insetInlineStart: '12px' }} />
                <input
                  type="text"
                  inputMode="numeric"
                  value={resetId}
                  onChange={(e) => setResetId(e.target.value.replace(/\D/g, ''))}
                  className="input"
                  style={{ paddingInlineStart: '38px' }}
                  placeholder="123456789"
                  required
                  autoFocus
                  dir="ltr"
                />
              </div>
              <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-dim, rgba(107,114,128,0.9))' }}>
                {fa ? 'می‌توانید آیدی خود را از ربات‌هایی مثل @userinfobot بگیرید.' : 'You can get your ID from bots like @userinfobot.'}
              </p>
            </div>
            <button type="submit" disabled={loading || !resetId} className="btn-primary w-full py-3 text-base">
              {loading ? (
                <span className="flex items-center gap-2">
                  <Spinner />
                  {fa ? 'در حال ارسال...' : 'Sending...'}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Send className="w-4 h-4" />
                  {fa ? 'ارسال کد به ربات' : 'Send code to bot'}
                </span>
              )}
            </button>
            <button type="button" onClick={goBackToLogin} className="w-full flex items-center justify-center gap-1.5 text-xs login-ghost-link transition-colors">
              <Back className="w-3.5 h-3.5" />
              {fa ? 'بازگشت به ورود' : 'Back to sign in'}
            </button>
          </form>
        )}

        {/* ── Reset form ── */}
        {step === 'reset' && (
          <form onSubmit={handleReset} className="space-y-4">
            <div>
              <label className="form-label">{fa ? 'کد تأیید دریافتی از ربات' : 'Code from the bot'}</label>
              <input
                type="text"
                inputMode="numeric"
                value={resetCode}
                onChange={(e) => setResetCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="input code-input"
                placeholder="••••••"
                required
                autoFocus
              />
            </div>
            <div>
              <label className="form-label">{fa ? 'رمز عبور جدید' : 'New password'}</label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" style={{ insetInlineStart: '12px' }} />
                <input
                  type={showNewPass ? 'text' : 'password'}
                  value={newPass}
                  onChange={(e) => setNewPass(e.target.value)}
                  className="input"
                  style={{ paddingInlineStart: '38px', paddingInlineEnd: '44px' }}
                  required
                  minLength={6}
                  dir="ltr"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPass(!showNewPass)}
                  className="absolute top-1/2 -translate-y-1/2 p-1 login-ghost-link transition-colors"
                  style={{ insetInlineEnd: '12px' }}
                >
                  {showNewPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div>
              <label className="form-label">{fa ? 'تکرار رمز عبور جدید' : 'Confirm new password'}</label>
              <input
                type="password"
                value={confirmPass}
                onChange={(e) => setConfirmPass(e.target.value)}
                className="input"
                required
                minLength={6}
                dir="ltr"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full py-3 text-base">
              {loading ? (
                <span className="flex items-center gap-2">
                  <Spinner />
                  {fa ? 'در حال ثبت...' : 'Saving...'}
                </span>
              ) : (fa ? 'تغییر رمز عبور' : 'Change password')}
            </button>
            <button type="button" onClick={goBackToLogin} className="w-full flex items-center justify-center gap-1.5 text-xs login-ghost-link transition-colors">
              <Back className="w-3.5 h-3.5" />
              {fa ? 'بازگشت به ورود' : 'Back to sign in'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
