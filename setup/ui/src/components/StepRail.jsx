import { Check, X, Loader2, Circle } from 'lucide-react'
import { STEP_LABELS, tr } from '../i18n.js'

// Live list of the 11 backend installation steps.
// `steps` comes straight from the wizard API: [{ key, status }, ...]
export default function StepRail({ steps, fa }) {
  if (!steps || steps.length === 0) return null

  return (
    <div className="stack" style={{ display: 'grid', gap: 6 }}>
      {steps.map((s, i) => {
        const status = s.status || 'pending'
        const label = tr(STEP_LABELS[s.key], fa) || s.key

        let Icon = Circle
        let color = 'var(--text-dim)'
        let extra = {}
        if (status === 'done') {
          Icon = Check
          color = 'var(--ok)'
        } else if (status === 'error') {
          Icon = X
          color = 'var(--err)'
        } else if (status === 'running') {
          Icon = Loader2
          color = 'var(--primary)'
          extra = { className: 'spin' }
        }

        return (
          <div
            key={s.key}
            className="row gap-3 animate-fade-in"
            style={{
              padding: '9px 12px',
              borderRadius: 10,
              background:
                status === 'running'
                  ? 'rgba(99,102,241,0.10)'
                  : status === 'error'
                    ? 'rgba(239,68,68,0.08)'
                    : 'transparent',
              border:
                status === 'running'
                  ? '1px solid rgba(99,102,241,0.28)'
                  : '1px solid transparent',
              animationDelay: `${i * 25}ms`,
            }}
          >
            <span
              style={{
                width: 22,
                height: 22,
                borderRadius: 999,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                color,
                background:
                  status === 'done'
                    ? 'rgba(16,185,129,0.14)'
                    : status === 'error'
                      ? 'rgba(239,68,68,0.14)'
                      : 'rgba(255,255,255,0.05)',
              }}
            >
              <Icon size={13} {...extra} />
            </span>
            <span
              className="small"
              style={{
                flex: 1,
                color:
                  status === 'pending' ? 'var(--text-dim)' : 'var(--text-strong)',
                fontWeight: status === 'running' ? 700 : 500,
              }}
            >
              {label}
            </span>
            <span className="tiny muted mono">{i + 1}/{steps.length}</span>
          </div>
        )
      })}
    </div>
  )
}
