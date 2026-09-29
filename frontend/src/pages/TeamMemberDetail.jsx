import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, CalendarDays, Plane } from 'lucide-react'
import { useFetch } from '../hooks/useFetch'
import { getTeamMember } from '../services/api'
import { Empty, ErrorBox, Loading, ProgressBar, StatusBadge } from '../components/ui'

export default function TeamMemberDetail() {
  const { id } = useParams()
  const { data, loading, error, refetch } = useFetch(() => getTeamMember(id), [id])

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={refetch} />
  if (!data) return null

  const Field = ({ label, value }) => (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-gray-600">{label}</div>
      <div className="text-sm text-gray-200 mt-0.5">{value || '—'}</div>
    </div>
  )

  return (
    <div>
      <Link to="/team" className="btn-ghost !py-1.5 text-xs mb-4">
        <ArrowLeft size={14} /> Back to team
      </Link>

      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">{data.name}</h1>
          <div className="text-sm text-gray-400">
            {data.role} · {data.department} · {data.id}
          </div>
          <div className="text-xs text-gray-500 mt-1">{data.email}</div>
        </div>
        <StatusBadge status={data.status} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="card">
          <div className="font-semibold text-white mb-4">Profile</div>
          <div className="space-y-3">
            <Field label="Phone" value={data.phone} />
            <Field label="Manager" value={data.manager} />
            <Field label="Mentor" value={data.mentor} />
            <Field label="Experience" value={data.experience} />
            <Field label="Education" value={data.education} />
            <Field label="Joining date" value={data.joining_date} />
            <Field label="Skills" value={data.skills?.join(', ')} />
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="font-semibold text-white">Onboarding progress</div>
              <span className="text-xs text-gray-500">
                {data.progress.completed_tasks}/{data.progress.total_tasks} tasks
              </span>
            </div>
            <ProgressBar pct={data.progress.progress_pct} />
          </div>

          <div className="card">
            <div className="font-semibold text-white mb-3">Their tasks ({data.tasks.length})</div>
            {data.tasks.length === 0 ? (
              <Empty title="No tasks generated yet" />
            ) : (
              <div className="space-y-2">
                {data.tasks.map(t => (
                  <div key={t.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-panel border border-edge">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-gray-100">{t.title}</div>
                      <div className="text-xs text-gray-500">{t.category} · due {t.due_date || '—'}</div>
                    </div>
                    <StatusBadge status={t.priority} />
                    <StatusBadge status={t.status} />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid sm:grid-cols-2 gap-6">
            <div className="card">
              <div className="font-semibold text-white mb-3 flex items-center gap-2">
                <CalendarDays size={15} className="text-blue-400" /> Meetings ({data.meetings.length})
              </div>
              {data.meetings.length === 0 ? (
                <div className="text-sm text-gray-500">None scheduled.</div>
              ) : (
                <div className="space-y-2">
                  {data.meetings.map(m => (
                    <div key={m.id} className="p-2 rounded-lg bg-panel border border-edge">
                      <div className="text-sm text-gray-200">{m.title}</div>
                      <div className="text-xs text-gray-500">
                        {m.date} · {m.start_time}–{m.end_time}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <div className="font-semibold text-white mb-3 flex items-center gap-2">
                <Plane size={15} className="text-amber-400" /> Leave ({data.leave_requests.length})
              </div>
              {data.leave_requests.length === 0 ? (
                <div className="text-sm text-gray-500">No requests.</div>
              ) : (
                <div className="space-y-2">
                  {data.leave_requests.map(l => (
                    <div key={l.id} className="p-2 rounded-lg bg-panel border border-edge">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm text-gray-200">
                          {l.leave_type} · {l.days}d
                        </div>
                        <StatusBadge status={l.status} />
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">{l.start_date} → {l.end_date}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}