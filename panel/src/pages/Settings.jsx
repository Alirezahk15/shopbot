import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext.jsx'
import { t } from '../i18n.js'
import { useToast } from '../components/Toast.jsx'
import api, { downloadFile } from '../api/client.js'
import {
  SectionCard, SystemLiveTab, BackupTab, PaymentExtraCards, BotExtraCards,
  ReferralExtraCards, PanelExtraCards, ReportsExtraCards,
} from './SettingsExtra.jsx'
import {
  Bot, CreditCard, Zap, Settings as SettingsIcon, Server,
  Users, Save, CheckCircle, Eye, EyeOff, Key, Download,
  Database, HardDrive, RefreshCw, TrendingUp, Crown, Shield,
  Wallet, DollarSign, MessageSquare, AtSign, Percent, Clock,
  AlertTriangle, Lock, UserX, Star, ChevronDown, ChevronRight,
  Ticket, ShoppingBag, Globe, UserCog, X
} from 'lucide-react'

// ── Feature definitions with categories, descriptions, and customization ──
const FEATURE_GROUPS = [
  {
    key: 'payment',
    label: { fa: 'پرداخت', en: 'Payment' },
    color: '#f59e0b',
    icon: CreditCard,
    features: [
      {
        key: 'card_iranian_only',
        label: { fa: 'کارت فقط ایرانی', en: 'Card (Iranian Only)' },
        desc: { fa: 'پرداخت کارتی فقط برای کاربران فارسی‌زبان', en: 'Card payment only for Persian users' },
        color: '#f59e0b',
        defaultOn: true,
      },
      {
        key: 'automatic_card_confirm',
        label: { fa: 'تأیید خودکار کارت', en: 'Auto-Confirm Card' },
        desc: { fa: 'پرداخت‌های کارتی بدون نیاز به تأیید ادمین', en: 'Card payments confirmed without admin approval' },
        color: '#10b981',
        defaultOn: false,
        customizable: true,
        customComponent: 'card_detect',
      },
      {
        key: 'usd_rate',
        label: { fa: 'نرخ دلار آنلاین', en: 'Live USD Rate' },
        desc: { fa: 'نمایش نرخ لحظه‌ای دلار به کاربران', en: 'Show live USD rate to users' },
        color: '#3b82f6',
        defaultOn: true,
        customizable: true,
        customComponent: 'usd_rate',
      },
    ],
  },
  {
    key: 'support',
    label: { fa: 'پشتیبانی', en: 'Support' },
    color: '#ec4899',
    icon: Ticket,
    features: [
      {
        key: 'tickets',
        label: { fa: 'تیکت پشتیبانی', en: 'Support Tickets' },
        desc: { fa: 'کاربران می‌توانند تیکت پشتیبانی ارسال کنند', en: 'Users can submit support tickets' },
        color: '#ec4899',
        defaultOn: true,
        statsKey: 'tickets_open',
        statsLabel: { fa: 'تیکت باز', en: 'open tickets' },
      },
      {
        key: 'warranty',
        label: { fa: 'گارانتی', en: 'Warranty' },
        desc: { fa: 'کاربران می‌توانند درخواست گارانتی ثبت کنند', en: 'Users can submit warranty claims' },
        color: '#84cc16',
        defaultOn: true,
        statsKey: 'warranty_pending',
        statsLabel: { fa: 'درخواست معلق', en: 'pending claims' },
      },
    ],
  },
  {
    key: 'security',
    label: { fa: 'امنیت', en: 'Security' },
    color: '#ef4444',
    icon: Shield,
    features: [
      {
        key: 'lock_channels',
        label: { fa: 'قفل کانال‌ها', en: 'Lock Channels' },
        desc: { fa: 'کاربران باید عضو کانال‌های قفل‌شده باشند', en: 'Users must join locked channels' },
        color: '#ef4444',
        defaultOn: true,
        statsKey: 'locked_channels',
        statsLabel: { fa: 'کانال قفل', en: 'locked channels' },
      },
      {
        key: 'lock_groups',
        label: { fa: 'قفل گروه‌ها', en: 'Lock Groups' },
        desc: { fa: 'کاربران باید عضو گروه‌های قفل‌شده باشند', en: 'Users must join locked groups' },
        color: '#ef4444',
        defaultOn: true,
        statsKey: 'locked_groups',
        statsLabel: { fa: 'گروه قفل', en: 'locked groups' },
      },
    ],
  },
  {
    key: 'other',
    label: { fa: 'سایر', en: 'Other' },
    color: '#8b5cf6',
    icon: Zap,
    features: [
      {
        key: 'referral',
        label: { fa: 'سیستم رفرال', en: 'Referral System' },
        desc: { fa: 'کاربران با معرفی دوستان پورسانت دریافت کنند', en: 'Users earn commission by referring friends' },
        color: '#6366f1',
        defaultOn: true,
        statsKey: 'referrals_total',
        statsLabel: { fa: 'رفرال فعال', en: 'active referrals' },
      },
      {
        key: 'multi_admin',
        label: { fa: 'چند ادمین', en: 'Multi-Admin' },
        desc: { fa: 'امکان افزودن ادمین‌های اضافی', en: 'Allow adding additional admins' },
        color: '#8b5cf6',
        defaultOn: true,
        statsKey: 'admins_count',
        statsLabel: { fa: 'ادمین', en: 'admins' },
      },
    ],
  },
  {
    key: 'advanced',
    label: { fa: 'پیشرفته', en: 'Advanced' },
    color: '#6b7280',
    icon: SettingsIcon,
    features: [
      {
        key: 'maintenance_mode',
        label: { fa: 'حالت تعمیر', en: 'Maintenance Mode' },
        desc: { fa: 'ربات پیام "در حال تعمیر" نشان می‌دهد', en: 'Bot shows maintenance message to users' },
        color: '#ef4444',
        defaultOn: false,
        customizable: true,
        customFields: [
          { key: 'maintenance_message', label: { fa: 'پیام تعمیر', en: 'Maintenance Message' }, type: 'textarea', placeholder: { fa: 'ربات در حال تعمیر است...', en: 'Bot is under maintenance...' } },
        ],
      },
      {
        key: 'registration_locked',
        label: { fa: 'ثبت‌نام بسته', en: 'Registration Locked' },
        desc: { fa: 'کاربران جدید نمی‌توانند ثبت‌نام کنند', en: 'New users cannot register' },
        color: '#f59e0b',
        defaultOn: false,
      },
      {
        key: 'daily_purchase_limit',
        label: { fa: 'محدودیت خرید روزانه', en: 'Daily Purchase Limit' },
        desc: { fa: 'هر کاربر روزانه حداکثر X خرید می‌تواند انجام دهد', en: 'Each user can make max X purchases per day' },
        color: '#3b82f6',
        defaultOn: false,
        customizable: true,
        customFields: [
          { key: 'daily_purchase_limit_value', label: { fa: 'حداکثر خرید روزانه', en: 'Max Daily Purchases' }, type: 'number', placeholder: '5', min: 1 },
        ],
      },
      {
        key: 'vip_mode',
        label: { fa: 'حالت VIP', en: 'VIP Mode' },
        desc: { fa: 'کاربران VIP تخفیف خودکار دریافت می‌کنند', en: 'VIP users receive automatic discounts' },
        color: '#f59e0b',
        defaultOn: false,
        customizable: true,
        customFields: [
          { key: 'vip_discount', label: { fa: 'درصد تخفیف VIP', en: 'VIP Discount %' }, type: 'number', placeholder: '10', min: 1, max: 100 },
        ],
      },
    ],
  },
]

// ── Saved indicator ──
function SavedBadge({ lang }) {
  return (
    <span className="flex items-center gap-1 text-xs text-green-400 animate-fade-in">
      <CheckCircle className="w-3.5 h-3.5" /> {lang === 'fa' ? 'ذخیره شد' : 'Saved'}
    </span>
  )
}

// ── Tab button ──
function TabBtn({ active, onClick, icon: Icon, label, color }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap"
      style={{
        background: active ? `${color}15` : 'transparent',
        border: `1px solid ${active ? color + '40' : 'transparent'}`,
        color: active ? color : 'rgba(156,163,175,0.7)',
      }}
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      {label}
    </button>
  )
}

// ── Bot Tab ──
function BotTab({ data, lang }) {
  const { toast } = useToast()
  const [form, setForm] = useState({ welcome_message: '', support_username: '', premium_button_icons: '0' })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setForm({ welcome_message: data.welcome_message || '', support_username: data.support_username || '', premium_button_icons: data.premium_button_icons || '0' })
    }
  }, [data])

  const mutation = useMutation({
    mutationFn: (body) => api.post('/settings/bot', body),
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); toast(lang === 'fa' ? 'تنظیمات ربات ذخیره شد' : 'Bot settings saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  return (
    <div className="settings-masonry">
      <div className="settings-col">
      <SectionCard icon={Bot} color="#6366f1" title={lang === 'fa' ? 'تنظیمات ربات' : 'Bot Settings'} badge={saved ? <SavedBadge lang={lang} /> : null}>
        <div className="space-y-4">
          <div>
            <label className="form-label flex items-center gap-1.5"><MessageSquare className="w-3.5 h-3.5" />{lang === 'fa' ? 'پیام خوش‌آمدگویی' : 'Welcome Message'}</label>
            <textarea
              value={form.welcome_message}
              onChange={(e) => setForm({ ...form, welcome_message: e.target.value })}
              className="input"
              rows={4}
              placeholder={lang === 'fa' ? 'پیام خوش‌آمدگویی به کاربران... (HTML پشتیبانی می‌شود)' : 'Welcome message for users... (HTML supported)'}
            />
            <p className="text-xs text-gray-500 mt-1">{lang === 'fa' ? 'اگر خالی باشد، پیام پیش‌فرض نمایش داده می‌شود — ایموجی پرمیوم: [emoji:شناسه:🔥]' : 'If empty, default message is shown — Premium emoji: [emoji:ID:🔥]'}</p>
          </div>
          <div>
            <label className="form-label flex items-center gap-1.5"><AtSign className="w-3.5 h-3.5" />{lang === 'fa' ? 'نام کاربری پشتیبانی' : 'Support Username'}</label>
            <input
              value={form.support_username}
              onChange={(e) => setForm({ ...form, support_username: e.target.value })}
              className="input"
              placeholder="@support_username"
              dir="ltr"
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <label className="form-label flex items-center gap-1.5"><Star className="w-3.5 h-3.5" />{lang === 'fa' ? 'ایموجی پرمیوم روی دکمه‌ها' : 'Premium emoji on buttons'}</label>
              <p className="text-xs text-gray-500">{lang === 'fa' ? 'نمایش [emoji:شناسه:🔥] به‌صورت آیکون واقعی روی دکمه‌ها (Bot API 9.4) — نیازمند اشتراک پرمیوم مالک ربات یا یوزرنیم Fragment' : 'Render [emoji:ID:🔥] as a real icon on buttons (Bot API 9.4) — requires bot-owner Premium or a Fragment username'}</p>
            </div>
            <button
              type="button"
              onClick={() => setForm({ ...form, premium_button_icons: form.premium_button_icons === '1' ? '0' : '1' })}
              className={`toggle-switch ${form.premium_button_icons === '1' ? 'on' : ''}`}
            >
              <span className="toggle-knob" />
            </button>
          </div>
          <button onClick={() => mutation.mutate(form)} disabled={mutation.isPending} className="btn-primary">
            <Save className="w-4 h-4" /> {mutation.isPending ? t('loading', lang) : t('save', lang)}
          </button>
        </div>
      </SectionCard>
      <BotExtraCards data={data} lang={lang} col={0} />
      </div>
      <div className="settings-col">
      <BotExtraCards data={data} lang={lang} col={1} />
      </div>
    </div>
  )
}

// ── Payment Tab ──
function PaymentTab({ data, lang }) {
  const { toast } = useToast()
  const [cardForm, setCardForm] = useState({ card_number: '', card_holder: '' })
  const [walletForm, setWalletForm] = useState({ wallet: '' })
  const [limitsForm, setLimitsForm] = useState({ min_deposit: 1, max_deposit: 0 })
  const [savedCard, setSavedCard] = useState(false)
  const [savedWallet, setSavedWallet] = useState(false)
  const [savedLimits, setSavedLimits] = useState(false)

  useEffect(() => {
    if (data) {
      setCardForm({ card_number: data.card_number || '', card_holder: data.card_holder || '' })
      setWalletForm({ wallet: data.usdt_wallet || '' })
      setLimitsForm({ min_deposit: parseFloat(data.min_deposit || 1), max_deposit: parseFloat(data.max_deposit || 0) })
    }
  }, [data])

  const cardMutation = useMutation({
    mutationFn: (body) => api.post('/settings/card', body),
    onSuccess: () => { setSavedCard(true); setTimeout(() => setSavedCard(false), 2000); toast(lang === 'fa' ? 'تنظیمات کارت ذخیره شد' : 'Card settings saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const walletMutation = useMutation({
    mutationFn: (body) => api.post('/settings/wallet', body),
    onSuccess: (res) => {
      if (res.data.error) { toast(res.data.error, 'error'); return }
      setSavedWallet(true); setTimeout(() => setSavedWallet(false), 2000)
      toast(lang === 'fa' ? 'کیف پول ذخیره شد' : 'Wallet saved', 'success')
    },
    onError: () => toast(t('error', lang), 'error'),
  })

  const limitsMutation = useMutation({
    mutationFn: (body) => api.post('/settings/deposit-limits', body),
    onSuccess: () => { setSavedLimits(true); setTimeout(() => setSavedLimits(false), 2000); toast(lang === 'fa' ? 'محدودیت‌ها ذخیره شد' : 'Limits saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  return (
    <div className="settings-masonry">
      <div className="settings-col">
      {/* Card */}
      <SectionCard icon={CreditCard} color="#eab308" title={lang === 'fa' ? 'کارت به کارت' : 'Card Payment'} badge={savedCard ? <SavedBadge lang={lang} /> : null}>
        <div className="space-y-3">
          <div>
            <label className="form-label">{t('pm_card_num', lang)}</label>
            <input value={cardForm.card_number} onChange={(e) => setCardForm({ ...cardForm, card_number: e.target.value })} className="input" placeholder="6037-XXXX-XXXX-XXXX" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{t('pm_card_holder', lang)}</label>
            <input value={cardForm.card_holder} onChange={(e) => setCardForm({ ...cardForm, card_holder: e.target.value })} className="input" />
          </div>
          <button onClick={() => cardMutation.mutate(cardForm)} disabled={cardMutation.isPending} className="btn-primary">
            <Save className="w-4 h-4" /> {cardMutation.isPending ? t('loading', lang) : t('save', lang)}
          </button>
        </div>
      </SectionCard>
      <PaymentExtraCards data={data} lang={lang} col={0} />
      </div>
      <div className="settings-col">

      {/* USDT Wallet */}
      <SectionCard icon={Wallet} color="#a855f7" title={lang === 'fa' ? 'کیف پول USDT (BEP20)' : 'USDT Wallet (BEP20)'} badge={savedWallet ? <SavedBadge lang={lang} /> : null}>
        <div className="space-y-3">
          <div>
            <label className="form-label">{t('pm_wallet', lang)}</label>
            <input value={walletForm.wallet} onChange={(e) => setWalletForm({ wallet: e.target.value })} className="input font-mono text-sm" placeholder="0x..." dir="ltr" />
          </div>
          <button onClick={() => walletMutation.mutate(walletForm)} disabled={walletMutation.isPending} className="btn-primary">
            <Save className="w-4 h-4" /> {walletMutation.isPending ? t('loading', lang) : t('save', lang)}
          </button>
        </div>
      </SectionCard>

      {/* Deposit limits */}
      <SectionCard icon={DollarSign} color="#10b981" title={lang === 'fa' ? 'محدودیت واریز' : 'Deposit Limits'} badge={savedLimits ? <SavedBadge lang={lang} /> : null}>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="form-label">{lang === 'fa' ? 'حداقل ($)' : 'Min ($)'}</label>
            <input type="number" step="0.01" min="0" value={limitsForm.min_deposit} onChange={(e) => setLimitsForm({ ...limitsForm, min_deposit: parseFloat(e.target.value) || 0 })} className="input" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{lang === 'fa' ? 'حداکثر ($) — ۰ = بدون محدودیت' : 'Max ($) — 0 = unlimited'}</label>
            <input type="number" step="0.01" min="0" value={limitsForm.max_deposit} onChange={(e) => setLimitsForm({ ...limitsForm, max_deposit: parseFloat(e.target.value) || 0 })} className="input" dir="ltr" />
          </div>
        </div>
        <button onClick={() => limitsMutation.mutate(limitsForm)} disabled={limitsMutation.isPending} className="btn-primary mt-3">
          <Save className="w-4 h-4" /> {limitsMutation.isPending ? t('loading', lang) : t('save', lang)}
        </button>
      </SectionCard>
      <PaymentExtraCards data={data} lang={lang} col={1} />
      </div>
    </div>
  )
}

// ── USD Rate Inline (inside Features tab) ──
function UsdRateInline({ lang, data }) {
  const { toast } = useToast()
  const [provider, setProvider] = useState(data?.usd_rate_provider || 'tgju')
  const [apiKey, setApiKey] = useState(data?.usd_rate_api_key || '')
  const [manualRate, setManualRate] = useState(data?.usd_rate_manual || '90000')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setProvider(data.usd_rate_provider || 'tgju')
      setApiKey(data.usd_rate_api_key || '')
      setManualRate(data.usd_rate_manual || '90000')
    }
  }, [data])

  const { data: providersData } = useQuery({ queryKey: ['usd-providers'], queryFn: () => api.get('/settings/usd-providers').then(r => r.data) })
  const providers = providersData?.providers || {}

  const saveMutation = useMutation({
    mutationFn: (body) => api.post('/settings/usd-rate', body),
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); toast(lang === 'fa' ? 'ذخیره شد' : 'Saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const handleTest = async () => {
    setTesting(true); setTestResult(null)
    try {
      const res = await api.post('/settings/usd-rate/test')
      setTestResult(res.data)
    } catch (err) {
      setTestResult({ success: false, error: err.response?.data?.detail || 'Test failed' })
    } finally { setTesting(false) }
  }

  const currentProvider = providers[provider] || {}

  return (
    <div className="space-y-3 pt-1">
      {/* Provider pills */}
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(providers).map(([key, p]) => (
          <button
            key={key}
            onClick={() => setProvider(key)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: provider === key ? 'rgba(59,130,246,0.15)' : 'var(--surface-hover, rgba(255,255,255,0.05))',
              border: `1px solid ${provider === key ? 'rgba(59,130,246,0.4)' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
              color: provider === key ? '#60a5fa' : 'rgba(156,163,175,0.7)',
            }}
          >
            {p.name}
          </button>
        ))}
      </div>

      {/* API Key */}
      {currentProvider.requires_key && provider !== 'manual' && (
        <div>
          <label className="form-label text-xs">API Key</label>
          <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="input text-sm py-1.5" placeholder="API Key..." dir="ltr" />
        </div>
      )}

      {/* Manual rate */}
      {provider === 'manual' && (
        <div>
          <label className="form-label text-xs">{lang === 'fa' ? 'نرخ دستی (تومان)' : 'Manual Rate (Toman)'}</label>
          <input type="number" value={manualRate} onChange={(e) => setManualRate(e.target.value)} className="input text-sm py-1.5" dir="ltr" />
        </div>
      )}

      {/* Test result */}
      {testResult && (
        <div className="rounded-lg px-3 py-2 text-xs animate-slide-up" style={{ background: testResult.success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)', border: `1px solid ${testResult.success ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}` }}>
          {testResult.success
            ? <span className="text-green-400">✅ {lang === 'fa' ? 'نرخ دلار' : 'USD Rate'}: <b>{testResult.rate?.toLocaleString()} {lang === 'fa' ? 'تومان' : 'Toman'}</b></span>
            : <span className="text-red-400">❌ {testResult.error}</span>
          }
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={() => saveMutation.mutate({ provider, api_key: apiKey, manual_rate: manualRate, cache_minutes: 30 })} disabled={saveMutation.isPending} className="btn-primary text-sm py-1.5 flex-1">
          <Save className="w-3.5 h-3.5" /> {saved ? (lang === 'fa' ? 'ذخیره شد' : 'Saved') : t('save', lang)}
        </button>
        {provider !== 'manual' && (
          <button onClick={handleTest} disabled={testing} className="btn-secondary text-sm py-1.5 px-3">
            {testing ? <div className="w-3.5 h-3.5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /> : (lang === 'fa' ? 'تست' : 'Test')}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Card Detect Inline (inside Features tab) ──
function CardDetectInline({ lang, data }) {
  const { toast } = useToast()
  const [method, setMethod] = useState(data?.card_detect_method || 'manual')
  const [fields, setFields] = useState({ sms_number: '', email: '', email_password: '', gateway_name: '', gateway_key: '', gateway_merchant: '' })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setMethod(data.card_detect_method || 'manual')
      setFields(prev => ({ ...prev, sms_number: data.card_detect_sms_number || '', email: data.card_detect_email || '', gateway_name: data.card_detect_gateway || '', gateway_key: data.card_detect_gateway_key || '' }))
    }
  }, [data])

  const { data: methodsData } = useQuery({ queryKey: ['card-detect-methods'], queryFn: () => api.get('/settings/card-detect-methods').then(r => r.data) })
  const methods = methodsData?.methods || {}
  const currentMethod = methods[method] || {}

  const saveMutation = useMutation({
    mutationFn: (body) => api.post('/settings/card-detect', body),
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); toast(lang === 'fa' ? 'ذخیره شد' : 'Saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  return (
    <div className="space-y-3 pt-1">
      {/* Method pills */}
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(methods).map(([key, m]) => (
          <button
            key={key}
            onClick={() => setMethod(key)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: method === key ? 'rgba(236,72,153,0.15)' : 'var(--surface-hover, rgba(255,255,255,0.05))',
              border: `1px solid ${method === key ? 'rgba(236,72,153,0.4)' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
              color: method === key ? '#f9a8d4' : 'rgba(156,163,175,0.7)',
            }}
          >
            {lang === 'fa' ? m.name : m.name_en}
          </button>
        ))}
      </div>

      {/* Method description */}
      {currentMethod.desc && (
        <p className="text-xs text-gray-500">{lang === 'fa' ? currentMethod.desc : currentMethod.desc_en}</p>
      )}

      {/* Dynamic fields */}
      {currentMethod.fields?.map(field => (
        <div key={field.key}>
          <label className="form-label text-xs">{lang === 'fa' ? field.label : field.label_en}</label>
          <input
            type={field.key.includes('password') || field.key.includes('key') ? 'password' : 'text'}
            value={fields[field.key] || ''}
            onChange={(e) => setFields(prev => ({ ...prev, [field.key]: e.target.value }))}
            className="input text-sm py-1.5"
            placeholder={field.placeholder}
            dir="ltr"
          />
        </div>
      ))}

      {currentMethod.note && (
        <p className="text-xs flex items-center gap-1" style={{ color: '#f59e0b' }}>
          <AlertTriangle className="w-3 h-3" /> {lang === 'fa' ? currentMethod.note : currentMethod.note_en}
        </p>
      )}

      <button onClick={() => saveMutation.mutate({ method, ...fields })} disabled={saveMutation.isPending} className="btn-primary text-sm py-1.5 w-full">
        <Save className="w-3.5 h-3.5" /> {saved ? (lang === 'fa' ? 'ذخیره شد' : 'Saved') : t('save', lang)}
      </button>
    </div>
  )
}

// ── Feature Item ──
function FeatureItem({ feature, isOn, lang, onToggle, stats, featureValues, onSaveValue, settingsData }) {
  const [expanded, setExpanded] = useState(false)
  const [localValues, setLocalValues] = useState({})
  const { toast } = useToast()

  useEffect(() => {
    if (featureValues) {
      const initial = {}
      feature.customFields?.forEach(f => {
        initial[f.key] = featureValues[f.key] || ''
      })
      setLocalValues(initial)
    }
  }, [featureValues])

  const statValue = stats?.[feature.statsKey]

  return (
    <div
      className="rounded-xl overflow-hidden transition-all"
      style={{
        background: isOn ? `${feature.color}08` : 'var(--surface-hover, rgba(255,255,255,0.03))',
        border: `1px solid ${isOn ? feature.color + '25' : 'var(--surface-hover, rgba(255,255,255,0.06))'}`,
      }}
    >
      {/* Main row */}
      <div className="flex items-center gap-3 px-4 py-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: isOn ? `${feature.color}15` : 'var(--surface-hover, rgba(255,255,255,0.05))' }}
        >
          <div className="w-2.5 h-2.5 rounded-full" style={{ background: isOn ? feature.color : 'rgba(107,114,128,0.4)' }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-200">{feature.label[lang] || feature.label.en}</span>
            {statValue !== undefined && statValue > 0 && (
              <span
                className="text-xs px-1.5 py-0.5 rounded-full"
                style={{ background: `${feature.color}15`, color: feature.color, border: `1px solid ${feature.color}25` }}
              >
                {statValue} {feature.statsLabel?.[lang] || feature.statsLabel?.en}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{feature.desc?.[lang] || feature.desc?.en}</p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {feature.customizable && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="action-btn action-neutral"
              title={lang === 'fa' ? 'تنظیمات' : 'Settings'}
            >
              {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4 rtl-flip" />}
            </button>
          )}
          <button
            onClick={() => onToggle(!isOn)}
            className={`toggle-switch ${isOn ? 'on' : ''}`}
          >
            <span className="toggle-knob" />
          </button>
        </div>
      </div>

      {/* Customization panel */}
      {expanded && feature.customizable && (
        <div
          className="px-4 pb-4 pt-2 accordion-content"
          style={{ borderTop: `1px solid ${feature.color}15` }}
        >
          {/* Custom component (USD Rate or Card Detect) */}
          {feature.customComponent === 'usd_rate' && (
            <UsdRateInline lang={lang} data={settingsData} />
          )}
          {feature.customComponent === 'card_detect' && (
            <CardDetectInline lang={lang} data={settingsData} />
          )}

          {/* Standard custom fields */}
          {!feature.customComponent && feature.customFields && (
            <div className="space-y-3">
              {feature.customFields.map(field => (
                <div key={field.key}>
                  <label className="form-label">{field.label[lang] || field.label.en}</label>
                  {field.type === 'textarea' ? (
                    <textarea
                      value={localValues[field.key] || ''}
                      onChange={(e) => setLocalValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                      className="input text-sm"
                      rows={3}
                      placeholder={field.placeholder?.[lang] || field.placeholder?.en}
                    />
                  ) : (
                    <input
                      type={field.type || 'text'}
                      min={field.min}
                      max={field.max}
                      value={localValues[field.key] || ''}
                      onChange={(e) => setLocalValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                      className="input text-sm"
                      placeholder={field.placeholder?.[lang] || field.placeholder?.en}
                      dir="ltr"
                    />
                  )}
                </div>
              ))}
              <button
                onClick={() => {
                  feature.customFields?.forEach(f => {
                    if (localValues[f.key] !== undefined) {
                      onSaveValue(f.key, localValues[f.key])
                    }
                  })
                }}
                className="btn-primary text-sm py-1.5"
              >
                <Save className="w-3.5 h-3.5" /> {t('save', lang)}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Features Tab ──
function FeaturesTab({ data, lang }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const [openGroups, setOpenGroups] = useState(new Set())

  const featureMutation = useMutation({
    mutationFn: ({ key, value }) => api.post('/settings/feature', { key, value }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['settings'] }),
    onError: () => toast(t('error', lang), 'error'),
  })

  const featureValueMutation = useMutation({
    mutationFn: ({ key, value }) => api.post('/settings/feature-value', { key, value }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['settings'] }); toast(lang === 'fa' ? 'ذخیره شد' : 'Saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const { data: statsData } = useQuery({
    queryKey: ['feature-stats'],
    queryFn: () => api.get('/settings/feature-stats').then(r => r.data),
    refetchInterval: 30000,
  })

  const features = data?.features || {}
  const featureValues = data?.feature_values || {}

  const toggleGroup = (key) => {
    setOpenGroups(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const renderGroup = (group) => {
        const GroupIcon = group.icon
        const isOpen = openGroups.has(group.key)
        const activeCount = group.features.filter(f => features[f.key]).length

        return (
          <div key={group.key} className="card p-0 overflow-hidden">
            {/* Group header */}
            <button
              onClick={() => toggleGroup(group.key)}
              className="w-full flex items-center gap-3 px-4 py-3 transition-all"
              style={{ background: isOpen ? `${group.color}08` : 'transparent' }}
            >
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: `${group.color}15` }}
              >
                <GroupIcon className="w-4 h-4" style={{ color: group.color }} />
              </div>
              <span className="font-semibold text-sm text-white flex-1 text-start">
                {group.label[lang] || group.label.en}
              </span>
              <span
                className="text-xs px-2 py-0.5 rounded-full me-2"
                style={{ background: `${group.color}15`, color: group.color }}
              >
                {activeCount}/{group.features.length} {lang === 'fa' ? 'فعال' : 'active'}
              </span>
              <ChevronDown
                className="w-4 h-4 text-gray-500 transition-transform"
                style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
              />
            </button>

            {/* Features list */}
            <div className={`group-collapse ${isOpen ? 'open' : ''}`}>
              <div className="group-collapse-inner">
              <div className="px-3 pb-3 space-y-2" style={{ borderTop: `1px solid ${isOpen ? group.color + '15' : 'transparent'}`, transition: 'border-color 0.3s ease' }}>
                <div className="pt-2" />
                {group.features.map(feature => (
                  <FeatureItem
                    key={feature.key}
                    feature={feature}
                    isOn={features[feature.key] ?? feature.defaultOn}
                    lang={lang}
                    onToggle={(value) => featureMutation.mutate({ key: feature.key, value })}
                    stats={statsData}
                    featureValues={featureValues}
                    onSaveValue={(key, value) => featureValueMutation.mutate({ key, value })}
                    settingsData={data}
                  />
                ))}
              </div>
              </div>
            </div>
          </div>
        )
  }

  return (
    <div className="settings-masonry">
      <div className="settings-col">{FEATURE_GROUPS.filter((_, i) => i % 2 === 0).map(renderGroup)}</div>
      <div className="settings-col">{FEATURE_GROUPS.filter((_, i) => i % 2 === 1).map(renderGroup)}</div>
    </div>
  )
}

// ── Panel Tab ──
function PanelTab({ lang }) {
  const { toast } = useToast()
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)

  const mutation = useMutation({
    mutationFn: (body) => api.post('/settings/change-password', body),
    onSuccess: () => {
      toast(lang === 'fa' ? 'رمز تغییر کرد — لطفاً دوباره وارد شوید' : 'Password changed — please log in again', 'success')
      setTimeout(() => { localStorage.removeItem('token'); window.location.href = '/login' }, 2000)
    },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (form.new_password !== form.confirm) { toast(lang === 'fa' ? 'رمزها یکسان نیستند' : 'Passwords do not match', 'error'); return }
    mutation.mutate({ current_password: form.current_password, new_password: form.new_password })
  }

  return (
    <div className="settings-masonry">
      <div className="settings-col">
      <SectionCard icon={Key} color="#6366f1" title={lang === 'fa' ? 'تغییر رمز عبور پنل' : 'Change Panel Password'}>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="form-label">{lang === 'fa' ? 'رمز فعلی' : 'Current Password'}</label>
            <div className="relative">
              <input type={showCurrent ? 'text' : 'password'} value={form.current_password} onChange={(e) => setForm({ ...form, current_password: e.target.value })} className="input" style={{ paddingInlineEnd: '40px' }} required dir="ltr" />
              <button type="button" onClick={() => setShowCurrent(!showCurrent)} className="absolute top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300" style={{ insetInlineEnd: '12px' }}>
                {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="form-label">{lang === 'fa' ? 'رمز جدید' : 'New Password'}</label>
            <div className="relative">
              <input type={showNew ? 'text' : 'password'} value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} className="input" style={{ paddingInlineEnd: '40px' }} required minLength={6} dir="ltr" />
              <button type="button" onClick={() => setShowNew(!showNew)} className="absolute top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300" style={{ insetInlineEnd: '12px' }}>
                {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="form-label">{lang === 'fa' ? 'تکرار رمز جدید' : 'Confirm New Password'}</label>
            <input type="password" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} className="input" required dir="ltr" />
          </div>
          <button type="submit" disabled={mutation.isPending} className="btn-primary">
            <Key className="w-4 h-4" /> {mutation.isPending ? t('loading', lang) : (lang === 'fa' ? 'تغییر رمز' : 'Change Password')}
          </button>
        </form>
      </SectionCard>
      <PanelExtraCards lang={lang} col={0} />
      </div>
      <div className="settings-col">
      <PanelExtraCards lang={lang} col={1} />
      </div>
    </div>
  )
}

// ── System Tab ──
function SystemTab({ lang }) {
  const { toast } = useToast()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['system-info'],
    queryFn: () => api.get('/settings/system-info').then(r => r.data),
  })

  const handleBackup = () => {
    downloadFile('/settings/backup', 'shop.db')
    toast(lang === 'fa' ? 'در حال دانلود backup...' : 'Downloading backup...', 'info')
  }

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /></div>

  return (
    <div className="settings-masonry">
      {/* System info */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white flex items-center gap-2"><Server className="w-4 h-4 text-blue-400" />{lang === 'fa' ? 'اطلاعات سیستم' : 'System Info'}</h3>
          <button onClick={() => refetch()} className="action-btn action-neutral"><RefreshCw className="w-4 h-4" /></button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Python', value: data?.python_version, color: '#6366f1' },
            { label: 'OS', value: data?.os, color: '#3b82f6' },
            { label: 'SQLite', value: data?.sqlite_version, color: '#10b981' },
            { label: lang === 'fa' ? 'حجم DB' : 'DB Size', value: `${data?.db_size_kb} KB`, color: '#f59e0b' },
          ].map((s, i) => (
            <div key={i} className="rounded-xl p-3" style={{ background: `${s.color}10`, border: `1px solid ${s.color}20` }}>
              <div className="text-xs text-gray-500 mb-0.5">{s.label}</div>
              <div className="font-semibold text-white text-sm">{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Database records */}
      <div className="card">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4"><Database className="w-4 h-4 text-green-400" />{lang === 'fa' ? 'آمار دیتابیس' : 'Database Records'}</h3>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: lang === 'fa' ? 'کاربران' : 'Users', value: data?.records?.users, color: '#6366f1' },
            { label: lang === 'fa' ? 'سفارش‌ها' : 'Orders', value: data?.records?.orders, color: '#10b981' },
            { label: lang === 'fa' ? 'تراکنش‌ها' : 'Transactions', value: data?.records?.transactions, color: '#f59e0b' },
          ].map((s, i) => (
            <div key={i} className="rounded-xl p-3 text-center" style={{ background: `${s.color}10`, border: `1px solid ${s.color}20` }}>
              <div className="font-bold text-lg" style={{ color: s.color }}>{s.value?.toLocaleString()}</div>
              <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Disk space */}
      {data?.disk && (
        <div className="card">
          <h3 className="font-semibold text-white flex items-center gap-2 mb-4"><HardDrive className="w-4 h-4 text-purple-400" />{lang === 'fa' ? 'فضای دیسک' : 'Disk Space'}</h3>
          <div className="mb-2">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>{lang === 'fa' ? 'استفاده شده' : 'Used'}: {data.disk.used_gb} GB</span>
              <span>{lang === 'fa' ? 'آزاد' : 'Free'}: {data.disk.free_gb} GB</span>
            </div>
            <div className="h-2 rounded-full" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.08))' }}>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${data.disk.percent}%`,
                  background: data.disk.percent > 80 ? '#ef4444' : data.disk.percent > 60 ? '#f59e0b' : '#10b981',
                }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">{data.disk.percent}% {lang === 'fa' ? 'از' : 'of'} {data.disk.total_gb} GB</p>
          </div>
        </div>
      )}

      {/* Backup */}
      <div className="card">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-3"><Download className="w-4 h-4 text-indigo-400" />{lang === 'fa' ? 'پشتیبان‌گیری' : 'Backup'}</h3>
        <p className="text-sm text-gray-400 mb-3">
          {lang === 'fa' ? 'دانلود فایل دیتابیس به عنوان backup' : 'Download database file as backup'}
        </p>
        <button onClick={handleBackup} className="btn-primary">
          <Download className="w-4 h-4" /> {lang === 'fa' ? 'دانلود shop.db' : 'Download shop.db'}
        </button>
      </div>
    </div>
  )
}

// ── Referral Tab ──
function ReferralTab({ data, lang }) {
  const { toast } = useToast()
  const [form, setForm] = useState({ referral_percent: 10, referral_min_days: 60 })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setForm({
        referral_percent: parseInt(data.referral_percent || 10),
        referral_min_days: parseInt(data.referral_min_days || 60),
      })
    }
  }, [data])

  const mutation = useMutation({
    mutationFn: (body) => api.post('/settings/referral', body),
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); toast(lang === 'fa' ? 'تنظیمات رفرال ذخیره شد' : 'Referral settings saved', 'success') },
    onError: (err) => toast(err.response?.data?.detail || t('error', lang), 'error'),
  })

  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['referral-stats'],
    queryFn: () => api.get('/settings/referral-stats').then(r => r.data),
  })

  return (
    <div className="settings-masonry">
      <div className="settings-col">
      {/* Settings */}
      <SectionCard icon={Users} color="#6366f1" title={lang === 'fa' ? 'تنظیمات رفرال' : 'Referral Settings'} badge={saved ? <SavedBadge lang={lang} /> : null}>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="form-label flex items-center gap-1.5"><Percent className="w-3.5 h-3.5" />{lang === 'fa' ? 'درصد پورسانت' : 'Commission %'}</label>
            <input
              type="number" dir="ltr" min="1" max="100"
              value={form.referral_percent}
              onChange={(e) => setForm({ ...form, referral_percent: parseInt(e.target.value) || 1 })}
              className="input"
              dir="ltr"
            />
            <p className="text-xs text-gray-500 mt-1">{lang === 'fa' ? 'درصدی از هر خرید که به معرف می‌رسد' : 'Percentage of each purchase paid to referrer'}</p>
          </div>
          <div>
            <label className="form-label flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" />{lang === 'fa' ? 'حداقل سن اکانت (روز)' : 'Min Account Age (days)'}</label>
            <input
              type="number" dir="ltr" min="0"
              value={form.referral_min_days}
              onChange={(e) => setForm({ ...form, referral_min_days: parseInt(e.target.value) || 0 })}
              className="input"
              dir="ltr"
            />
            <p className="text-xs text-gray-500 mt-1">{lang === 'fa' ? 'اکانت باید حداقل این تعداد روز قدیمی باشد' : 'Account must be at least this many days old'}</p>
          </div>
        </div>
        <button onClick={() => mutation.mutate(form)} disabled={mutation.isPending} className="btn-primary">
          <Save className="w-4 h-4" /> {mutation.isPending ? t('loading', lang) : t('save', lang)}
        </button>
      </SectionCard>
      <ReferralExtraCards data={data} lang={lang} col={0} />
      </div>
      <div className="settings-col">

      {/* Stats */}
      <SectionCard icon={TrendingUp} color="#10b981" title={lang === 'fa' ? 'آمار رفرال' : 'Referral Stats'}>
        {statsLoading ? (
          <div className="flex justify-center py-4"><div className="w-6 h-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /></div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}>
                <div className="font-bold text-xl text-indigo-400">{statsData?.total_referrals || 0}</div>
                <div className="text-xs text-gray-500 mt-0.5">{lang === 'fa' ? 'کل رفرال‌ها' : 'Total Referrals'}</div>
              </div>
              <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
                <div className="font-bold text-xl text-green-400">${statsData?.total_earnings?.toFixed(2) || '0.00'}</div>
                <div className="text-xs text-gray-500 mt-0.5">{lang === 'fa' ? 'کل پورسانت پرداختی' : 'Total Commissions Paid'}</div>
              </div>
            </div>

            {/* Top referrers */}
            {(statsData?.top_referrers || []).length > 0 && (
              <div>
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">{lang === 'fa' ? 'برترین معرف‌ها' : 'Top Referrers'}</div>
                <div className="space-y-2">
                  {(statsData?.top_referrers || []).map((r, i) => (
                    <div key={r.user_id} className="flex items-center gap-3 rounded-xl px-3 py-2" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
                      <span className="text-xs font-bold w-5 text-center" style={{ color: i === 0 ? '#f59e0b' : '#6b7280' }}>{i + 1}</span>
                      <span className="text-sm text-gray-300 flex-1 truncate">@{r.username || r.user_id}</span>
                      <span className="badge-blue text-xs">{r.ref_count} {lang === 'fa' ? 'رفرال' : 'refs'}</span>
                      <span className="text-xs text-green-400">${r.ref_earnings?.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </SectionCard>
      <ReferralExtraCards data={data} lang={lang} col={1} />
      </div>
    </div>
  )
}

// ── USD Rate Tab ──
function UsdRateTab({ data, lang }) {
  const { toast } = useToast()
  const [provider, setProvider] = useState(data?.usd_rate_provider || 'tgju')
  const [apiKey, setApiKey] = useState(data?.usd_rate_api_key || '')
  const [manualRate, setManualRate] = useState(data?.usd_rate_manual || '90000')
  const [cacheMinutes, setCacheMinutes] = useState(parseInt(data?.usd_rate_cache_minutes || 30))
  const [saved, setSaved] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    if (data) {
      setProvider(data.usd_rate_provider || 'tgju')
      setApiKey(data.usd_rate_api_key || '')
      setManualRate(data.usd_rate_manual || '90000')
      setCacheMinutes(parseInt(data.usd_rate_cache_minutes || 30))
    }
  }, [data])

  const { data: providersData } = useQuery({
    queryKey: ['usd-providers'],
    queryFn: () => api.get('/settings/usd-providers').then(r => r.data),
  })

  const saveMutation = useMutation({
    mutationFn: (body) => api.post('/settings/usd-rate', body),
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); toast(lang === 'fa' ? 'تنظیمات نرخ دلار ذخیره شد' : 'USD rate settings saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.post('/settings/usd-rate/test')
      setTestResult(res.data)
    } catch (err) {
      setTestResult({ success: false, error: err.response?.data?.detail || 'Test failed' })
    } finally {
      setTesting(false)
    }
  }

  const providers = providersData?.providers || {}
  const currentProvider = providers[provider] || {}

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white flex items-center gap-2"><DollarSign className="w-4 h-4 text-green-400" />{lang === 'fa' ? 'سرویس نرخ دلار' : 'USD Rate Service'}</h3>
          {saved && <SavedBadge lang={lang} />}
        </div>

        {/* Provider selection */}
        <div className="space-y-2 mb-4">
          {Object.entries(providers).map(([key, p]) => (
            <button
              key={key}
              onClick={() => setProvider(key)}
              className="w-full flex items-start gap-3 px-4 py-3 rounded-xl text-sm transition-all"
              style={{
                background: provider === key ? 'rgba(16,185,129,0.12)' : 'var(--surface-hover, rgba(255,255,255,0.04))',
                border: `1px solid ${provider === key ? 'rgba(16,185,129,0.35)' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
              }}
            >
              <div
                className="w-4 h-4 rounded-full border-2 flex-shrink-0 mt-0.5"
                style={{
                  borderColor: provider === key ? '#10b981' : 'rgba(107,114,128,0.5)',
                  background: provider === key ? '#10b981' : 'transparent',
                }}
              />
              <div className="flex-1 text-start">
                <div className="font-medium" style={{ color: provider === key ? '#34d399' : 'rgba(209,213,219,0.9)' }}>
                  {p.name}
                  {p.free && <span className="ms-2 text-xs badge-green">رایگان</span>}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{lang === 'fa' ? p.description : (p.description_en || p.description)}</div>
              </div>
            </button>
          ))}
        </div>

        {/* API Key (if required) */}
        {currentProvider.requires_key && provider !== 'manual' && (
          <div className="mb-3">
            <label className="form-label">{lang === 'fa' ? 'API Key' : 'API Key'}</label>
            <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="input font-mono text-sm" placeholder="API Key..." dir="ltr" />
          </div>
        )}

        {/* Manual rate */}
        {provider === 'manual' && (
          <div className="mb-3">
            <label className="form-label">{lang === 'fa' ? 'نرخ دستی (تومان)' : 'Manual Rate (Toman)'}</label>
            <input type="number" value={manualRate} onChange={(e) => setManualRate(e.target.value)} className="input" placeholder="90000" dir="ltr" />
          </div>
        )}

        {/* Cache minutes */}
        {provider !== 'manual' && (
          <div className="mb-4">
            <label className="form-label">{lang === 'fa' ? 'بروزرسانی هر (دقیقه)' : 'Update every (minutes)'}</label>
            <input type="number" min="1" max="1440" value={cacheMinutes} onChange={(e) => setCacheMinutes(parseInt(e.target.value) || 30)} className="input" dir="ltr" />
          </div>
        )}

        {/* Test result */}
        {testResult && (
          <div
            className="rounded-xl px-4 py-3 mb-3 animate-slide-up"
            style={{
              background: testResult.success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
              border: `1px solid ${testResult.success ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
            }}
          >
            {testResult.success ? (
              <div>
                <p className="text-sm font-semibold text-green-400">✅ {lang === 'fa' ? 'تست موفق' : 'Test Successful'}</p>
                <p className="text-sm text-white mt-1">{lang === 'fa' ? 'نرخ دلار' : 'USD Rate'}: <b>{testResult.rate?.toLocaleString()} {lang === 'fa' ? 'تومان' : 'Toman'}</b></p>
                <p className="text-xs text-gray-500 mt-0.5">{lang === 'fa' ? 'منبع' : 'Source'}: {testResult.provider}</p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-semibold text-red-400">❌ {lang === 'fa' ? 'تست ناموفق' : 'Test Failed'}</p>
                <p className="text-xs text-gray-400 mt-1">{testResult.error}</p>
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={() => saveMutation.mutate({ provider, api_key: apiKey, manual_rate: manualRate, cache_minutes: cacheMinutes })}
            disabled={saveMutation.isPending}
            className="btn-primary flex-1"
          >
            <Save className="w-4 h-4" /> {saveMutation.isPending ? t('loading', lang) : t('save', lang)}
          </button>
          {provider !== 'manual' && (
            <button onClick={handleTest} disabled={testing} className="btn-secondary px-4">
              {testing ? <div className="w-4 h-4 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" /> : (lang === 'fa' ? 'تست' : 'Test')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Card Detection Tab ──
function CardDetectTab({ data, lang }) {
  const { toast } = useToast()
  const [method, setMethod] = useState(data?.card_detect_method || 'manual')
  const [fields, setFields] = useState({
    sms_number: data?.card_detect_sms_number || '',
    email: data?.card_detect_email || '',
    email_password: '',
    gateway_name: data?.card_detect_gateway || '',
    gateway_key: data?.card_detect_gateway_key || '',
    gateway_merchant: '',
  })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setMethod(data.card_detect_method || 'manual')
      setFields(prev => ({
        ...prev,
        sms_number: data.card_detect_sms_number || '',
        email: data.card_detect_email || '',
        gateway_name: data.card_detect_gateway || '',
        gateway_key: data.card_detect_gateway_key || '',
      }))
    }
  }, [data])

  const { data: methodsData } = useQuery({
    queryKey: ['card-detect-methods'],
    queryFn: () => api.get('/settings/card-detect-methods').then(r => r.data),
  })

  const saveMutation = useMutation({
    mutationFn: (body) => api.post('/settings/card-detect', body),
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); toast(lang === 'fa' ? 'تنظیمات ذخیره شد' : 'Settings saved', 'success') },
    onError: () => toast(t('error', lang), 'error'),
  })

  const methods = methodsData?.methods || {}
  const currentMethod = methods[method] || {}

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white flex items-center gap-2"><CreditCard className="w-4 h-4 text-pink-400" />{lang === 'fa' ? 'روش تشخیص پرداخت کارتی' : 'Card Payment Detection Method'}</h3>
          {saved && <SavedBadge lang={lang} />}
        </div>

        {/* Method selection */}
        <div className="space-y-2 mb-4">
          {Object.entries(methods).map(([key, m]) => (
            <button
              key={key}
              onClick={() => setMethod(key)}
              className="w-full flex items-start gap-3 px-4 py-3 rounded-xl text-sm transition-all"
              style={{
                background: method === key ? 'rgba(236,72,153,0.1)' : 'var(--surface-hover, rgba(255,255,255,0.04))',
                border: `1px solid ${method === key ? 'rgba(236,72,153,0.3)' : 'var(--surface-hover, rgba(255,255,255,0.08))'}`,
              }}
            >
              <div
                className="w-4 h-4 rounded-full border-2 flex-shrink-0 mt-0.5"
                style={{
                  borderColor: method === key ? '#ec4899' : 'rgba(107,114,128,0.5)',
                  background: method === key ? '#ec4899' : 'transparent',
                }}
              />
              <div className="flex-1 text-start">
                <div className="font-medium" style={{ color: method === key ? '#f9a8d4' : 'rgba(209,213,219,0.9)' }}>
                  {lang === 'fa' ? m.name : m.name_en}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{lang === 'fa' ? m.desc : m.desc_en}</div>
                {m.note && (
                  <div className="text-xs mt-1 flex items-center gap-1" style={{ color: '#f59e0b' }}>
                    <AlertTriangle className="w-3 h-3" />
                    {lang === 'fa' ? m.note : m.note_en}
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Dynamic fields for selected method */}
        {currentMethod.fields?.length > 0 && (
          <div className="space-y-3 mb-4 p-4 rounded-xl accordion-content" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))', border: '1px solid var(--border-soft, rgba(255,255,255,0.06))' }}>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{lang === 'fa' ? 'تنظیمات روش انتخابی' : 'Selected Method Settings'}</p>
            {currentMethod.fields.map(field => (
              <div key={field.key}>
                <label className="form-label">{lang === 'fa' ? field.label : field.label_en}</label>
                <input
                  type={field.key.includes('password') || field.key.includes('key') ? 'password' : 'text'}
                  value={fields[field.key] || ''}
                  onChange={(e) => setFields(prev => ({ ...prev, [field.key]: e.target.value }))}
                  className="input text-sm"
                  placeholder={field.placeholder}
                  dir="ltr"
                />
              </div>
            ))}
          </div>
        )}

        <button
          onClick={() => saveMutation.mutate({ method, ...fields })}
          disabled={saveMutation.isPending}
          className="btn-primary w-full"
        >
          <Save className="w-4 h-4" /> {saveMutation.isPending ? t('loading', lang) : t('save', lang)}
        </button>
      </div>

      {/* Info box */}
      <div className="card" style={{ borderColor: 'rgba(245,158,11,0.2)', background: 'rgba(245,158,11,0.05)' }}>
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-yellow-300 mb-1">{lang === 'fa' ? 'توجه مهم' : 'Important Note'}</p>
            <p className="text-xs text-gray-400 leading-relaxed">
              {lang === 'fa'
                ? 'روش‌های SMS، ایمیل و درگاه پرداخت نیاز به تنظیمات اضافی در سرور دارند. این تنظیمات فقط پیکربندی را ذخیره می‌کنند — پیاده‌سازی کامل نیاز به توسعه بیشتر دارد.'
                : 'SMS, Email, and Gateway methods require additional server-side setup. These settings only save the configuration — full implementation requires further development.'
              }
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main Settings Page ──
export default function Settings() {
  const { lang } = useApp()
  const [activeTab, setActiveTab] = useState('features')

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get('/settings').then(r => r.data),
  })

  const tabs = [
    { key: 'features', icon: Zap, label: lang === 'fa' ? 'قابلیت‌ها' : 'Features', color: '#6366f1' },
    { key: 'payment', icon: CreditCard, label: lang === 'fa' ? 'پرداخت' : 'Payment', color: '#f59e0b' },
    { key: 'bot', icon: Bot, label: lang === 'fa' ? 'ربات' : 'Bot', color: '#3b82f6' },
    { key: 'referral', icon: Users, label: lang === 'fa' ? 'رفرال' : 'Referral', color: '#8b5cf6' },
    { key: 'panel', icon: SettingsIcon, label: lang === 'fa' ? 'پنل' : 'Panel', color: '#a855f7' },
    { key: 'reports', icon: MessageSquare, label: lang === 'fa' ? 'گزارش‌ها' : 'Reports', color: '#22c55e' },
    { key: 'backup', icon: Database, label: lang === 'fa' ? 'بکاپ' : 'Backup', color: '#10b981' },
    { key: 'system', icon: Server, label: lang === 'fa' ? 'سیستم' : 'System', color: '#6b7280' },
  ]

  if (isLoading) return (
    <div className="flex justify-center py-12">
      <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
    </div>
  )

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">{t('set_title', lang)}</h1>
        <p className="text-sm text-gray-500 mt-0.5">{lang === 'fa' ? 'مدیریت تنظیمات ربات و پنل' : 'Manage bot and panel settings'}</p>
      </div>

      {/* Tab bar */}
      <div
        className="flex gap-1 mb-6 overflow-x-auto pb-1"
        style={{ scrollbarWidth: 'none' }}
      >
        {tabs.map(tab => (
          <TabBtn
            key={tab.key}
            active={activeTab === tab.key}
            onClick={() => setActiveTab(tab.key)}
            icon={tab.icon}
            label={tab.label}
            color={tab.color}
          />
        ))}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in">
        {activeTab === 'features' && <FeaturesTab data={data} lang={lang} />}
        {activeTab === 'payment' && <PaymentTab data={data} lang={lang} />}
        {activeTab === 'bot' && <BotTab data={data} lang={lang} />}
        {activeTab === 'referral' && <ReferralTab data={data} lang={lang} />}
        {activeTab === 'panel' && <PanelTab lang={lang} />}
        {activeTab === 'reports' && <ReportsTab data={data} lang={lang} />}
        {activeTab === 'backup' && <BackupTab lang={lang} />}
        {activeTab === 'system' && <SystemLiveTab lang={lang} />}
      </div>
    </div>
  )
}

// ── Reports Tab (گزارشات گروهی با تاپیک) ──
function ReportsTab({ data, lang }) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const fa = lang === 'fa'
  const CATS = [
    { key: 'sales', icon: ShoppingBag, label: fa ? 'فروش‌ها' : 'Sales' },
    { key: 'payments', icon: CreditCard, label: fa ? 'پرداخت‌های کارتی' : 'Card Payments' },
    { key: 'deposits', icon: Wallet, label: fa ? 'واریزهای USDT' : 'USDT Deposits' },
    { key: 'tickets', icon: Ticket, label: fa ? 'تیکت‌ها' : 'Tickets' },
    { key: 'warranty', icon: Shield, label: fa ? 'گارانتی' : 'Warranty' },
    { key: 'new_users', icon: Users, label: fa ? 'کاربران جدید' : 'New Users' },
    { key: 'daily', icon: TrendingUp, label: fa ? 'گزارش روزانه' : 'Daily Report' },
    { key: 'errors', icon: AlertTriangle, label: fa ? 'خطاها و هشدارها' : 'Errors & Alerts' },
    { key: 'sessions', icon: UserCog, label: fa ? 'نشست‌ها (ورود به پنل)' : 'Sessions (Panel Logins)' },
    { key: 'backups', icon: Database, label: fa ? 'بکاپ دیتابیس' : 'Database Backups' },
  ]
  const [form, setForm] = useState({ group_id: '', mode: 'dm', daily_time: '23:00', backup_hours: '0', topics: {}, flags: {} })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) setForm({
      group_id: data.report_group_id || '',
      mode: data.report_mode || 'dm',
      daily_time: data.report_daily_time || '23:00',
      backup_hours: String(parseFloat(data.backup_interval_hours || '0') || 0),
      topics: data.report_topics || {},
      flags: data.report_flags || {},
    })
  }, [data])

  const saveMutation = useMutation({
    mutationFn: () => api.post('/settings/reports', {
      report_group_id: form.group_id,
      report_mode: form.mode,
      report_daily_time: form.daily_time,
      backup_interval_hours: form.backup_hours,
      topics: form.topics,
      flags: form.flags,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['settings'] }); setSaved(true); setTimeout(() => setSaved(false), 2000); toast(fa ? 'تنظیمات گزارشات ذخیره شد' : 'Report settings saved', 'success') },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا در ذخیره' : 'Save failed'), 'error'),
  })

  const testMutation = useMutation({
    mutationFn: () => api.post('/settings/reports/test'),
    onSuccess: (r) => {
      const res = r.data.results || {}
      const fails = Object.entries(res).filter(([, v]) => v !== true)
      if (fails.length === 0) toast(fa ? 'پیام تست به همه تاپیک‌ها ارسال شد' : 'Test sent to all topics', 'success')
      else toast((fa ? 'خطا در ارسال: ' : 'Failed: ') + fails.map(([k, v]) => `${k} (${v})`).join(' — '), 'error')
    },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا در تست' : 'Test failed'), 'error'),
  })

  const prettyTopicError = (msg) => {
    const m = String(msg)
    if (!fa) return m
    if (m.includes('not enough rights')) return 'ربات دسترسی «مدیریت تاپیک‌ها» را در گروه ندارد'
    if (m.includes('not a forum')) return 'قابلیت تاپیک‌ها (Topics) در گروه فعال نیست'
    if (m.includes('chat not found')) return 'گروه پیدا نشد؛ آیدی گروه را بررسی کنید'
    return m
  }

  const createTopicsMutation = useMutation({
    mutationFn: () => api.post('/settings/reports/create-topics', { group_id: form.group_id }),
    onSuccess: (r) => {
      const { created = {}, errors = {} } = r.data
      const newTopics = { ...form.topics }
      Object.entries(created).forEach(([k, v]) => { newTopics[k] = String(v) })
      setForm({ ...form, topics: newTopics })
      qc.invalidateQueries({ queryKey: ['settings'] })
      const errList = Object.entries(errors)
      const n = Object.keys(created).length
      if (errList.length === 0) {
        toast(fa ? (n > 0 ? `${n} تاپیک ساخته و ذخیره شد` : 'همه دسته‌ها از قبل تاپیک دارند') : `${n} topics created`, 'success')
      } else {
        toast((fa ? 'خطا: ' : 'Error: ') + prettyTopicError(errList[0][1]), 'error')
      }
    },
    onError: (e) => toast(e.response?.data?.detail || (fa ? 'خطا در ساخت تاپیک‌ها' : 'Failed to create topics'), 'error'),
  })

  const setTopic = (key, val) => setForm({ ...form, topics: { ...form.topics, [key]: val } })
  const toggleFlag = (key) => setForm({ ...form, flags: { ...form.flags, [key]: !form.flags[key] } })

  return (
    <div className="settings-masonry">
      <div className="settings-col">
      {/* Group config */}
      <SectionCard icon={MessageSquare} color="#10b981" title={fa ? 'گروه گزارشات' : 'Reports Group'} badge={saved ? <SavedBadge lang={lang} /> : null}>
        <p className="text-xs mb-4 leading-6" style={{ color: 'var(--text-dim)' }}>
          {fa
            ? 'یک گروه با قابلیت «تاپیک‌ها» (Topics) بسازید، ربات را ادمین کنید و آیدی عددی گروه را اینجا وارد کنید. سپس با دکمه «ساخت خودکار تاپیک‌ها» همه تاپیک‌ها یک‌جا ساخته و آیدی‌هاشان خودکار ذخیره می‌شود (نیازمند دسترسی Manage Topics برای ربات). در صورت تمایل می‌توانید آیدی تاپیک را دستی هم وارد کنید (خالی = ارسال در General).'
            : 'Create a group with Topics enabled, add the bot as admin, and enter the numeric group ID. For each category set its topic ID (empty = General topic). You can find the topic ID in the link of any message inside that topic.'}
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="form-label">{fa ? 'آیدی عددی گروه' : 'Group ID'}</label>
            <input value={form.group_id} onChange={(e) => setForm({ ...form, group_id: e.target.value })} className="input" placeholder="-1001234567890" dir="ltr" />
          </div>
          <div>
            <label className="form-label">{fa ? 'حالت ارسال گزارش‌ها' : 'Delivery Mode'}</label>
            <select value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })} className="input">
              <option value="dm">{fa ? 'فقط پیوی ادمین‌ها' : 'Admin DMs only'}</option>
              <option value="group">{fa ? 'فقط گروه' : 'Group only'}</option>
              <option value="both">{fa ? 'گروه + پیوی ادمین‌ها' : 'Group + Admin DMs'}</option>
            </select>
          </div>
        </div>
      </SectionCard>
      <ReportsExtraCards data={data} lang={lang} col={0} />
      </div>
      <div className="settings-col">

      {/* Topics per category */}
      <SectionCard icon={Server} color="#6366f1" title={fa ? 'تاپیک هر دسته گزارش' : 'Topic per Category'}>
        <div className="space-y-2">
          {CATS.map(({ key, icon: Icon, label }) => (
            <div key={key} className="flex flex-wrap items-center gap-3 p-3 rounded-xl" style={{ background: 'var(--surface-hover, rgba(255,255,255,0.03))' }}>
              <button
                onClick={() => toggleFlag(key)}
                className={`toggle-switch ${form.flags[key] ? 'on' : ''}`}
                title={form.flags[key] ? (fa ? 'فعال' : 'On') : (fa ? 'غیرفعال' : 'Off')}
              >
                <span className="toggle-knob" />
              </button>
              <div className="flex items-center gap-2 flex-1" style={{ minWidth: 150 }}>
                <Icon className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                <span className="text-sm text-white">{label}</span>
              </div>
              {key === 'daily' && (
                <input value={form.daily_time} onChange={(e) => setForm({ ...form, daily_time: e.target.value })} className="input" style={{ width: 100 }} placeholder="23:00" dir="ltr" title={fa ? 'ساعت ارسال (به وقت سرور)' : 'Send time (server time)'} />
              )}
              <input
                value={form.topics[key] || ''}
                onChange={(e) => setTopic(key, e.target.value)}
                className="input"
                style={{ width: 130 }}
                placeholder={fa ? 'آیدی تاپیک' : 'Topic ID'}
                dir="ltr"
              />
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 mt-4">
          <button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="btn-primary">
            <Save className="w-4 h-4" /> {saveMutation.isPending ? t('loading', lang) : t('save', lang)}
          </button>
          <button onClick={() => createTopicsMutation.mutate()} disabled={createTopicsMutation.isPending} className="btn-secondary">
            <Server className={`w-4 h-4 ${createTopicsMutation.isPending ? 'animate-pulse' : ''}`} />
            {createTopicsMutation.isPending ? (fa ? 'در حال ساخت...' : 'Creating...') : (fa ? 'ساخت خودکار تاپیک‌ها' : 'Auto-create Topics')}
          </button>
          <button onClick={() => testMutation.mutate()} disabled={testMutation.isPending} className="btn-secondary">
            <RefreshCw className={`w-4 h-4 ${testMutation.isPending ? 'animate-spin' : ''}`} />
            {fa ? 'ارسال پیام تست' : 'Send Test'}
          </button>
        </div>
        <p className="text-[11px] mt-3 leading-5" style={{ color: 'var(--text-dim)' }}>
          {fa
            ? 'نکته: هر ورود به پنل در تاپیک «نشست‌ها» با دکمه تأیید/رد گزارش می‌شود؛ با زدن «رد و خروج» آن دستگاه بلافاصله از پنل خارج می‌شود. ساعت گزارش روزانه و بکاپ خودکار بر اساس ساعت سرور است.'
            : 'Note: each panel login is reported to the Sessions topic with Approve/Reject buttons; rejecting immediately logs that device out. Daily report and auto-backup times use server time.'}
        </p>
      </SectionCard>
      <ReportsExtraCards data={data} lang={lang} col={1} />
      </div>
    </div>
  )
}
