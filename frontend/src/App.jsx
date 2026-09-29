import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './layouts/Layout.jsx'
import { RequireAuth, RequireRole } from './components/guards.jsx'
import { useAuth } from './context/AuthContext'

import Login from './pages/Login.jsx'
import Signup from './pages/Signup.jsx'
import MyHome from './pages/MyHome.jsx'
import MyTasks from './pages/MyTasks.jsx'
import MyLeave from './pages/MyLeave.jsx'
import MyMeetings from './pages/MyMeetings.jsx'
import MyTeam from './pages/MyTeam.jsx'
import TeamMemberDetail from './pages/TeamMemberDetail.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Employees from './pages/Employees.jsx'
import EmployeeDetail from './pages/EmployeeDetail.jsx'
import Resumes from './pages/Resumes.jsx'
import Onboarding from './pages/Onboarding.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import LeaveRequests from './pages/LeaveRequests.jsx'
import Policies from './pages/Policies.jsx'
import AgentActivity from './pages/AgentActivity.jsx'
import Settings from './pages/Settings.jsx'

const HR = ['HR']
const HR_MANAGER = ['HR', 'MANAGER']

/** Landing page per role — everyone has somewhere sensible to land. */
function HomeByRole() {
  const { user } = useAuth()
  if (user?.role === 'EMPLOYEE') return <Navigate to="/my" replace />
  return <Dashboard />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        {/* Self-service — every role */}
        <Route path="/my" element={<MyHome />} />
        <Route path="/my/tasks" element={<MyTasks />} />
        <Route path="/my/leave" element={<MyLeave />} />
        <Route path="/my/meetings" element={<MyMeetings />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/settings" element={<Settings />} />

        {/* Manager + HR */}
        <Route path="/" element={<HomeByRole />} />
        <Route path="/team" element={<RequireRole roles={['MANAGER']}><MyTeam /></RequireRole>} />
        <Route path="/my/team/:id" element={<RequireRole roles={HR_MANAGER}><TeamMemberDetail /></RequireRole>} />
        <Route path="/leave" element={<RequireRole roles={HR_MANAGER}><LeaveRequests /></RequireRole>} />
        <Route path="/calendar" element={<RequireRole roles={HR_MANAGER}><CalendarPage /></RequireRole>} />
        <Route path="/agents" element={<RequireRole roles={HR_MANAGER}><AgentActivity /></RequireRole>} />

        {/* HR only */}
        <Route path="/employees" element={<RequireRole roles={HR}><Employees /></RequireRole>} />
        <Route path="/employees/:id" element={<RequireRole roles={HR}><EmployeeDetail /></RequireRole>} />
        <Route path="/resumes" element={<RequireRole roles={HR}><Resumes /></RequireRole>} />
        <Route path="/onboarding" element={<RequireRole roles={HR}><Onboarding /></RequireRole>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}