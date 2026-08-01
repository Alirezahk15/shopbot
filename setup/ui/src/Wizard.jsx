import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Bot, Languages, ArrowLeft, ArrowRight, Rocket, ShieldCheck,
  Globe, CreditCard, UserCog, ClipboardCheck, Sparkles,
} from 'lucide-react'
import { Alert, Spinner } from './components/Shared.jsx'
import {
  WelcomeStep, BotStep, AdminStep, DomainStep, PaymentsStep, ReviewStep,
} from './screens/FormSteps.jsx'
import Install from './screens/Install.jsx'
import { T, tr } from './i18n.js'
import {
  getServerInfo, getState, saveConfig, startInstall, resumeInstall,
  retryStep, retrySsl, restartClean,
} from './api.js'

const PAGES = [
  { key: 'welcome', icon: Sparkles, title: T.welcomeTitle, sub: T.wizardSub },
  { key: 'bot', icon: Bot, title: T.botTitle, sub: T.botSub },
  { key: 'admin', icon: UserCog, title: T.adminTitle, sub: T.adminSub },
  { key: 'domain', icon: Globe, title: T.domainTitle, sub: T.domainSub },
  { key: 'payments', icon: CreditCard, title: T.payTitle, sub: T.paySub },
  { key: 'review', icon: ClipboardCheck, title: T.reviewTitle, sub: T.reviewSub },
]

const EMPTY_STATE = {
  progress: 0,
  done: false,
  error: null,
  running: false,
  steps: [],
  warnings: [],
  panel_url: '',
}

export default function Wizard() {
  const [fa, setFa] = useState(true)
  const [page, setPage] = useState(0)
  const [installing, setInstalling] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [shakeKey, setShakeKey] = useState(0)

  const [serverIp, setServerIp] = useState('')
  const [resumeAvailable, setResumeAvailable] = useState(false)
  const [tokenVerified, setTokenVerified] = useState(false)

  const [cfg, setCfg] = useState({
    bot_token: '', bot_username: '', admin_id: '', panel_password: '',
    domain: '', ssl: true, ssl_email: '',
    pay_card: '', pay_bep20: '', pay_trc20: '', pay_ton: '', pay_zarinpal: '',
    bscscan_key: '', zarinpal_id: '', navasan_key: '',
  })

  const [state, setState] = useState(EMPTY_STATE)
  const [logs, setLogs] = useState([])
  const esRef = useRef(null)

  const set = useCallback((k, v) => setCfg((c) => ({ ...c, [k]: v })), [])

  const fail = (msg) => {
    setError(msg)
    setShakeKey((k) => k + 1)
  }

  useEffect(() => {
    document.documentElement.lang = fa ? 'fa' : 'en'
    document.documentElement.dir = fa ? 'rtl' : 'ltr'
  }, [fa])

  useEffect(() => {
    getServerInfo()
      .then((info) => {
        if (!info) return
        setServerIp(info.ip || '')
        setResumeAvailable(Boolean(info.resume_available))
      })
      .catch(() => {})
  }, [])

  /* Stream logs + state while an installation is running. */
  const openStream = useCallback(() => {
    if (esRef.current) esRef.current.close()
    const es = new EventSource('/api/logs/stream')
    esRef.current = es

    es.onmessage = (ev) => {
      let data
      try {
        data = JSON.parse(ev.data)
      } catch {
        return
      }
      if (data.msg && data.msg !== '__DONE__') {
        setLogs((l) => [...l, data.msg])
      }
      setState((s) => ({
        ...s,
        progress: typeof data.progress === 'number' ? data.progress : s.progress,
        steps: data.steps || s.steps,
      }))
      if (data.msg === '__DONE__') {
        es.close()
        esRef.current = null
        setBusy(false)
        getState()
          .then((snap) => snap && setState((s) => ({ ...s, ...snap })))
          .catch(() => {})
      }
    }

    es.onerror = () => {
      es.close()
      esRef.current = null
      // The install keeps running server-side; fall back to polling.
      getState()
        .then((snap) => snap && setState((s) => ({ ...s, ...snap })))
        .catch(() => {})
    }
  }, [])

  useEffect(() => () => esRef.current && esRef.current.close(), [])

  const beginRun = async (fn) => {
    setBusy(true)
    setError('')
    setState((s) => ({ ...s, error: null, done: false }))
    try {
      await fn()
      setInstalling(true)
      openStream()
    } catch (e) {
      setBusy(false)
      fail(e.message || 'Request failed')
    }
  }

  const handleStart = async () => {
    setLogs([])
    await beginRun(async () => {
      await saveConfig({ ...cfg, admin_id: Number(cfg.admin_id) || 0 })
      await startInstall()
    })
  }

  const handleResume = () => beginRun(resumeInstall)
  const handleRetryStep = () => beginRun(retryStep)
  const handleRetrySsl = () => beginRun(retrySsl)
  const handleRestartClean = () => {
    setLogs([])
    return beginRun(restartClean)
  }

  /* -------------------------------------------------- validation */
  const validate = () => {
    const p = PAGES[page].key
    if (p === 'bot') {
      if (!/^[0-9]{6,}:[A-Za-z0-9_-]{30,}$/.test((cfg.bot_token || '').trim())) {
        fail(tr(T.tokenFormat, fa))
        return false
      }
    }
    if (p === 'admin') {
      if (!/^[0-9]{5,}$/.test(cfg.admin_id || '')) {
        fail(tr(T.adminIdInvalid, fa))
        return false
      }
      if ((cfg.panel_password || '').length < 8) {
        fail(tr(T.passTooShort, fa))
        return false
      }
    }
    return true
  }

  const next = () => {
    setError('')
    if (!validate()) return
    setPage((p) => Math.min(PAGES.length - 1, p + 1))
  }

  const back = () => {
    setError('')
    setPage((p) => Math.max(0, p - 1))
  }

  const meta = installing
    ? {
        icon: Rocket,
        title: state.done && !state.error ? T.doneTitle : T.installTitle,
        sub: T.installSub,
      }
    : { icon: PAGES[page].icon, title: PAGES[page].title, sub: PAGES[page].sub }
  const MetaIcon = meta.icon
  const Back = fa ? ArrowRight : ArrowLeft
  const Fwd = fa ? ArrowLeft : ArrowRight

  return (
    <div className="wizard-page">
      <div className="wizard-glow one" />
      <div className="wizard-glow two" />
      <div className="wizard-grid" />

      <button
        onClick={() => setFa((v) => !v)}
        className="btn-secondary tiny"
        style={{ position: 'fixed', top: 16, insetInlineEnd: 16, zIndex: 5, padding: '6px 12px' }}
      >
        <Languages size={13} />
        {fa ? 'EN' : 'FA'}
      </button>

      <div className="wizard-shell">
        <div className="card animate-slide-up">
          <div className="card-hairline" />

          {/* header */}
          <div className="center" style={{ marginBottom: 22 }}>
            <div
              style={{
                width: 64,
                height: 64,
                margin: '0 auto 14px',
                borderRadius: 18,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, var(--primary), var(--accent))',
                boxShadow: '0 8px 25px var(--primary-50)',
              }}
            >
              <MetaIcon size={30} color="#fff" />
            </div>
            <h1 style={{ margin: 0, fontSize: 20, color: 'var(--text-strong)' }}>
              {tr(meta.title, fa)}
            </h1>
            <p className="tiny muted" style={{ marginTop: 6 }}>
              {tr(meta.sub, fa)}
            </p>
          </div>

          {/* step dots */}
          {!installing ? (
            <div className="row gap-2" style={{ justifyContent: 'center', marginBottom: 22 }}>
              {PAGES.map((p, i) => (
                <span
                  key={p.key}
                  title={tr(p.title, fa)}
                  style={{
                    height: 5,
                    width: i === page ? 26 : 16,
                    borderRadius: 999,
                    transition: 'all 0.3s ease',
                    background:
                      i < page
                        ? 'var(--ok)'
                        : i === page
                          ? 'linear-gradient(90deg, var(--primary), var(--accent))'
                          : 'rgba(255,255,255,0.14)',
                  }}
                />
              ))}
            </div>
          ) : null}

          {error ? (
            <div style={{ marginBottom: 16 }}>
              <Alert kind="error" shakeKey={shakeKey}>
                {error}
              </Alert>
            </div>
          ) : null}

          {/* body */}
          {installing ? (
            <Install
              fa={fa}
              state={state}
              logs={logs}
              busy={busy}
              onRetryStep={handleRetryStep}
              onRetrySsl={handleRetrySsl}
              onResume={handleResume}
              onRestartClean={handleRestartClean}
            />
          ) : (
            <>
              {PAGES[page].key === 'welcome' && (
                <WelcomeStep
                  fa={fa}
                  serverIp={serverIp}
                  resumeAvailable={resumeAvailable}
                  onResume={handleResume}
                />
              )}
              {PAGES[page].key === 'bot' && (
                <BotStep fa={fa} cfg={cfg} set={set} setValid={setTokenVerified} />
              )}
              {PAGES[page].key === 'admin' && <AdminStep fa={fa} cfg={cfg} set={set} />}
              {PAGES[page].key === 'domain' && (
                <DomainStep fa={fa} cfg={cfg} set={set} serverIp={serverIp} />
              )}
              {PAGES[page].key === 'payments' && <PaymentsStep fa={fa} cfg={cfg} set={set} />}
              {PAGES[page].key === 'review' && (
                <ReviewStep fa={fa} cfg={cfg} serverIp={serverIp} />
              )}

              {/* nav */}
              <div className="row between gap-3" style={{ marginTop: 26 }}>
                <button
                  className="btn-ghost"
                  onClick={back}
                  disabled={page === 0}
                  style={{ visibility: page === 0 ? 'hidden' : 'visible' }}
                >
                  <Back size={15} />
                  {tr(T.back, fa)}
                </button>

                {page < PAGES.length - 1 ? (
                  <button className="btn-primary" onClick={next}>
                    {tr(T.next, fa)}
                    <Fwd size={15} />
                  </button>
                ) : (
                  <button className="btn-primary" onClick={handleStart} disabled={busy}>
                    {busy ? <Spinner /> : <Rocket size={16} />}
                    {tr(T.start, fa)}
                  </button>
                )}
              </div>
            </>
          )}
        </div>

        <p className="center tiny muted" style={{ marginTop: 18 }}>
          <span className="row gap-2" style={{ justifyContent: 'center' }}>
            <ShieldCheck size={12} />
            {tr(T.wizardTitle, fa)}
          </span>
        </p>
      </div>
    </div>
  )
}
