import { Link } from 'react-router-dom'
import { UsersRound, Plane, TrendingUp } from 'lucide-react'
import { useFetch } from '../hooks/useFetch'
import { useAuth } from '../context/AuthContext'
import { getTeam } from '../services/api'
import { Empty, ErrorBox, Loading, PageHeader, ProgressBar, StatCard, StatusBadge } from '../components/ui'

export default function MyTeam() {
  const { user } = useAuth()
  const { data, loading, error, refetch } = useFetch(getTeam, [])

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={refetch} />

  const team = data || []
  const pendingTotal = team.reduce((n, t) => n + (t.pending_leave?.length || 0), 0)
  const avgProgress = team.length
    ? Math.round(team.reduce((n, t) => n + t.progress_pct, 0) / team.length)
    : 0

  return (
    <div>
      <PageHeader
        title="My Team"
        subtitle={`Direct reports of ${user?.name}. You see only your own team — not the whole company.`}
        actions={
          pendingTotal > 0 && (
            <Link to="/leave" className="btn-primary">
              <Plane size={16} /> {pendingTotal} awaiting your decision
            </Link>
          )
        }
      />

      <div className="grid sm:grid-cols-3 gap-4 mb-6">
        <StatCard icon={UsersRound} label="Direct reports" value={team.length} />
        <StatCard
          icon={TrendingUp}
          label="Average onboarding progress"
          value={`${avgProgress}%`}
          color="text-emerald-400"
        />
        <StatCard
          icon={Plane}
          label="Pending leave approvals"
          value={pendingTotal}
          color={pendingTotal ? 'text-amber-400' : 'text-gray-400'}
        />
      </div>

      {team.length === 0 ? (
        <Empty
          icon={UsersRound}
          title="No direct reports"
          hint="Employees need manager_id pointing at your record to appear here."
        />
      ) : (
        <div className="grid lg:grid-cols-2 gap-4">
          {team.map(m => (
            <div key={m.id} className="card">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <Link
                    to={`/my/team/${m.id}`}
                    className="text-sm font-semibold text-white hover:text-indigo-300"
                  >
                    {m.name}
                  </Link>
                  <div className="text-xs text-gray-500">
                    {m.role} · {m.department} · joined {m.joining_date}
                  </div>
                </div>
                <StatusBadge status={m.status} />
              </div>

              <div className="mb-3">
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Onboarding progress</span>
                  <span>{m.completed_tasks}/{m.total_tasks} tasks</span>
                </div>
                <ProgressBar pct={m.progress_pct} />
              </div>

              {m.pending_leave?.length > 0 ? (
                <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30">
                  <div className="text-xs text-amber-300 font-medium mb-1">Leave awaiting your decision</div>
                  {m.pending_leave.map(l => (
                    <div key={l.id} className="text-xs text-gray-400">
                      {l.leave_type} · {l.start_date} → {l.end_date} ({l.days}d) — {l.reason || 'no reason'}
                    </div>
                  ))}
                  <Link to="/leave" className="btn-ghost !py-1 text-xs mt-2">
                    Review & decide →
                  </Link>
                </div>
              ) : (
                <div className="text-xs text-gray-500">No pending requests.</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}