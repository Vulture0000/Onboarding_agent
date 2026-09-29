import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { UserPlus, Search, ShieldCheck, TriangleAlert } from 'lucide-react'
import { listEmployees, createEmployee, previewRole, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { Loading, ErrorBox, StatusBadge, PageHeader, Modal } from '../components/ui'

const DEPARTMENTS = ['Engineering', 'Data', 'Design', 'Human Resources', 'Marketing', 'Sales', 'Finance', 'Operations']

const EMPTY = {
  name: '', email: '', role: '', department: 'Engineering', experience: '',
  joining_date: '', login_role: '', login_password: '',
}

const ACCESS_ROLE_TONE = {
  HR: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  MANAGER: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  EMPLOYEE: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
}

export default function Employees() {
  const { data, loading, error, refetch } = useFetch(listEmployees)
  const [q, setQ] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState(null)
  const [created, setCreated] = useState(null)
  // Live preview of the access role the email prefix will grant.
  const [preview, setPreview] = useState(null)

  // Debounced role preview so HR sees the outcome while typing the email.
  useEffect(() => {
    const email = form.email.trim()
    if (!email || !email.includes('@')) { setPreview(null); return }
    const t = setTimeout(() => {
      previewRole(email).then(setPreview).catch(() => setPreview(null))
    }, 300)
    return () => clearTimeout(t)
  }, [form.email])

  const closeForm = () => {
    setShowForm(false); setForm(EMPTY); setFormError(null); setPreview(null)
  }

  const submit = async e => {
    e.preventDefault()
    setSaving(true); setFormError(null)
    try {
      const result = await createEmployee({
        ...form,
        joining_date: form.joining_date || undefined,
        login_role: form.login_role || undefined,
        login_password: form.login_password || undefined,
      })
      closeForm()
      setCreated(result)
      refetch()
    } catch (err) { setFormError(errMsg(err)) }
    finally { setSaving(false) }
  }

  const filtered = (data || []).filter(e =>
    [e.name, e.email, e.role, e.department, e.id].some(v => (v || '').toLowerCase().includes(q.toLowerCase()))
  )

  return (
    <div>
      <PageHeader
        title="Employees"
        subtitle="All employee profiles managed by the onboarding agents"
        actions={
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <UserPlus size={16} /> Add Employee
          </button>
        }
      />

      <div className="relative mb-4 max-w-sm">
        <Search size={16} className="absolute left-3 top-2.5 text-gray-500" />
        <input className="input pl-9" placeholder="Search employees…" value={q} onChange={e => setQ(e.target.value)} />
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {data && (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-edge">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Role</th>
                <th className="px-5 py-3">Department</th>
                <th className="px-5 py-3">Joining</th>
                <th className="px-5 py-3">Manager</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(e => (
                <tr key={e.id} className="border-b border-edge/50 hover:bg-panel/60 transition-colors">
                  <td className="px-5 py-3 font-mono text-xs text-gray-400">{e.id}</td>
                  <td className="px-5 py-3">
                    <Link to={`/employees/${e.id}`} className="text-indigo-300 hover:text-indigo-200 font-medium">
                      {e.name}
                    </Link>
                    <div className="text-xs text-gray-500">{e.email}</div>
                  </td>
                  <td className="px-5 py-3 text-gray-300">{e.role || '—'}</td>
                  <td className="px-5 py-3 text-gray-300">{e.department || '—'}</td>
                  <td className="px-5 py-3 text-gray-300">{e.joining_date}</td>
                  <td className="px-5 py-3 text-gray-300">{e.manager || '—'}</td>
                  <td className="px-5 py-3"><StatusBadge status={e.status} /></td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-10 text-center text-gray-500">No employees match your search.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={showForm} onClose={closeForm} title="Add Employee">
        <form onSubmit={submit} className="space-y-3">
          {formError && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-2">{formError}</div>}
          <div><label className="label">Full name *</label>
            <input required className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div><label className="label">Email *</label>
            <input required type="email" className="input" value={form.email}
              placeholder="employee1042@xyzcorp.com"
              onChange={e => setForm({ ...form, email: e.target.value })} />
            <p className="text-xs text-gray-500 mt-1">
              The text before the employee id sets their access: <code className="text-gray-400">hr</code>, <code className="text-gray-400">manage</code>, <code className="text-gray-400">employee</code>, and similar.
            </p></div>

          {preview && !form.login_role && (
            <div className={`flex items-start gap-2 rounded-lg border p-2.5 text-sm ${
              preview.recognized
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
                : 'border-amber-500/30 bg-amber-500/10 text-amber-200'
            }`}>
              {preview.recognized
                ? <ShieldCheck size={16} className="mt-0.5 shrink-0" />
                : <TriangleAlert size={16} className="mt-0.5 shrink-0" />}
              <div>
                <div className="font-medium">
                  Login <span className="font-mono">{preview.email}</span> will be created as{' '}
                  <span className="font-semibold">{preview.role}</span>
                </div>
                <div className="text-xs opacity-80 mt-0.5">{preview.reason}</div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Job title</label>
              <input className="input" placeholder="Software Engineer" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} /></div>
            <div><label className="label">Department</label>
              <select className="input" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })}>
                {DEPARTMENTS.map(d => <option key={d}>{d}</option>)}
              </select></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Experience</label>
              <input className="input" placeholder="Fresher / 3 years" value={form.experience} onChange={e => setForm({ ...form, experience: e.target.value })} /></div>
            <div><label className="label">Joining date</label>
              <input type="date" className="input" value={form.joining_date} onChange={e => setForm({ ...form, joining_date: e.target.value })} /></div>
          </div>

          <details className="rounded-lg border border-edge p-2.5">
            <summary className="text-sm text-gray-300 cursor-pointer select-none">
              Access role override {form.login_role && <span className="text-amber-300">({form.login_role})</span>}
            </summary>
            <div className="mt-2.5 space-y-3">
              <div>
                <label className="label">Access role</label>
                <select className="input" value={form.login_role} onChange={e => setForm({ ...form, login_role: e.target.value })}>
                  <option value="">Use the email prefix {preview && `(${preview.role})`}</option>
                  <option value="EMPLOYEE">EMPLOYEE</option>
                  <option value="MANAGER">MANAGER</option>
                  <option value="HR">HR</option>
                </select>
              </div>
              <div>
                <label className="label">Initial password</label>
                <input type="password" className="input" placeholder="Leave blank to use the demo password"
                  value={form.login_password} onChange={e => setForm({ ...form, login_password: e.target.value })} />
                <p className="text-xs text-gray-500 mt-1">Minimum 8 characters.</p>
              </div>
            </div>
          </details>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={closeForm}>Cancel</button>
            <button className="btn-primary" disabled={saving || (preview && !preview.recognized && !form.login_role)}>
              {saving ? 'Saving…' : 'Create Employee'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal open={!!created} onClose={() => setCreated(null)} title="Employee created">
        {created && (
          <div className="space-y-3 text-sm">
            <p className="text-gray-300">
              <span className="font-medium text-white">{created.name}</span> ({created.id}) can now sign in as{' '}
              <span className={`inline-block align-middle px-1.5 py-0.5 rounded border text-xs font-semibold ${ACCESS_ROLE_TONE[created.login_role]}`}>
                {created.login_role}
              </span>
            </p>
            <dl className="space-y-1.5 text-xs">
              <div className="flex justify-between gap-4">
                <dt className="text-gray-500">Email</dt>
                <dd className="font-mono text-gray-300">{created.login_email}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-gray-500">Role determined by</dt>
                <dd className="text-gray-300">{created.role_source === 'explicit' ? 'manual override' : 'email prefix'}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-gray-500">Password</dt>
                <dd className="font-mono text-gray-300">{created.default_password ? 'Demo@1234' : 'custom'}</dd>
              </div>
            </dl>
            <p className="text-xs text-gray-500">Share the credentials with the new user. They can sign in immediately.</p>
            <div className="flex justify-end pt-1">
              <button className="btn-primary" onClick={() => setCreated(null)}>Done</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
