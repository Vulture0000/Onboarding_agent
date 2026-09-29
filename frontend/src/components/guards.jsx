import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Loading } from './ui'

/** Any signed-in role. Redirects to /login when there is no session. */
export function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}

/** Restricts a route to specific roles. `roles` is checked inclusively. */
export function RequireRole({ roles, children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (!roles.includes(user.role)) {
    // Send them somewhere they are actually allowed to be.
    return <Navigate to={user.role === 'EMPLOYEE' ? '/my' : '/'} replace />
  }
  return children
}