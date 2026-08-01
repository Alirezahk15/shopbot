import { useEffect, useRef, useState } from 'react'
import { Terminal, Copy, CheckCheck } from 'lucide-react'
import { T, tr } from '../i18n.js'

export default function LogConsole({ lines, fa }) {
  const boxRef = useRef(null)
  const [copied, setCopied] = useState(false)
  const [stick, setStick] = useState(true)

  useEffect(() => {
    const el = boxRef.current
    if (el && stick) el.scrollTop = el.scrollHeight
  }, [lines, stick])

  const onScroll = () => {
    const el = boxRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setStick(atBottom)
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(lines.join('\n'))
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* clipboard blocked over plain http - ignore */
    }
  }

  return (
    <div>
      <div className="row between" style={{ marginBottom: 8 }}>
        <span className="row gap-2 small strong">
          <Terminal size={14} />
          {tr(T.logs, fa)}
        </span>
        <button type="button" className="btn-ghost tiny" onClick={copy}>
          {copied ? <CheckCheck size={13} /> : <Copy size={13} />}
          {copied ? tr(T.copied, fa) : tr(T.copyLog, fa)}
        </button>
      </div>

      <div
        ref={boxRef}
        onScroll={onScroll}
        dir="ltr"
        className="mono"
        style={{
          height: 260,
          overflowY: 'auto',
          background: 'rgba(0,0,0,0.45)',
          border: '1px solid var(--line)',
          borderRadius: 12,
          padding: '12px 14px',
          fontSize: 12,
          lineHeight: 1.75,
          textAlign: 'left',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {lines.length === 0 ? (
          <span className="muted">Waiting for output...</span>
        ) : (
          lines.map((line, i) => {
            let color = 'var(--text)'
            if (line.startsWith('====')) color = 'var(--primary)'
            else if (/^(ERROR|FAILED)/i.test(line)) color = 'var(--err)'
            else if (/^(OK|DONE|SUCCESS)/i.test(line)) color = 'var(--ok)'
            else if (/^(WARN|WARNING|\.\.\.)/i.test(line)) color = 'var(--warn)'
            return (
              <div key={i} style={{ color }}>
                {line}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
