import { Link } from 'react-router-dom'
import { Users, ListChecks, CalendarDays, Plane, ArrowRight, Activity } from 'lucide-react'
import { getDashboard } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { Loading, ErrorBox, ProgressBar, StatusBadge, StatCard, PageHeader } from '../components/ui'

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function Dashboard() {
  const { data, loading, error, refetch } = useFetch(getDashboard)

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={refetch} />
  const d = data

  return (
    <div>
      <PageHeader
        title={`${greeting()}, HR Admin`}
        subtitle="Employee onboarding overview — orchestrated by LangGraph agents"
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard icon={Users} label="Employees" value={d.employees} sub={`${d.onboarding} onboarding`} />
        <StatCard icon={ListChecks} label="Onboarding tasks" value={`${d.tasks_completed}/${d.tasks_total}`} sub="completed" color="text-violet-400" />
        <StatCard icon={CalendarDays} label="Upcoming meetings" value={d.upcoming_meetings} color="text-blue-400" />
        <StatCard icon={Plane} label="Leave pending" value={d.pending_leave} color="text-amber-400" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <section className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Recent Employees</h2>
            <Link to="/employees" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">View all <ArrowRight size={12} /></Link>
          </div>
          <div className="space-y-3">
            {d.recent_employees.map(e => (
              <Link key={e.id} to={`/employees/${e.id}`} className="flex items-center gap-3 p-3 rounded-lg bg-panel border border-edge hover:border-accent/50 transition-colors">
                <div className="w-9 h-9 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center text-indigo-300 text-sm font-bold">
                  {e.name.split(' ').map(w => w[0]).slice(0, 2).join('')}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">{e.name} <span className="text-gray-500">· {e.id}</span></div>
                  <div className="text-xs text-gray-400 truncate">{e.role} · {e.department}</div>
                </div>
                <div className="w-28"><ProgressBar pct={e.progress_pct} /></div>
                <StatusBadge status={e.status} />
              </Link>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Upcoming Meetings</h2>
            <Link to="/calendar" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">Calendar <ArrowRight size={12} /></Link>
          </div>
          <div className="space-y-2">
            {d.upcoming_meetings_list.length === 0 && <div className="text-sm text-gray-500">No upcoming meetings.</div>}
            {d.upcoming_meetings_list.map(m => (
              <div key={m.id} className="flex items-center gap-3 p-3 rounded-lg bg-panel border border-edge">
                <CalendarDays size={16} className="text-blue-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white truncate">{m.title}</div>
                  <div className="text-xs text-gray-400">{m.employee_name} · {m.date}</div>
                </div>
                <div className="text-xs text-gray-300 font-mono">{m.start_time}–{m.end_time}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Pending Approvals</h2>
            <Link to="/leave" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">Leave queue <ArrowRight size={12} /></Link>
          </div>
          <div className="space-y-2">
            {d.pending_approvals.length === 0 && <div className="text-sm text-gray-500">Nothing awaiting approval.</div>}
            {d.pending_approvals.map(l => (
              <div key={l.id} className="flex items-center gap-3 p-3 rounded-lg bg-panel border border-amber-500/20">
                <Plane size={16} className="text-amber-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white truncate">{l.employee_name} · {l.leave_type} leave</div>
                  <div className="text-xs text-gray-400">{l.start_date} → {l.end_date} ({l.days}d) — {l.reason}</div>
                </div>
                <StatusBadge status="PENDING" />
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2"><Activity size={16} className="text-indigo-400" /> Agent Activity</h2>
            <Link to="/agents" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">Full log <ArrowRight size={12} /></Link>
          </div>
          <div className="space-y-2">
            {d.recent_activity.map(a => (
              <div key={a.id} className="flex items-start gap-3 p-2.5 rounded-lg bg-panel border border-edge">
                <span className="text-[11px] font-mono text-gray-500 pt-0.5 w-14 shrink-0">{a.timestamp.slice(11, 19)}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-indigo-300 font-medium">{a.agent} <span className="text-gray-500">· {a.action}</span></div>
                  <div className="text-xs text-gray-400 truncate">{a.detail}</div>
                </div>
                <StatusBadge status={a.status} />
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
