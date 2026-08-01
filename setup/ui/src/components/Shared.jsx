import { useState } from 'react'
import { AlertCircle, CheckCircle2, Info, TriangleAlert, Eye, EyeOff } from 'lucide-react'

export function Spinner({ size = 16 }) {
  return (
    <svg
      className="spin"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle opacity="0.25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        opacity="0.75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

const ALERT_ICONS = {
  error: AlertCircle,
  success: CheckCircle2,
  warn: TriangleAlert,
  info: Info,
}

export function Alert({ kind = 'info', children, shakeKey }) {
  const Icon = ALERT_ICONS[kind] || Info
  return (
    <div key={shakeKey} className={`alert ${kind}`}>
      <Icon size={16} style={{ flexShrink: 0, marginTop: 2 }} />
      <span>{children}</span>
    </div>
  )
}

export function Field({
  label,
  icon: Icon,
  hint,
  error,
  okText,
  badge,
  children,
}) {
  return (
    <div>
      <div className="row between" style={{ marginBottom: 2 }}>
        <label className="form-label">{label}</label>
        {badge ? (
          <span className="tiny muted" style={{ marginBottom: 6 }}>
            {badge}
          </span>
        ) : null}
      </div>
      <div className="input-wrap">
        {Icon ? <Icon size={16} className="input-icon" /> : null}
        {children}
      </div>
      {error ? <p className="field-error">{error}</p> : null}
      {!error && okText ? <p className="field-ok">{okText}</p> : null}
      {!error && !okText && hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  )
}

export function TextInput({ icon, invalid, style, ...rest }) {
  return (
    <input
      {...rest}
      className={`input${invalid ? ' invalid' : ''}`}
      style={{ paddingInlineStart: icon ? 38 : undefined, ...style }}
    />
  )
}

export function PasswordInput({ icon, invalid, value, onChange, ...rest }) {
  const [show, setShow] = useState(false)
  return (
    <>
      <input
        {...rest}
        type={show ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        dir="ltr"
        className={`input${invalid ? ' invalid' : ''}`}
        style={{ paddingInlineStart: icon ? 38 : 14, paddingInlineEnd: 44 }}
      />
      <button
        type="button"
        className="input-action"
        onClick={() => setShow((s) => !s)}
        tabIndex={-1}
      >
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </>
  )
}

export function Toggle({ checked, onChange, label, hint }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="row gap-3"
      style={{
        width: '100%',
        textAlign: 'start',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid var(--line)',
        borderRadius: 12,
        padding: '12px 14px',
        color: 'inherit',
      }}
    >
      <span
        style={{
          width: 40,
          height: 22,
          borderRadius: 999,
          flexShrink: 0,
          position: 'relative',
          transition: 'background 0.2s ease',
          background: checked
            ? 'linear-gradient(135deg, var(--primary), var(--accent))'
            : 'rgba(255,255,255,0.14)',
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: 3,
            insetInlineStart: checked ? 21 : 3,
            width: 16,
            height: 16,
            borderRadius: 999,
            background: '#fff',
            transition: 'inset-inline-start 0.2s ease',
          }}
        />
      </span>
      <span style={{ flex: 1 }}>
        <span style={{ display: 'block', fontWeight: 600 }}>{label}</span>
        {hint ? (
          <span className="tiny muted" style={{ display: 'block' }}>
            {hint}
          </span>
        ) : null}
      </span>
    </button>
  )
}
