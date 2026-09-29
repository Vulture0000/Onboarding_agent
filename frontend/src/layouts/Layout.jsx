import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Users, FileText, ListChecks, CalendarDays,
  Plane, BookOpen, Activity, Settings, Bot, UserCircle,
  ClipboardCheck, UsersRound, LogOut, Shield,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const ROLE_STYLE = {
  HR: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
  MANAGER: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  EMPLOYEE: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
}

/** `roles: null` means every signed-in role can see it. */
const NAV = [
  { to: '/my', label: 'My Home', icon: UserCircle, roles: null, group: 'mine' },
  { to: '/my/tasks', label: 'My Tasks', icon: ClipboardCheck, roles: null, group: 'mine' },
  { to: '/my/leave', label: 'My Leave', icon: Plane, roles: null, group: 'mine' },
  { to: '/my/meetings', label: 'My Meetings', icon: CalendarDays, roles: null, group: 'mine' },

  { to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['HR', 'MANAGER'] },
  { to: '/team', label: 'My Team', icon: UsersRound, roles: ['MANAGER'] },
  { to: '/leave', label: 'Leave Approvals', icon: Plane, roles: ['HR', 'MANAGER'] },
  { to: '/employees', label: 'Employees', icon: Users, roles: ['HR'] },
  { to: '/resumes', label: 'Resumes', icon: FileText, roles: ['HR'] },
  { to: '/onboarding', label: 'Onboarding', icon: ListChecks, roles: ['HR'] },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays, roles: ['HR', 'MANAGER'] },
  { to: '/agents', label: 'Agent Activity', icon: Activity, roles: ['HR', 'MANAGER'] },

  { to: '/policies', label: 'HR Policies', icon: BookOpen, roles: null },
]

const MINE_NAV = NAV.filter(n => n.group === 'mine')
const WORK_NAV = NAV.filter(n => !n.group && n.roles && (n.roles.includes('HR') || n.roles.includes('MANAGER')))

function NavItem({ to, label, icon: Icon, end }) {
  return (
    <NavLink
      to={to}
      end={end}
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
  )
}

function Section({ title, items, endFirst }) {
  if (!items.length) return null
  return (
    <div className="mb-1">
      {title && (
        <div className="px-3 pt-4 pb-1 text-[10px] uppercase tracking-widest text-gray-600">{title}</div>
      )}
      <div className="space-y-1">
        {items.map((n, i) => (
          <NavItem key={n.to} to={n.to} label={n.label} icon={n.icon} end={endFirst && i === 0} />
        ))}
      </div>
    </div>
  )
}

export default function Layout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const role = user?.role

  const mine = MINE_NAV.filter(n => !n.roles || n.roles.includes(role))
  const work = WORK_NAV.filter(n => n.roles.includes(role))
  const isPrivileged = role === 'HR' || role === 'MANAGER'

  const logout = () => {
    signOut()
    navigate('/login', { replace: true })
  }

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

        <nav className="flex-1 px-3 py-3 overflow-y-auto">
          <Section title="For me" items={mine} />
          {isPrivileged && <Section title="Management" items={work} endFirst />}
          <div className="mt-1">
            <NavItem to="/policies" label="HR Policies" icon={BookOpen} />
          </div>
        </nav>

        <div className="px-3 py-3 border-t border-edge">
          <div className="px-3 pb-2">
            <div className="text-sm text-white truncate">{user?.name}</div>
            <div className="text-[11px] text-gray-500 truncate mb-1.5">{user?.email}</div>
            <span className={`badge border ${ROLE_STYLE[role] || ''}`}>
              <Shield size={11} />
              {role === 'HR' ? 'HR Admin' : role === 'MANAGER' ? 'Manager' : 'Employee'}
            </span>
          </div>
          <NavItem to="/settings" label="Settings" icon={Settings} />
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-red-300 hover:bg-red-500/10 w-full mt-1"
          >
            <LogOut size={17} />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0 p-6 lg:p-8 overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  )
}