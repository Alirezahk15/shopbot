export default function ProgressBar({ value }) {
  const pct = Math.max(0, Math.min(100, Math.round(value || 0)))
  return (
    <div>
      <div
        style={{
          position: 'relative',
          height: 10,
          borderRadius: 999,
          overflow: 'hidden',
          background: 'rgba(255,255,255,0.07)',
          border: '1px solid var(--line)',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            borderRadius: 999,
            transition: 'width 0.5s cubic-bezier(0.4,0,0.2,1)',
            background: 'linear-gradient(90deg, var(--primary), var(--accent))',
            boxShadow: '0 0 18px var(--primary-50)',
          }}
        />
        {pct > 0 && pct < 100 ? (
          <div
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              width: '35%',
              background:
                'linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent)',
              animation: 'shine 1.8s linear infinite',
            }}
          />
        ) : null}
      </div>
      <div className="row between tiny muted" style={{ marginTop: 6 }}>
        <span className="mono">{pct}%</span>
      </div>
    </div>
  )
}
