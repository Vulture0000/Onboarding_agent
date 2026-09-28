import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './layouts/Layout.jsx'
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

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/employees" element={<Employees />} />
        <Route path="/employees/:id" element={<EmployeeDetail />} />
        <Route path="/resumes" element={<Resumes />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/leave" element={<LeaveRequests />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/agents" element={<AgentActivity />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
