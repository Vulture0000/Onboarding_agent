import { useMemo, useState } from 'react'
import { ListChecks, Loader2, Filter } from 'lucide-react'
import { useFetch } from '../hooks/useFetch'
import { errMsg, listMyTasks, updateMyTask } from '../services/api'
import { Empty, ErrorBox, Loading, PageHeader, ProgressBar, StatusBadge } from '../components/ui'

const STATUSES = ['TODO', 'IN_PROGRESS', 'COMPLETED', 'OVERDUE']

export default function MyTasks() {
  const { data, loading, error, refetch, setData } = useFetch(listMyTasks, [])
  const [filter, setFilter] = useState('ALL')
  const [busyId, setBusyId] = useState(null)
  const [actionError, setActionError] = useState(null)

  const tasks = data || []
  const filtered = useMemo(
    () => (filter === 'ALL' ? tasks : tasks.filter(t => t.status === filter)),
    [tasks, filter],
  )
  const counts = useMemo(() => {
    const c = { ALL: tasks.length }
    STATUSES.forEach(s => { c[s] = tasks.filter(t => t.status === s).length })
    return c
  }, [tasks])
  const completed = counts.COMPLETED
  const pct = tasks.length ? Math.round((completed / tasks.length) * 100) : 0

  const setStatus = async (task, status) => {
    setBusyId(task.id)
    setActionError(null)
    try {
      const updated = await updateMyTask(task.id, status)
      setData(prev => prev.map(t => (t.id === task.id ? updated : t)))
    } catch (e) {
      setActionError(errMsg(e))
    } finally {
      setBusyId(null)
    }
  }

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={refetch} />

  return (
    <div>
      <PageHeader
        title="My Tasks"
        subtitle="Only tasks assigned to you. Updating status here updates your onboarding progress."
        actions={
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="input w-auto flex items-center gap-2"
          >
            <option value="ALL">All ({counts.ALL})</option>
            {STATUSES.map(s => (
              <option key={s} value={s}>{s.replace('_', ' ')} ({counts[s]})</option>
            ))}
          </select>
        }
      />

      <div className="card mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm text-gray-400 flex items-center gap-2">
            <Filter size={14} />
            Overall completion
          </div>
          <span className="text-xs text-gray-500">{completed}/{tasks.length} · {pct}%</span>
        </div>
        <ProgressBar pct={pct} />
      </div>

      {actionError && <div className="mb-4"><ErrorBox message={actionError} /></div>}

      {filtered.length === 0 ? (
        <Empty
          icon={ListChecks}
          title={filter === 'ALL' ? 'No tasks assigned yet' : `No ${filter.toLowerCase().replace('_', ' ')} tasks`}
          hint={filter === 'ALL' ? 'Your onboarding plan has not been generated.' : 'Try a different filter.'}
        />
      ) : (
        <div className="card overflow-hidden !p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-edge text-left text-xs uppercase tracking-wide text-gray-500">
                <th className="px-5 py-3 font-medium">Task</th>
                <th className="px-5 py-3 font-medium">Category</th>
                <th className="px-5 py-3 font-medium">Priority</th>
                <th className="px-5 py-3 font-medium">Due</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Set status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(t => (
                <tr key={t.id} className="border-b border-edge/50 last:border-0 hover:bg-panel/50">
                  <td className="px-5 py-3">
                    <div className="text-gray-100">{t.title}</div>
                    {t.description && (
                      <div className="text-xs text-gray-500 mt-0.5">{t.description}</div>
                    )}
                  </td>
                  <td className="px-5 py-3 text-gray-400">{t.category || '—'}</td>
                  <td className="px-5 py-3"><StatusBadge status={t.priority} /></td>
                  <td className="px-5 py-3 text-gray-400 whitespace-nowrap">{t.due_date || '—'}</td>
                  <td className="px-5 py-3"><StatusBadge status={t.status} /></td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <select
                        value={t.status}
                        disabled={busyId === t.id}
                        onChange={e => setStatus(t, e.target.value)}
                        className="bg-card border border-edge rounded-lg px-2 py-1 text-xs text-gray-200 outline-none focus:border-accent disabled:opacity-50"
                      >
                        {STATUSES.map(s => (
                          <option key={s} value={s}>{s.replace('_', ' ')}</option>
                        ))}
                      </select>
                      {busyId === t.id && <Loader2 size={14} className="animate-spin text-gray-500" />}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}