import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ClipboardCheck, CalendarDays, Plane, TrendingUp,
  CheckCircle2, Clock, AlertTriangle, Loader2,
} from 'lucide-react'
import { useFetch } from '../hooks/useFetch'
import { useAuth } from '../context/AuthContext'
import { errMsg, getMySummary, updateMyTask } from '../services/api'
import { Empty, ErrorBox, Loading, PageHeader, ProgressBar, StatCard, StatusBadge } from '../components/ui'

const STATUSES = ['TODO', 'IN_PROGRESS', 'COMPLETED', 'OVERDUE']
const OPEN_STATUSES = ['TODO', 'IN_PROGRESS', 'OVERDUE']

export default function MyHome() {
  const { user, isEmployee } = useAuth()
  const { data, loading, error, refetch, setData } = useFetch(getMySummary, [])
  const [busyId, setBusyId] = useState(null)
  const [actionError, setActionError] = useState(null)

  const openTasks = useMemo(
    () => (data?.tasks || []).filter(t => OPEN_STATUSES.includes(t.status)),
    [data],
  )
  const doneTasks = useMemo(
    () => (data?.tasks || []).filter(t => t.status === 'COMPLETED'),
    [data],
  )
  const upcoming = data?.upcoming_meetings || []
  const pendingLeave = data?.pending_leave || []

  const setStatus = async (task, status) => {
    setBusyId(task.id)
    setActionError(null)
    try {
      const updated = await updateMyTask(task.id, status)
      setData(prev => ({
        ...prev,
        tasks: prev.tasks.map(t => (t.id === task.id ? updated : t)),
        progress: getMySummaryProgress(prev.tasks, updated),
      }))
    } catch (e) {
      setActionError(errMsg(e))
    } finally {
      setBusyId(null)
    }
  }

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={refetch} />
  if (!data) return null

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user?.name?.split(' ')[0] || ''}`}
        subtitle={
          isEmployee
            ? 'Your onboarding tasks, meetings and leave — scoped to you only.'
            : 'Your own record. Use the Management section for team and org views.'
        }
        actions={
          <span className="badge border border-edge bg-card text-gray-400">
            {user?.employee_id} · {data.balances?.length || 0} leave types
          </span>
        }
      />

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={ClipboardCheck}
          label="Open tasks"
          value={openTasks.length}
          sub={`of ${data.progress.total_tasks} total`}
        />
        <StatCard
          icon={CheckCircle2}
          label="Completed"
          value={data.progress.completed_tasks}
          sub={`${data.progress.progress_pct}% done`}
          color="text-emerald-400"
        />
        <StatCard
          icon={CalendarDays}
          label="Upcoming meetings"
          value={upcoming.length}
          color="text-blue-400"
        />
        <StatCard
          icon={Plane}
          label="Leave awaiting approval"
          value={pendingLeave.length}
          color={pendingLeave.length ? 'text-amber-400' : 'text-gray-400'}
        />
      </div>

      <div className="card mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="font-semibold text-white">My onboarding progress</div>
          <span className="text-xs text-gray-500">
            {data.progress.completed_tasks}/{data.progress.total_tasks} tasks
          </span>
        </div>
        <ProgressBar pct={data.progress.progress_pct} />
      </div>

      {actionError && <div className="mb-4"><ErrorBox message={actionError} /></div>}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <div className="font-semibold text-white flex items-center gap-2">
              <TrendingUp size={16} className="text-indigo-400" />
              Tasks assigned to me
            </div>
            <Link to="/my/tasks" className="text-xs text-indigo-300 hover:text-indigo-200">
              View all →
            </Link>
          </div>

          {openTasks.length === 0 ? (
            <Empty
              icon={CheckCircle2}
              title="Nothing outstanding"
              hint="All your onboarding tasks are complete. Nice work."
            />
          ) : (
            <div className="space-y-2">
              {openTasks.slice(0, 6).map(t => (
                <TaskRow key={t.id} task={t} busy={busyId === t.id} onSet={setStatus} />
              ))}
            </div>
          )}

          {doneTasks.length > 0 && (
            <details className="mt-4 pt-4 border-t border-edge">
              <summary className="text-sm text-gray-400 cursor-pointer select-none">
                {doneTasks.length} completed task{doneTasks.length > 1 ? 's' : ''}
              </summary>
              <div className="space-y-2 mt-3">
                {doneTasks.map(t => (
                  <TaskRow key={t.id} task={t} busy={busyId === t.id} onSet={setStatus} />
                ))}
              </div>
            </details>
          )}
        </div>

        <div className="space-y-6">
          <div className="card">
            <div className="font-semibold text-white mb-3">Upcoming meetings</div>
            {upcoming.length === 0 ? (
              <div className="text-sm text-gray-500">No meetings scheduled.</div>
            ) : (
              <div className="space-y-2">
                {upcoming.slice(0, 5).map(m => (
                  <div key={m.id} className="flex items-start gap-3 p-2 rounded-lg bg-panel border border-edge">
                    <CalendarDays size={15} className="text-blue-400 mt-0.5 shrink-0" />
                    <div className="min-w-0">
                      <div className="text-sm text-gray-200 truncate">{m.title}</div>
                      <div className="text-xs text-gray-500">
                        {m.date} · {m.start_time}–{m.end_time}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="font-semibold text-white mb-3">My leave balances</div>
            <div className="space-y-2.5">
              {(data.balances || []).map(b => (
                <div key={b.id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-300">{b.leave_type}</span>
                    <span className="text-gray-400">
                      {b.remaining_days}/{b.total_days} left
                    </span>
                  </div>
                  <ProgressBar pct={b.total_days ? (b.remaining_days / b.total_days) * 100 : 0} />
                </div>
              ))}
            </div>
            <Link
              to="/my/leave"
              className="btn-ghost w-full justify-center mt-4 !py-1.5 text-xs"
            >
              Request leave
            </Link>
          </div>

          {pendingLeave.length > 0 && (
            <div className="card border-amber-500/30">
              <div className="font-semibold text-white mb-2 flex items-center gap-2">
                <Clock size={15} className="text-amber-400" />
                Awaiting approval
              </div>
              {pendingLeave.map(l => (
                <div key={l.id} className="text-sm text-gray-400">
                  {l.leave_type} · {l.start_date} → {l.end_date} ({l.days}d)
                </div>
              ))}
              <div className="text-xs text-gray-500 mt-2">
                Your manager or HR will decide this.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function getMySummaryProgress(tasks, updated) {
  const completed = tasks.filter(
    t => (t.id === updated.id ? updated.status : t.status) === 'COMPLETED',
  ).length
  const total = tasks.length
  return {
    total_tasks: total,
    completed_tasks: completed,
    progress_pct: total ? Math.round((completed / total) * 100) : 0,
  }
}

function TaskRow({ task, busy, onSet }) {
  return (
    <div className="flex items-center gap-3 p-2.5 rounded-lg bg-panel border border-edge">
      <div className="min-w-0 flex-1">
        <div className="text-sm text-gray-100 flex items-center gap-2">
          {task.title}
          {task.priority === 'HIGH' && (
            <AlertTriangle size={13} className="text-red-400 shrink-0" />
          )}
        </div>
        <div className="text-xs text-gray-500">
          {task.category} · due {task.due_date || '—'}
        </div>
      </div>
      <StatusBadge status={task.status} />
      <select
        value={task.status}
        disabled={busy}
        onChange={e => onSet(task, e.target.value)}
        className="bg-card border border-edge rounded-lg px-2 py-1 text-xs text-gray-200 outline-none focus:border-accent disabled:opacity-50"
      >
        {STATUSES.map(s => (
          <option key={s} value={s}>{s.replace('_', ' ')}</option>
        ))}
      </select>
      {busy && <Loader2 size={14} className="animate-spin text-gray-500" />}
    </div>
  )
}