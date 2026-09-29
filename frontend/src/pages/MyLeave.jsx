import { useState } from 'react'
import { Plane, Plus } from 'lucide-react'
import { useFetch } from '../hooks/useFetch'
import { errMsg, createMyLeave, listMyBalances, listMyLeave } from '../services/api'
import { Empty, ErrorBox, Loading, Modal, PageHeader, ProgressBar, StatusBadge } from '../components/ui'

const LEAVE_TYPES = ['CASUAL', 'SICK', 'EARNED']
const todayISO = () => new Date().toISOString().slice(0, 10)

export default function MyLeave() {
  const leave = useFetch(listMyLeave, [])
  const balances = useFetch(listMyBalances, [])
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    leave_type: 'CASUAL', start_date: todayISO(), end_date: todayISO(), reason: '',
  })
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState(null)
  const [notice, setNotice] = useState(null)

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    setFormError(null)
    try {
      const created = await createMyLeave({
        leave_type: form.leave_type,
        start_date: form.start_date,
        end_date: form.end_date,
        reason: form.reason || null,
      })
      setNotice(
        created.requires_approval
          ? `Request #${created.id} submitted. It needs your manager or HR to approve it.`
          : `Request #${created.id} was auto-approved by the Leave Agent.`,
      )
      setOpen(false)
      leave.refetch()
      balances.refetch()
    } catch (err) {
      setFormError(errMsg(err))
    } finally {
      setBusy(false)
    }
  }

  if (leave.loading || balances.loading) return <Loading />
  if (leave.error) return <ErrorBox message={leave.error} onRetry={leave.refetch} />

  const requests = leave.data || []

  return (
    <div>
      <PageHeader
        title="My Leave"
        subtitle="Submit a request and track its status. Approvals come from your manager or HR."
        actions={
          <button className="btn-primary" onClick={() => setOpen(true)}>
            <Plus size={16} /> New request
          </button>
        }
      />

      {notice && (
        <div className="card border-emerald-500/40 bg-emerald-500/5 text-emerald-300 text-sm mb-4">
          {notice}
        </div>
      )}

      <div className="grid sm:grid-cols-3 gap-4 mb-6">
        {(balances.data || []).map(b => (
          <div key={b.id} className="card">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-300">{b.leave_type} leave</span>
              <span className="text-sm text-white font-semibold">
                {b.remaining_days}<span className="text-gray-500 font-normal">/{b.total_days}</span>
              </span>
            </div>
            <ProgressBar pct={b.total_days ? (b.remaining_days / b.total_days) * 100 : 0} />
            <div className="text-[11px] text-gray-500 mt-1.5">{b.used_days} day(s) used</div>
          </div>
        ))}
      </div>

      {requests.length === 0 ? (
        <Empty icon={Plane} title="No leave requests yet" hint="Submit your first request above." />
      ) : (
        <div className="card overflow-hidden !p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-edge text-left text-xs uppercase tracking-wide text-gray-500">
                <th className="px-5 py-3 font-medium">#</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Dates</th>
                <th className="px-5 py-3 font-medium">Days</th>
                <th className="px-5 py-3 font-medium">Reason</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Decided by</th>
              </tr>
            </thead>
            <tbody>
              {requests.map(l => (
                <tr key={l.id} className="border-b border-edge/50 last:border-0">
                  <td className="px-5 py-3 text-gray-500">#{l.id}</td>
                  <td className="px-5 py-3 text-gray-200">{l.leave_type}</td>
                  <td className="px-5 py-3 text-gray-400 whitespace-nowrap">
                    {l.start_date} → {l.end_date}
                  </td>
                  <td className="px-5 py-3 text-gray-400">{l.days}</td>
                  <td className="px-5 py-3 text-gray-400 max-w-[220px] truncate">{l.reason || '—'}</td>
                  <td className="px-5 py-3">
                    <StatusBadge status={l.status} />
                    {l.requires_approval && l.status === 'PENDING' && (
                      <div className="text-[11px] text-gray-500 mt-1">needs approval</div>
                    )}
                  </td>
                  <td className="px-5 py-3 text-gray-400">{l.decided_by || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="New leave request">
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">Leave type</label>
            <select
              className="input"
              value={form.leave_type}
              onChange={e => setForm({ ...form, leave_type: e.target.value })}
            >
              {LEAVE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Start date</label>
              <input
                type="date" required className="input" value={form.start_date}
                onChange={e => setForm({ ...form, start_date: e.target.value })}
              />
            </div>
            <div>
              <label className="label">End date</label>
              <input
                type="date" required className="input" value={form.end_date}
                min={form.start_date}
                onChange={e => setForm({ ...form, end_date: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="label">Reason</label>
            <textarea
              rows={3} className="input resize-none" value={form.reason}
              onChange={e => setForm({ ...form, reason: e.target.value })}
              placeholder="Optional context for your approver"
            />
          </div>
          <p className="text-xs text-gray-500">
            The Leave Agent checks dates and balance, then consults the policy documents. Requests
            beyond the auto-approval limit pause for human approval.
          </p>
          {formError && <ErrorBox message={formError} />}
          <div className="flex gap-2 justify-end">
            <button type="button" className="btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? 'Submitting…' : 'Submit request'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}