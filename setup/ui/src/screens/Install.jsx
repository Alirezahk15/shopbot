import {
  TriangleAlert, RefreshCw, ShieldCheck, RotateCcw, PartyPopper,
  ExternalLink, Lightbulb,
} from 'lucide-react'
import StepRail from '../components/StepRail.jsx'
import LogConsole from '../components/LogConsole.jsx'
import ProgressBar from '../components/ProgressBar.jsx'
import { Alert, Spinner } from '../components/Shared.jsx'
import { T, tr } from '../i18n.js'

/* Live installation view: progress, per-step rail, streaming log,
   and recovery actions when a step fails. */
export default function Install({
  fa,
  state,
  logs,
  busy,
  onRetryStep,
  onRetrySsl,
  onResume,
  onRestartClean,
}) {
  const error = state.error
  const done = state.done && !error
  const steps = state.steps || []
  const failedKey = (steps.find((s) => s.status === 'error') || {}).key

  return (
    <div className="stack">
      {!done && !error ? <ProgressBar value={state.progress} /> : null}

      {/* ---------------------------------------------- failure */}
      {error ? (
        <div className="stack">
          <Alert kind="error">
            <span className="strong">{tr(T.errorTitle, fa)}</span>
            {error.title ? <> - {error.title}</> : null}
          </Alert>

          {error.detail ? (
            <pre
              dir="ltr"
              className="mono tiny"
              style={{
                margin: 0,
                padding: '10px 12px',
                borderRadius: 10,
                background: 'rgba(0,0,0,0.45)',
                border: '1px solid var(--line)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: '#fca5a5',
                textAlign: 'left',
              }}
            >
              {error.detail}
            </pre>
          ) : null}

          {error.solutions && error.solutions.length ? (
            <div
              style={{
                padding: '12px 14px',
                borderRadius: 12,
                border: '1px solid rgba(245,158,11,0.3)',
                background: 'rgba(245,158,11,0.07)',
              }}
            >
              <div className="row gap-2 small strong" style={{ marginBottom: 8 }}>
                <Lightbulb size={14} />
                {tr(T.howToFix, fa)}
              </div>
              <ol style={{ margin: 0, paddingInlineStart: 18 }}>
                {error.solutions.map((s, i) => (
                  <li key={i} className="small" style={{ marginBottom: 6 }}>
                    <span dir="ltr" className="mono" style={{ wordBreak: 'break-word' }}>
                      {s}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}

          <div className="row gap-2" style={{ flexWrap: 'wrap' }}>
            <button className="btn-primary" onClick={onRetryStep} disabled={busy}>
              {busy ? <Spinner /> : <RefreshCw size={16} />}
              {busy ? tr(T.retrying, fa) : tr(T.retryStep, fa)}
            </button>
            <button className="btn-secondary" onClick={onResume} disabled={busy}>
              <RefreshCw size={16} />
              {tr(T.resumeRest, fa)}
            </button>
            {failedKey === 'ssl' ? (
              <button className="btn-secondary" onClick={onRetrySsl} disabled={busy}>
                <ShieldCheck size={16} />
                {tr(T.retrySsl, fa)}
              </button>
            ) : null}
            <button className="btn-ghost" onClick={onRestartClean} disabled={busy}>
              <RotateCcw size={16} />
              {tr(T.startOver, fa)}
            </button>
          </div>
        </div>
      ) : null}

      {/* ---------------------------------------------- success */}
      {done ? (
        <div className="stack">
          <div className="center stack">
            <div
              style={{
                width: 64,
                height: 64,
                margin: '0 auto',
                borderRadius: 18,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, var(--ok), #34d399)',
                boxShadow: '0 8px 25px rgba(16,185,129,0.45)',
              }}
            >
              <PartyPopper size={30} color="#fff" />
            </div>
            <h2 style={{ margin: 0, fontSize: 20 }}>{tr(T.doneTitle, fa)}</h2>
            <p className="muted small" style={{ marginTop: 4 }}>
              {tr(T.doneSub, fa)}
            </p>
          </div>

          {state.panel_url ? (
            <a
              className="btn-primary btn-full"
              href={state.panel_url}
              target="_blank"
              rel="noreferrer"
              style={{ textDecoration: 'none' }}
            >
              <ExternalLink size={16} />
              {tr(T.openPanel, fa)}
            </a>
          ) : null}

          <Alert kind="info">{tr(T.loginHint, fa)}</Alert>
          <Alert kind="warn">{tr(T.doneSecurity, fa)}</Alert>
        </div>
      ) : null}

      {/* ---------------------------------------------- warnings */}
      {state.warnings && state.warnings.length ? (
        <div className="stack">
          {state.warnings.map((w, i) => (
            <Alert kind="warn" key={i}>
              <span className="row gap-2">
                <TriangleAlert size={14} style={{ flexShrink: 0 }} />
                {w}
              </span>
            </Alert>
          ))}
        </div>
      ) : null}

      <StepRail steps={steps} fa={fa} />
      <LogConsole lines={logs} fa={fa} />
    </div>
  )
}
