import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { fetchMe, login as loginRequest, setToken, setUnauthorizedHandler, getToken } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const signOut = useCallback(() => {
    setToken('')
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken('')
      setUser(null)
    })
  }, [])

  // Restore the session from a stored token on first load.
  useEffect(() => {
    let alive = true
    const boot = async () => {
      if (!getToken()) {
        if (alive) setLoading(false)
        return
      }
      try {
        const me = await fetchMe()
        if (alive) setUser(me)
      } catch {
        setToken('')
      } finally {
        if (alive) setLoading(false)
      }
    }
    boot()
    return () => { alive = false }
  }, [])

  const signIn = useCallback(async (email, password) => {
    const data = await loginRequest(email, password)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      signIn,
      signOut,
      role: user?.role || null,
      isHR: user?.role === 'HR',
      isManager: user?.role === 'MANAGER',
      isEmployee: user?.role === 'EMPLOYEE',
      can: (...roles) => !!user && roles.includes(user.role),
    }),
    [user, loading, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}