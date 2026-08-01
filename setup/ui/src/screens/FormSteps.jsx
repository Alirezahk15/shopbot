import { useState } from 'react'
import {
  Bot, Hash, Lock, Globe, Mail, CreditCard, Wallet, KeyRound,
  ServerCog, ShieldCheck, RefreshCw, Coins,
} from 'lucide-react'
import { Field, TextInput, PasswordInput, Toggle, Alert, Spinner } from '../components/Shared.jsx'
import { T, tr } from '../i18n.js'
import { validateToken, checkDomain } from '../api.js'

const TOKEN_RE = /^[0-9]{6,}:[A-Za-z0-9_-]{30,}$/

/* ------------------------------------------------------------ Welcome */

export function WelcomeStep({ fa, serverIp, resumeAvailable, onResume }) {
  return (
    <div className="stack">
      <p className="muted">{tr(T.welcomeBody, fa)}</p>

      <div
        className="row between"
        style={{
          padding: '12px 14px',
          borderRadius: 12,
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid var(--line)',
        }}
      >
        <span className="row gap-2 small">
          <ServerCog size={15} />
          {tr(T.serverIp, fa)}
        </span>
        <span className="mono strong" dir="ltr">{serverIp || '...'}</span>
      </div>

      {resumeAvailable ? (
        <>
          <Alert kind="warn">{tr(T.resumeFound, fa)}</Alert>
          <button type="button" className="btn-secondary btn-full" onClick={onResume}>
            <RefreshCw size={16} />
            {tr(T.resumeBtn, fa)}
          </button>
        </>
      ) : null}
    </div>
  )
}

/* ------------------------------------------------------------ Bot */

export function BotStep({ fa, cfg, set, setValid }) {
  const [state, setState] = useState('idle') // idle | checking | ok | bad
  const [info, setInfo] = useState(null)
  const token = cfg.bot_token || ''
  const formatOk = TOKEN_RE.test(token.trim())

  const verify = async () => {
    if (!formatOk) return
    setState('checking')
    try {
      const res = await validateToken(token.trim())
      if (res && res.ok) {
        setState('ok')
        setInfo(res.info || null)
        if (res.info && res.info.username) set('bot_username', res.info.username)
        setValid(true)
      } else {
        setState('bad')
        setValid(false)
      }
    } catch {
      setState('bad')
      setValid(false)
    }
  }

  return (
    <div className="stack">
      <Field
        label={tr(T.botToken, fa)}
        icon={Bot}
        badge={tr(T.required, fa)}
        hint={tr(T.botTokenHint, fa)}
        error={
          (token && !formatOk && tr(T.tokenFormat, fa)) ||
          (state === 'bad' && tr(T.tokenInvalid, fa)) ||
          ''
        }
        okText={
          state === 'ok'
            ? `${tr(T.tokenValid, fa)}${info && info.username ? ' - @' + info.username : ''}`
            : ''
        }
      >
        <TextInput
          icon
          dir="ltr"
          autoFocus
          value={token}
          invalid={Boolean(token) && !formatOk}
          placeholder="123456789:AAE..."
          onChange={(e) => {
            set('bot_token', e.target.value.trim())
            setState('idle')
            setValid(false)
          }}
          onBlur={verify}
        />
      </Field>

      <button
        type="button"
        className="btn-secondary btn-full"
        onClick={verify}
        disabled={!formatOk || state === 'checking'}
      >
        {state === 'checking' ? <Spinner /> : <ShieldCheck size={16} />}
        {state === 'checking' ? tr(T.checking, fa) : tr(T.tokenValid, fa)}
      </button>
    </div>
  )
}

/* ------------------------------------------------------------ Admin */

export function AdminStep({ fa, cfg, set }) {
  const id = cfg.admin_id || ''
  const pass = cfg.panel_password || ''
  const idBad = Boolean(id) && !/^[0-9]{5,}$/.test(id)
  const passBad = Boolean(pass) && pass.length < 8

  return (
    <div className="stack">
      <Field
        label={tr(T.adminId, fa)}
        icon={Hash}
        badge={tr(T.required, fa)}
        hint={tr(T.adminIdHint, fa)}
        error={idBad ? tr(T.adminIdInvalid, fa) : ''}
      >
        <TextInput
          icon
          dir="ltr"
          inputMode="numeric"
          autoFocus
          value={id}
          invalid={idBad}
          placeholder="123456789"
          onChange={(e) => set('admin_id', e.target.value.replace(/\D/g, ''))}
        />
      </Field>

      <Field
        label={tr(T.panelPass, fa)}
        icon={Lock}
        badge={tr(T.required, fa)}
        hint={tr(T.panelPassHint, fa)}
        error={passBad ? tr(T.passTooShort, fa) : ''}
      >
        <PasswordInput
          icon
          value={pass}
          invalid={passBad}
          placeholder="********"
          onChange={(e) => set('panel_password', e.target.value)}
        />
      </Field>
    </div>
  )
}

/* ------------------------------------------------------------ Domain */

export function DomainStep({ fa, cfg, set, serverIp }) {
  const [dns, setDns] = useState(null) // null | 'checking' | true | false
  const domain = cfg.domain || ''

  const probe = async () => {
    if (!domain.trim()) {
      setDns(null)
      return
    }
    setDns('checking')
    try {
      const res = await checkDomain(domain.trim())
      const ok = Boolean(res && (res.ok || res.points_here))
      setDns(ok)
      set('_ssl_ok', ok)
    } catch {
      setDns(false)
    }
  }

  return (
    <div className="stack">
      <Field
        label={tr(T.domain, fa)}
        icon={Globe}
        badge={tr(T.optional, fa)}
        hint={tr(T.domainHint, fa)}
        okText={dns === true ? tr(T.domainOkPoints, fa) : ''}
        error={dns === false ? tr(T.domainWrongPoints, fa) : ''}
      >
        <TextInput
          icon
          dir="ltr"
          value={domain}
          placeholder="shop.example.com"
          onChange={(e) => {
            set('domain', e.target.value.trim().toLowerCase())
            setDns(null)
          }}
          onBlur={probe}
        />
      </Field>

      {dns === 'checking' ? (
        <p className="row gap-2 small muted">
          <Spinner size={14} />
          {tr(T.checking, fa)}
        </p>
      ) : null}

      {!domain ? <Alert kind="info">{tr(T.noDomainNote, fa)}</Alert> : null}

      {domain ? (
        <>
          <Toggle
            checked={Boolean(cfg.ssl)}
            onChange={(v) => set('ssl', v)}
            label={tr(T.useSsl, fa)}
            hint={`${serverIp || ''}`}
          />
          {cfg.ssl ? (
            <Field label={tr(T.sslEmail, fa)} icon={Mail} badge={tr(T.optional, fa)}>
              <TextInput
                icon
                dir="ltr"
                type="email"
                value={cfg.ssl_email || ''}
                placeholder="you@example.com"
                onChange={(e) => set('ssl_email', e.target.value.trim())}
              />
            </Field>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

/* ------------------------------------------------------------ Payments */

export function PaymentsStep({ fa, cfg, set }) {
  const rows = [
    ['pay_card', T.payCard, CreditCard, '6037 xxxx xxxx xxxx'],
    ['pay_zarinpal', T.payZarinpal, Coins, 'xxxxxxxx-xxxx-xxxx'],
    ['pay_bep20', T.payBep20, Wallet, '0x...'],
    ['pay_trc20', T.payTrc20, Wallet, 'T...'],
    ['pay_ton', T.payTon, Wallet, 'UQ...'],
    ['bscscan_key', T.bscscan, KeyRound, ''],
    ['navasan_key', T.navasan, KeyRound, ''],
  ]

  return (
    <div className="stack">
      <Alert kind="info">{tr(T.paySub, fa)}</Alert>
      {rows.map(([key, label, Icon, ph]) => (
        <Field
          key={key}
          label={tr(label, fa)}
          icon={Icon}
          badge={tr(T.optional, fa)}
          hint={key === 'bscscan_key' ? tr(T.bscscanHint, fa) : ''}
        >
          <TextInput
            icon
            dir="ltr"
            value={cfg[key] || ''}
            placeholder={ph}
            onChange={(e) => set(key, e.target.value.trim())}
          />
        </Field>
      ))}
    </div>
  )
}

/* ------------------------------------------------------------ Review */

export function ReviewStep({ fa, cfg, serverIp }) {
  const mask = (v) => (v ? '*'.repeat(Math.min(10, String(v).length)) : '')
  const none = tr(T.notSet, fa)

  const rows = [
    [tr(T.botToken, fa), cfg.bot_username ? '@' + cfg.bot_username : mask(cfg.bot_token) || none],
    [tr(T.adminId, fa), cfg.admin_id || none],
    [tr(T.panelPass, fa), mask(cfg.panel_password) || none],
    [tr(T.domain, fa), cfg.domain || `${serverIp || ''} (IP)`],
    ['SSL', cfg.domain && cfg.ssl ? tr(T.enabled, fa) : tr(T.disabled, fa)],
    [tr(T.payCard, fa), cfg.pay_card || none],
    [tr(T.payZarinpal, fa), cfg.pay_zarinpal || none],
    [tr(T.payBep20, fa), cfg.pay_bep20 || none],
    [tr(T.payTrc20, fa), cfg.pay_trc20 || none],
    [tr(T.payTon, fa), cfg.pay_ton || none],
  ]

  return (
    <div className="stack">
      <div
        style={{
          borderRadius: 12,
          border: '1px solid var(--line)',
          overflow: 'hidden',
        }}
      >
        {rows.map(([k, v], i) => (
          <div
            key={k}
            className="row between"
            style={{
              padding: '10px 14px',
              background: i % 2 ? 'rgba(255,255,255,0.02)' : 'transparent',
              gap: 12,
            }}
          >
            <span className="small muted">{k}</span>
            <span
              className="small mono"
              dir="ltr"
              style={{
                textAlign: 'end',
                wordBreak: 'break-all',
                color: v === none ? 'var(--text-dim)' : 'var(--text-strong)',
              }}
            >
              {v}
            </span>
          </div>
        ))}
      </div>
      <Alert kind="warn">{tr(T.reviewNote, fa)}</Alert>
    </div>
  )
}
