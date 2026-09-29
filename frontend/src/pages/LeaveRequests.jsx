import { useMemo, useState } from 'react'
import { Plane, Plus, Check, X } from 'lucide-react'
import {
  listLeave, listBalances, listEmployees, getTeam, createLeave, approveLeave, rejectLeave, errMsg,
} from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useAuth } from '../context/AuthContext'
import { Loading, ErrorBox, StatusBadge, Empty, PageHeader, Modal } from '../components/ui'

export default function LeaveRequests() {
  const { isHR } = useAuth()
  // HR picks from the whole company; a manager picks from their own team only.
  const { data: hrEmployees } = useFetch(listEmployees, [], { enabled: isHR })
  const { data: team } = useFetch(getTeam, [], { enabled: !isHR })
  const { data: leaves, loading, error, refetch } = useFetch(() => listLeave(), [])
  const { data: balances, refetch: refetchBal } = useFetch(() => listBalances(), [])
  const [showNew, setShowNew] = useState(false)
  const [form, setForm] = useState({ employee_id: '', leave_type: 'CASUAL', start_date: '', end_date: '', reason: '' })
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState(null)

  const employees = useMemo(
    () => (isHR ? hrEmployees || [] : team || []),
    [isHR, hrEmployees, team],
  )
  const empName = id =>
    (leaves || []).find(l => l.employee_id === id)?.employee_name ||
    employees.find(e => e.id === id)?.name ||
    id

  const submit = async e => {
    e.preventDefault()
    setBusy(true); setFormError(null)
    try {
      await createLeave(form)
      setShowNew(false)
      setForm({ employee_id: '', leave_type: 'CASUAL', start_date: '', end_date: '', reason: '' })
      refetch(); refetchBal()
    } catch (err) { setFormError(errMsg(err)) }
    finally { setBusy(false) }
  }

  const decide = async (id, approve) => {
    try {
      await (approve ? approveLeave(id) : rejectLeave(id))
      refetch(); refetchBal()
    } catch (e) { alert(errMsg(e)) }
  }

  const pending = (leaves || []).filter(l => l.status === 'PENDING')
  const decided = (leaves || []).filter(l => l.status !== 'PENDING')

  return (
    <div>
      <PageHeader
        title={isHR ? 'Leave Requests' : 'Leave Approvals'}
        subtitle={
          isHR
            ? 'Every leave request in the company. Approvals stay human — the agents only advise.'
            : 'Leave requests from your direct reports. You can approve or reject only your own team.'
        }
        actions={
          <button className="btn-primary" onClick={() => { setShowNew(true); setFormError(null) }}>
            <Plus size={16} /> New Request
          </button>
        }
      />

      {/* Leave balances */}
      {balances && balances.length > 0 && (
        <div className="card mb-4">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">Leave Balances (remaining)</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
            {(employees || []).map(e => {
              const bs = balances.filter(b => b.employee_id === e.id)
              return (
                <div key={e.id} className="bg-panel border border-edge rounded-lg p-3">
                  <div className="text-xs text-gray-400 truncate mb-2">{e.name}</div>
                  <div className="flex gap-3 text-sm">
                    {bs.map(b => (
                      <div key={b.id} className="text-center">
                        <div className="font-bold text-white">{b.remaining_days}</div>
                        <div className="text-[10px] text-gray-500 uppercase">{b.leave_type.slice(0, 2)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}

      {pending.length > 0 && (
        <>
          <h2 className="font-semibold text-white mb-3">Awaiting Approval ({pending.length})</h2>
          <div className="grid md:grid-cols-2 gap-4 mb-8">
            {pending.map(l => (
              <div key={l.id} className="card border-amber-500/30">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-white">{empName(l.employee_id)} <span className="text-gray-500 font-normal text-xs">{l.employee_id}</span></div>
                    <div className="text-sm text-indigo-300 mt-0.5">{l.leave_type} Leave · {l.days} day(s)</div>
                    <div className="text-sm text-gray-300">{l.start_date} → {l.end_date}</div>
                    <div className="text-sm text-gray-400 mt-1 italic">“{l.reason || 'No reason given'}”</div>
                  </div>
                  <StatusBadge status={l.status} />
                </div>
                {l.agent_notes && (
                  <div className="mt-3 text-xs text-gray-500 bg-panel border border-edge rounded-lg p-2">
                    <span className="text-indigo-400 font-medium">LeaveAgent: </span>{l.agent_notes}
                  </div>
                )}
                {l.requires_approval ? (
                  <div className="flex gap-2 mt-4">
                    <button className="btn-success flex-1 justify-center" onClick={() => decide(l.id, true)}><Check size={15} /> Approve</button>
                    <button className="btn-danger flex-1 justify-center" onClick={() => decide(l.id, false)}><X size={15} /> Reject</button>
                  </div>
                ) : (
                  <div className="text-xs text-gray-500 mt-3">Auto-decision pending</div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {leaves && leaves.length === 0 && (
        <Empty icon={Plane} title="No leave requests yet" hint="Create one — the Leave Agent will validate dates, balance and policy automatically." />
      )}

      {decided.length > 0 && (
        <>
          <h2 className="font-semibold text-white mb-3">History</h2>
          <div className="card p-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-edge">
                  <th className="px-5 py-3">Employee</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3">Dates</th>
                  <th className="px-5 py-3">Days</th>
                  <th className="px-5 py-3">Reason</th>
                  <th className="px-5 py-3">Decided by</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {decided.map(l => (
                  <tr key={l.id} className="border-b border-edge/50 hover:bg-panel/60">
                    <td className="px-5 py-3 text-gray-200">{empName(l.employee_id)}</td>
                    <td className="px-5 py-3 text-gray-300">{l.leave_type}</td>
                    <td className="px-5 py-3 text-gray-300 whitespace-nowrap">{l.start_date} → {l.end_date}</td>
                    <td className="px-5 py-3 text-gray-300">{l.days}</td>
                    <td className="px-5 py-3 text-gray-400 max-w-[220px] truncate">{l.reason}</td>
                    <td className="px-5 py-3 text-gray-400">{l.decided_by || '—'}</td>
                    <td className="px-5 py-3"><StatusBadge status={l.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <Modal open={showNew} onClose={() => setShowNew(false)} title="New Leave Request">
        <form onSubmit={submit} className="space-y-3">
          {formError && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-2">{formError}</div>}
          {agentMsgs && <div className="text-sm text-gray-300 bg-panel border border-edge rounded-lg p-2">{agentMsgs}</div>}
          <div><label className="label">Employee *</label>
            <select required className="input" value={form.employee_id} onChange={e => setForm({ ...form, employee_id: e.target.value })}>
              <option value="">Select employee…</option>
              {(employees || []).map(e => <option key={e.id} value={e.id}>{e.name} ({e.id})</option>)}
            </select></div>
          <div><label className="label">Leave type *</label>
            <select className="input" value={form.leave_type} onChange={e => setForm({ ...form, leave_type: e.target.value })}>
              <option>CASUAL</option><option>SICK</option><option>EARNED</option>
            </select></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Start *</label>
              <input required type="date" className="input" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} /></div>
            <div><label className="label">End *</label>
              <input required type="date" className="input" value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} /></div>
          </div>
          <div><label className="label">Reason</label>
            <textarea className="input" rows={2} value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} /></div>
          <p className="text-xs text-gray-500">
            The Leave Agent validates dates and balance, retrieves the applicable policy, and auto-approves
            short casual/sick leave. Anything else pauses for your approval.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={() => setShowNew(false)}>Cancel</button>
            <button className="btn-primary" disabled={busy}>{busy ? 'Running agents…' : 'Submit Request'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
