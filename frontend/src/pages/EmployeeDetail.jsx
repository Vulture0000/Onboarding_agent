import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Mail, Phone, GraduationCap, Briefcase, UserCheck, Star } from 'lucide-react'
import { getEmployee, updateTask, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { Loading, ErrorBox, StatusBadge, ProgressBar, PageHeader } from '../components/ui'

const STATUSES = ['TODO', 'IN_PROGRESS', 'COMPLETED', 'OVERDUE']

export default function EmployeeDetail() {
  const { id } = useParams()
  const { data: emp, loading, error, refetch } = useFetch(() => getEmployee(id), [id])

  const changeStatus = async (taskId, status) => {
    try { await updateTask(taskId, status); refetch() }
    catch (e) { alert(errMsg(e)) }
  }

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} />
  if (!emp) return null

  return (
    <div>
      <Link to="/employees" className="text-sm text-gray-400 hover:text-white flex items-center gap-1 mb-4">
        <ArrowLeft size={14} /> Back to Employees
      </Link>
      <PageHeader
        title={emp.name}
        subtitle={`${emp.id} · ${emp.role || 'Role TBD'} · ${emp.department || 'Department TBD'}`}
        actions={<StatusBadge status={emp.status} />}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="card space-y-4">
          <h2 className="font-semibold text-white">Profile</h2>
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-3 text-gray-300"><Mail size={15} className="text-indigo-400" />{emp.email}</div>
            {emp.phone && <div className="flex items-center gap-3 text-gray-300"><Phone size={15} className="text-indigo-400" />{emp.phone}</div>}
            {emp.education && <div className="flex items-center gap-3 text-gray-300"><GraduationCap size={15} className="text-indigo-400" />{emp.education}</div>}
            <div className="flex items-center gap-3 text-gray-300"><Briefcase size={15} className="text-indigo-400" />{emp.experience || 'Fresher'}</div>
            <div className="flex items-center gap-3 text-gray-300"><UserCheck size={15} className="text-indigo-400" />Manager: {emp.manager || '—'}</div>
            <div className="flex items-center gap-3 text-gray-300"><Star size={15} className="text-indigo-400" />Mentor: {emp.mentor || '—'}</div>
          </div>
          {emp.skills?.length > 0 && (
            <div>
              <div className="label">Skills</div>
              <div className="flex flex-wrap gap-1.5">
                {emp.skills.map(s => (
                  <span key={s} className="badge bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">{s}</span>
                ))}
              </div>
            </div>
          )}
          <div>
            <div className="label">Joining date</div>
            <div className="text-sm text-gray-200">{emp.joining_date}</div>
          </div>
          <div>
            <div className="label">Leave balances</div>
            <div className="grid grid-cols-3 gap-2">
              {emp.balances.map(b => (
                <div key={b.id} className="bg-panel border border-edge rounded-lg p-2 text-center">
                  <div className="text-lg font-bold text-white">{b.remaining_days}</div>
                  <div className="text-[10px] uppercase tracking-wide text-gray-500">{b.leave_type}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Onboarding Progress</h2>
            <span className="text-xs text-gray-400">
              {emp.progress.completed_tasks}/{emp.progress.total_tasks} tasks complete
            </span>
          </div>
          <ProgressBar pct={emp.progress.progress_pct} />

          <div className="mt-5 space-y-2">
            {emp.tasks.map(t => (
              <div key={t.id} className="flex items-center gap-3 p-3 rounded-lg bg-panel border border-edge">
                <input
                  type="checkbox"
                  checked={t.status === 'COMPLETED'}
                  onChange={e => changeStatus(t.id, e.target.checked ? 'COMPLETED' : 'TODO')}
                  className="w-4 h-4 accent-emerald-500"
                />
                <div className="flex-1 min-w-0">
                  <div className={`text-sm ${t.status === 'COMPLETED' ? 'text-gray-500 line-through' : 'text-white'}`}>{t.title}</div>
                  <div className="text-xs text-gray-500 truncate">{t.description}</div>
                </div>
                <span className="text-xs text-gray-500 hidden sm:block">{t.due_date}</span>
                <StatusBadge status={t.priority} />
                <select
                  value={t.status}
                  onChange={e => changeStatus(t.id, e.target.value)}
                  className="bg-base border border-edge rounded-lg text-xs px-2 py-1.5 text-gray-300 focus:outline-none"
                >
                  {STATUSES.map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
            ))}
            {emp.tasks.length === 0 && <div className="text-sm text-gray-500 py-6 text-center">No onboarding tasks yet.</div>}
          </div>

          {emp.meetings?.length > 0 && (
            <>
              <h2 className="font-semibold text-white mt-6 mb-3">Meetings</h2>
              <div className="space-y-2">
                {emp.meetings.map(m => (
                  <div key={m.id} className="flex items-center gap-3 p-3 rounded-lg bg-panel border border-edge text-sm">
                    <div className="flex-1">
                      <span className={m.status === 'CANCELLED' ? 'text-gray-500 line-through' : 'text-white'}>{m.title}</span>
                      <span className="text-gray-500 text-xs ml-2">{m.date} · {m.start_time}–{m.end_time}</span>
                    </div>
                    <StatusBadge status={m.status} />
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}
