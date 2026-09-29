import { useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { Bot, UserPlus, Loader2, ArrowLeft } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { errMsg } from '../services/api'

export default function Signup() {
  const { user, signUp } = useAuth()
  const location = useLocation()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={location.state?.from || '/'} replace />

  const set = k => e => setForm({ ...form, [k]: e.target.value })

  const submit = async e => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await signUp({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
      })
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-panel">
      <div className="w-full max-w-md">
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

          <h1 className="text-xl font-semibold text-white mb-1">Create your account</h1>
          <p className="text-sm text-gray-400 mb-6">
            Register to get your onboarding plan, tasks and meetings. If HR has already
            added you, signing up here links your login to that record.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label">Full name</label>
              <input
                required
                minLength={2}
                autoComplete="name"
                value={form.name}
                onChange={set('name')}
                placeholder="Arun Kumar"
                className="input"
              />
            </div>
            <div>
              <label className="label">Work email</label>
              <input
                type="email"
                required
                autoComplete="username"
                value={form.email}
                onChange={set('email')}
                placeholder="you@xyzcorp.com"
                className="input"
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={form.password}
                onChange={set('password')}
                placeholder="At least 8 characters"
                className="input"
              />
            </div>
            <div>
              <label className="label">Confirm password</label>
              <input
                type="password"
                required
                autoComplete="new-password"
                value={form.confirm}
                onChange={set('confirm')}
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
              {busy ? <Loader2 size={16} className="animate-spin" /> : <UserPlus size={16} />}
              {busy ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <div className="mt-4 rounded-lg border border-edge bg-panel/60 p-3">
            <p className="text-[11px] text-gray-400">
              New accounts start as <span className="text-gray-200 font-medium">Employee</span>. Manager
              and HR access is granted by HR after you register — it cannot be self-selected.
            </p>
          </div>

          <Link
            to="/login"
            className="mt-4 flex items-center justify-center gap-1.5 text-xs text-gray-400 hover:text-gray-200"
          >
            <ArrowLeft size={13} /> Already have an account? Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
