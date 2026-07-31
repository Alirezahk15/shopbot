import { AlertTriangle, X } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'

/**
 * Usage:
 * const [confirm, setConfirm] = useState(null)
 * 
 * // Trigger:
 * setConfirm({
 *   title: 'حذف کاربر',
 *   message: 'آیا مطمئن هستید؟',
 *   type: 'danger',  // 'danger' | 'warning' | 'info'
 *   onConfirm: () => doSomething(),
 * })
 * 
 * // Render:
 * {confirm && <ConfirmModal {...confirm} onClose={() => setConfirm(null)} />}
 */
export default function ConfirmModal({ title, message, type = 'danger', onConfirm, onClose, confirmText, cancelText }) {
  const { lang } = useApp()

  const configs = {
    danger: {
      iconBg: 'rgba(239,68,68,0.1)',
      iconBorder: 'rgba(239,68,68,0.2)',
      iconColor: '#ef4444',
      btnClass: 'btn-danger',
    },
    warning: {
      iconBg: 'rgba(245,158,11,0.1)',
      iconBorder: 'rgba(245,158,11,0.2)',
      iconColor: '#f59e0b',
      btnClass: 'btn-warning',
    },
    info: {
      iconBg: 'rgba(99,102,241,0.1)',
      iconBorder: 'rgba(99,102,241,0.2)',
      iconColor: '#6366f1',
      btnClass: 'btn-primary',
    },
  }

  const cfg = configs[type] || configs.danger

  const handleConfirm = () => {
    onConfirm()
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-[9998] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', animation: 'fadeIn 0.15s ease' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-sm rounded-2xl p-6"
        style={{
          background: 'var(--surface-strong, #1a1a2e)',
          border: '1px solid var(--border-soft, rgba(99,102,241,0.2))',
          boxShadow: 'var(--shadow-modal, 0 25px 50px rgba(0,0,0,0.5))',
          animation: 'slideUp 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: cfg.iconBg, border: `1px solid ${cfg.iconBorder}` }}
            >
              <AlertTriangle className="w-5 h-5" style={{ color: cfg.iconColor }} />
            </div>
            <h3 className="font-bold text-base" style={{ color: 'var(--text-strong, #ffffff)' }}>{title}</h3>
          </div>
          <button onClick={onClose} className="action-btn action-neutral">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Message */}
        <p className="text-sm mb-6 leading-relaxed" style={{ color: 'var(--text-dim, rgba(156,163,175,0.9))' }}>{message}</p>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleConfirm}
            className={`${cfg.btnClass} flex-1 py-2.5`}
          >
            {confirmText || (lang === 'fa' ? 'بله، مطمئنم' : 'Yes, confirm')}
          </button>
          <button
            onClick={onClose}
            className="btn-secondary flex-1 py-2.5"
          >
            {cancelText || (lang === 'fa' ? 'انصراف' : 'Cancel')}
          </button>
        </div>
      </div>
    </div>
  )
}
