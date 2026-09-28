import { Link } from 'react-router-dom'
import { useState } from 'react'
import { UserPlus, Search } from 'lucide-react'
import { listEmployees, createEmployee, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { Loading, ErrorBox, StatusBadge, PageHeader, Modal } from '../components/ui'

const DEPARTMENTS = ['Engineering', 'Data', 'Design', 'Human Resources', 'Marketing', 'Sales', 'Finance', 'Operations']

export default function Employees() {
  const { data, loading, error, refetch } = useFetch(listEmployees)
  const [q, setQ] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', role: '', department: 'Engineering', experience: '', joining_date: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState(null)

  const submit = async e => {
    e.preventDefault()
    setSaving(true); setFormError(null)
    try {
      await createEmployee({ ...form, joining_date: form.joining_date || undefined })
      setShowForm(false)
      setForm({ name: '', email: '', role: '', department: 'Engineering', experience: '', joining_date: '' })
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

      <Modal open={showForm} onClose={() => setShowForm(false)} title="Add Employee">
        <form onSubmit={submit} className="space-y-3">
          {formError && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-2">{formError}</div>}
          <div><label className="label">Full name *</label>
            <input required className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div><label className="label">Email *</label>
            <input required type="email" className="input" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Role</label>
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
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
            <button className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Create Employee'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
