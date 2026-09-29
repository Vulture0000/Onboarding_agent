import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Bot, LogIn, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { errMsg } from '../services/api'

const DEMO_ACCOUNTS = [
  {
    email: 'employee1021@xyzcorp.com',
    role: 'EMPLOYEE',
    who: 'Arun Kumar · Software Engineer',
    can: 'Sees only his own tasks, meetings and leave',
  },
  {
    email: 'manage1234@xyzcorp.com',
    role: 'MANAGER',
    who: 'Priya Sharma · Engineering Manager',
    can: 'Sees her team, approves their leave',
  },
  {
    email: 'hr1000@xyzcorp.com',
    role: 'HR',
    who: 'Meera Iyer · HR Executive',
    can: 'Sees everything, uploads resumes',
  },
]

const ROLE_STYLE = {
  EMPLOYEE: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  MANAGER: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  HR: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
}

export default function Login() {
  const { user, signIn } = useAuth()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={location.state?.from || '/'} replace />

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(email.trim(), password)
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-panel">
      <div className="w-full max-w-5xl grid lg:grid-cols-2 gap-8 items-center">
        <div className="card p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-xl bg-accent/20 border border-accent/40 flex items-center justify-center">
              <Bot size={22} className="text-indigo-400" />
            </div>
            <div>
              <div className="font-bold tracking-wide text-white text-lg leading-tight">ONBOARD AI</div>
              <div className="text-[10px] text-gray-500 uppercase tracking-widest">Agentic HR Ops</div>
            </div>
          </div>

          <h1 className="text-xl font-semibold text-white mb-1">Sign in</h1>
          <p className="text-sm text-gray-400 mb-6">
            Access is scoped to your role. Pick an account on the right to try it.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@xyzcorp.com"
                className="input"
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="input"
              />
            </div>

            {error && (
              <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button type="submit" disabled={busy} className="btn-primary w-full justify-center">
              {busy ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
          <p className="text-[11px] text-gray-500 mt-4">
            Demo password for every account: <code className="text-gray-400">Demo@1234</code>
          </p>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Demo accounts</h2>
          {DEMO_ACCOUNTS.map(a => (
            <button
              key={a.email}
              type="button"
              onClick={() => { setEmail(a.email); setPassword('Demo@1234'); setError(null) }}
              className="card w-full text-left hover:border-accent/50 transition-colors p-4"
            >
              <div className="flex items-center justify-between gap-3 mb-1">
                <code className="text-sm text-white">{a.email}</code>
                <span className={`badge border ${ROLE_STYLE[a.role]}`}>{a.role}</span>
              </div>
              <div className="text-xs text-gray-400">{a.who}</div>
              <div className="text-xs text-gray-500 mt-1">{a.can}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}