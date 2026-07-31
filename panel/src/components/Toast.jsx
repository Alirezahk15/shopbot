import { createContext, useContext, useState, useCallback } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react'

const ToastContext = createContext()

let toastId = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'success', duration = 3500) => {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message, type, duration }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, duration)
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      {/* Toast container */}
      <div
        className="fixed z-[9999] flex flex-col gap-2"
        style={{ top: '20px', insetInlineEnd: '20px', maxWidth: '360px', width: '100%' }}
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({ toast, onRemove }) {
  const configs = {
    success: {
      icon: CheckCircle,
      bg: 'rgba(16,185,129,0.12)',
      border: 'rgba(16,185,129,0.3)',
      iconColor: '#10b981',
      barColor: '#10b981',
    },
    error: {
      icon: XCircle,
      bg: 'rgba(239,68,68,0.12)',
      border: 'rgba(239,68,68,0.3)',
      iconColor: '#ef4444',
      barColor: '#ef4444',
    },
    warning: {
      icon: AlertTriangle,
      bg: 'rgba(245,158,11,0.12)',
      border: 'rgba(245,158,11,0.3)',
      iconColor: '#f59e0b',
      barColor: '#f59e0b',
    },
    info: {
      icon: Info,
      bg: 'rgba(99,102,241,0.12)',
      border: 'rgba(99,102,241,0.3)',
      iconColor: '#6366f1',
      barColor: '#6366f1',
    },
  }

  const cfg = configs[toast.type] || configs.info
  const Icon = cfg.icon

  return (
    <div
      className="relative overflow-hidden rounded-xl flex items-start gap-3 px-4 py-3 shadow-2xl"
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        backdropFilter: 'blur(20px)',
        animation: 'slideInToast 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
      }}
    >
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: cfg.iconColor }} />
      <p className="text-sm text-white flex-1 leading-relaxed">{toast.message}</p>
      <button
        onClick={() => onRemove(toast.id)}
        className="flex-shrink-0 text-gray-500 hover:text-gray-300 transition-colors p-0.5"
      >
        <X className="w-3.5 h-3.5" />
      </button>
      {/* Progress bar */}
      <div
        className="absolute bottom-0 start-0 h-0.5 rounded-full"
        style={{
          background: cfg.barColor,
          animation: `toastProgress ${toast.duration || 3500}ms linear forwards`,
          width: '100%',
        }}
      />
    </div>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
