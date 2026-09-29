import { useMemo, useState } from 'react'
import { CalendarPlus, CalendarDays, XCircle, CalendarClock } from 'lucide-react'
import { listMeetings, listEmployees, getTeam, createMeeting, updateMeeting, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useAuth } from '../context/AuthContext'
import { Loading, ErrorBox, StatusBadge, Empty, PageHeader, Modal } from '../components/ui'

export default function CalendarPage() {
  const { isHR } = useAuth()
  // HR picks any employee; a manager picks from their own team.
  const { data: hrEmployees } = useFetch(listEmployees, [], { enabled: isHR })
  const { data: team } = useFetch(getTeam, [], { enabled: !isHR })
  const { data: meetings, loading, error, refetch } = useFetch(() => listMeetings(), [])
  const [showNew, setShowNew] = useState(false)
  const [resched, setResched] = useState(null)
  const [form, setForm] = useState({ employee_id: '', title: '', date: '', start_time: '', end_time: '' })
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState(null)

  const employees = useMemo(
    () => (isHR ? hrEmployees || [] : team || []),
    [isHR, hrEmployees, team],
  )

  const submitNew = async e => {
    e.preventDefault()
    setBusy(true); setFormError(null)
    try {
      await createMeeting({
        employee_id: form.employee_id,
        title: form.title,
        date: form.date,
        start_time: form.start_time || undefined,
        end_time: form.end_time || undefined,
      })
      setShowNew(false)
      setForm({ employee_id: '', title: '', date: '', start_time: '', end_time: '' })
      refetch()
    } catch (err) { setFormError(errMsg(err)) }
    finally { setBusy(false) }
  }

  const submitResched = async e => {
    e.preventDefault()
    setBusy(true); setFormError(null)
    try {
      await updateMeeting(resched.id, {
        date: form.date || undefined,
        start_time: form.start_time || undefined,
        end_time: form.end_time || undefined,
      })
      setResched(null)
      refetch()
    } catch (err) { setFormError(errMsg(err)) }
    finally { setBusy(false) }
  }

  const cancel = async m => {
    if (!confirm(`Cancel "${m.title}" for ${m.employee_name}?`)) return
    try { await updateMeeting(m.id, { status: 'CANCELLED' }); refetch() }
    catch (e) { alert(errMsg(e)) }
  }

  const active = (meetings || []).filter(m => m.status !== 'CANCELLED')
  const cancelled = (meetings || []).filter(m => m.status === 'CANCELLED')

  return (
    <div>
      <PageHeader
        title="Calendar"
        subtitle="Onboarding meetings scheduled by the Calendar Agent (mock provider — swappable for Google Calendar)"
        actions={
          <button className="btn-primary" onClick={() => { setShowNew(true); setFormError(null) }}>
            <CalendarPlus size={16} /> Schedule Meeting
          </button>
        }
      />

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {meetings && active.length === 0 && (
        <Empty icon={CalendarDays} title="No meetings scheduled" hint="Schedule one, or upload a resume to auto-generate the onboarding meeting set." />
      )}

      {active.length > 0 && (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-edge">
                <th className="px-5 py-3">Meeting</th>
                <th className="px-5 py-3">Employee</th>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Time</th>
                <th className="px-5 py-3">Participants</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {active.map(m => (
                <tr key={m.id} className="border-b border-edge/50 hover:bg-panel/60">
                  <td className="px-5 py-3 text-white font-medium">{m.title}</td>
                  <td className="px-5 py-3 text-gray-300">{m.employee_name}</td>
                  <td className="px-5 py-3 text-gray-300 whitespace-nowrap">{m.date}</td>
                  <td className="px-5 py-3 font-mono text-xs text-gray-300">{m.start_time}–{m.end_time}</td>
                  <td className="px-5 py-3 text-gray-400 text-xs max-w-[200px] truncate">{(m.participants || []).join(', ')}</td>
                  <td className="px-5 py-3"><StatusBadge status={m.status} /></td>
                  <td className="px-5 py-3">
                    <div className="flex justify-end gap-1">
                      <button className="btn-ghost !px-2 !py-1" title="Reschedule"
                              onClick={() => { setResched(m); setForm({ date: m.date, start_time: m.start_time, end_time: m.end_time }); setFormError(null) }}>
                        <CalendarClock size={14} />
                      </button>
                      <button className="btn-ghost !px-2 !py-1 text-red-400" title="Cancel meeting" onClick={() => cancel(m)}>
                        <XCircle size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {cancelled.length > 0 && (
        <>
          <h2 className="font-semibold text-gray-400 mt-8 mb-3 text-sm uppercase tracking-wide">Cancelled</h2>
          <div className="space-y-2">
            {cancelled.map(m => (
              <div key={m.id} className="card !py-3 flex items-center gap-3 text-sm text-gray-500">
                <XCircle size={14} />
                <span className="line-through">{m.title}</span>
                <span className="text-xs">{m.employee_name} · {m.date} {m.start_time}</span>
              </div>
            ))}
          </div>
        </>
      )}

      <Modal open={showNew} onClose={() => setShowNew(false)} title="Schedule Meeting">
        <form onSubmit={submitNew} className="space-y-3">
          {formError && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-2">{formError}</div>}
          <div><label className="label">Employee *</label>
            <select required className="input" value={form.employee_id} onChange={e => setForm({ ...form, employee_id: e.target.value })}>
              <option value="">Select employee…</option>
              {(employees || []).map(e => <option key={e.id} value={e.id}>{e.name} ({e.id})</option>)}
            </select></div>
          <div><label className="label">Title *</label>
            <input required className="input" placeholder="e.g. Design System Walkthrough" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></div>
          <div><label className="label">Date *</label>
            <input required type="date" className="input" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Start (optional)</label>
              <input type="time" className="input" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })} /></div>
            <div><label className="label">End (optional)</label>
              <input type="time" className="input" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })} /></div>
          </div>
          <p className="text-xs text-gray-500">Leave times empty and the Calendar Agent will find an available slot automatically.</p>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={() => setShowNew(false)}>Cancel</button>
            <button className="btn-primary" disabled={busy}>{busy ? 'Scheduling…' : 'Schedule'}</button>
          </div>
        </form>
      </Modal>

      <Modal open={!!resched} onClose={() => setResched(null)} title={`Reschedule: ${resched?.title || ''}`}>
        <form onSubmit={submitResched} className="space-y-3">
          {formError && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-2">{formError}</div>}
          <div><label className="label">New date</label>
            <input type="date" className="input" value={form.date || ''} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Start</label>
              <input type="time" className="input" value={form.start_time || ''} onChange={e => setForm({ ...form, start_time: e.target.value })} /></div>
            <div><label className="label">End</label>
              <input type="time" className="input" value={form.end_time || ''} onChange={e => setForm({ ...form, end_time: e.target.value })} /></div>
          </div>
          <p className="text-xs text-gray-500">Availability is checked by the Calendar Agent (work hours 09:00–18:00, lunch 13:00–14:00, weekends blocked).</p>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={() => setResched(null)}>Close</button>
            <button className="btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Reschedule'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
