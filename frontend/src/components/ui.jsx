import { AlertTriangle, CheckCircle2, XCircle, Clock, Loader2, Info } from 'lucide-react'

export function StatusBadge({ status }) {
  const map = {
    TODO: 'bg-gray-500/15 text-gray-300 border-gray-500/30',
    IN_PROGRESS: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
    COMPLETED: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    OVERDUE: 'bg-red-500/15 text-red-300 border-red-500/30',
    PENDING: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    APPROVED: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    REJECTED: 'bg-red-500/15 text-red-300 border-red-500/30',
    SCHEDULED: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
    CANCELLED: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
    ONBOARDING: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
    ACTIVE: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    HIGH: 'bg-red-500/15 text-red-300 border-red-500/30',
    MEDIUM: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    LOW: 'bg-gray-500/15 text-gray-300 border-gray-500/30',
    completed: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    warning: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    error: 'bg-red-500/15 text-red-300 border-red-500/30',
  }
  const cls = map[status] || 'bg-gray-500/15 text-gray-300 border-gray-500/30'
  return (
    <span className={`badge border ${cls}`}>
      {status === 'COMPLETED' || status === 'APPROVED' || status === 'completed' ? <CheckCircle2 size={12} /> : null}
      {status === 'PENDING' || status === 'warning' || status === 'OVERDUE' ? <AlertTriangle size={12} /> : null}
      {status === 'REJECTED' || status === 'error' ? <XCircle size={12} /> : null}
      {status === 'IN_PROGRESS' || status === 'SCHEDULED' ? <Clock size={12} /> : null}
      {String(status).replaceAll('_', ' ')}
    </span>
  )
}

export function ProgressBar({ pct }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-panel rounded-full overflow-hidden border border-edge">
        <div
          className="h-full bg-gradient-to-r from-accent to-accent2 rounded-full"
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-9 text-right">{pct}%</span>
    </div>
  )
}

export function Loading() {
  return (
    <div className="flex items-center justify-center py-16 text-gray-500">
      <Loader2 className="animate-spin mr-2" size={20} /> Loading…
    </div>
  )
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="card border-red-500/40 bg-red-500/5 flex items-start gap-3 text-red-300">
      <AlertTriangle size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1">
        <div className="font-medium text-sm">Something went wrong</div>
        <div className="text-sm text-red-300/80 mt-1">{message}</div>
        {onRetry && (
          <button onClick={onRetry} className="btn-ghost mt-3 !py-1.5 text-xs">Retry</button>
        )}
      </div>
    </div>
  )
}

export function Empty({ icon: Icon = Info, title, hint }) {
  return (
    <div className="card flex flex-col items-center justify-center py-14 text-center">
      <Icon size={32} className="text-gray-600 mb-3" />
      <div className="text-gray-300 font-medium">{title}</div>
      {hint && <div className="text-sm text-gray-500 mt-1">{hint}</div>}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-gray-400 mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  )
}

export function Modal({ open, onClose, title, children, wide }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className={`relative bg-card border border-edge rounded-2xl shadow-2xl w-full ${wide ? 'max-w-2xl' : 'max-w-md'} max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-edge sticky top-0 bg-card rounded-t-2xl">
          <h3 className="font-semibold text-white">{title}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-xl leading-none">×</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export function StatCard({ icon: Icon, label, value, sub, color = 'text-indigo-400' }) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`w-11 h-11 rounded-xl bg-panel border border-edge flex items-center justify-center ${color}`}>
        <Icon size={20} />
      </div>
      <div>
        <div className="text-2xl font-bold text-white leading-none">{value}</div>
        <div className="text-xs text-gray-400 mt-1">{label}</div>
        {sub && <div className="text-[11px] text-gray-500">{sub}</div>}
      </div>
    </div>
  )
}
