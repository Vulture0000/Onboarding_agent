import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Users, FileText, ListChecks, CalendarDays,
  Plane, BookOpen, Activity, Settings, Bot,
} from 'lucide-react'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/employees', label: 'Employees', icon: Users },
  { to: '/resumes', label: 'Resumes', icon: FileText },
  { to: '/onboarding', label: 'Onboarding', icon: ListChecks },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/leave', label: 'Leave Requests', icon: Plane },
  { to: '/policies', label: 'HR Policies', icon: BookOpen },
  { to: '/agents', label: 'Agent Activity', icon: Activity },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 bg-panel border-r border-edge flex flex-col">
        <div className="px-5 py-5 border-b border-edge flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center">
            <Bot size={18} className="text-indigo-400" />
          </div>
          <div>
            <div className="font-bold tracking-wide text-white leading-tight">ONBOARD AI</div>
            <div className="text-[10px] text-gray-500 uppercase tracking-widest">Agentic HR Ops</div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-accent/15 text-indigo-300 border border-accent/30'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-card border border-transparent'
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 py-4 border-t border-edge">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
                isActive ? 'bg-accent/15 text-indigo-300' : 'text-gray-400 hover:text-gray-200 hover:bg-card'
              }`
            }
          >
            <Settings size={17} />
            Settings
          </NavLink>
        </div>
      </aside>
      <main className="flex-1 min-w-0 p-6 lg:p-8 overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  )
}
