import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 120000 })

export const TOKEN_KEY = 'onboardai.token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** Signed-out callback, installed by AuthContext so a 401 anywhere bounces to /login. */
let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

api.interceptors.request.use(config => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  r => r,
  e => {
    if (e?.response?.status === 401 && onUnauthorized) onUnauthorized()
    return Promise.reject(e)
  },
)

export function errMsg(e) {
  return e?.response?.data?.detail || e?.message || 'Something went wrong.'
}

// Auth
export const login = (email, password) =>
  api.post('/auth/login', { email, password }).then(r => r.data)
export const fetchMe = () => api.get('/auth/me').then(r => r.data)
export const fetchDemoAccounts = () => api.post('/auth/demo-accounts').then(r => r.data)

// Self-service (identity comes from the token, never from a parameter)
export const getMySummary = () => api.get('/me/summary').then(r => r.data)
export const getMyProfile = () => api.get('/me/profile').then(r => r.data)
export const listMyTasks = params => api.get('/me/tasks', { params }).then(r => r.data)
export const updateMyTask = (id, status) =>
  api.patch(`/me/tasks/${id}`, { status }).then(r => r.data)
export const listMyMeetings = () => api.get('/me/meetings').then(r => r.data)
export const listMyLeave = () => api.get('/me/leave').then(r => r.data)
export const listMyBalances = () => api.get('/me/leave/balances').then(r => r.data)
export const createMyLeave = data => api.post('/me/leave', data).then(r => r.data)
export const getTeam = () => api.get('/team').then(r => r.data)
export const getTeamMember = id => api.get(`/team/${id}`).then(r => r.data)

// Employees (HR only)
export const listEmployees = () => api.get('/employees').then(r => r.data)
export const getEmployee = id => api.get(`/employees/${id}`).then(r => r.data)
export const createEmployee = data => api.post('/employees', data).then(r => r.data)
export const resetEmployeePassword = id =>
  api.post(`/employees/${id}/reset-password`).then(r => r.data)
export const setEmployeeRole = (id, role) =>
  api.patch(`/employees/${id}/role`, { role }).then(r => r.data)
// Which access role would this email get? (HR only, drives the live form hint)
export const previewRole = email =>
  api.get('/employees/role-preview', { params: { email } }).then(r => r.data)

// Resumes (HR only)
export const listResumes = () => api.get('/resumes').then(r => r.data)
export const uploadResume = file => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/resumes/upload', form).then(r => r.data)
}

// Tasks (scoped server-side by role)
export const listTasks = params => api.get('/tasks', { params }).then(r => r.data)
export const updateTask = (id, status) => api.patch(`/tasks/${id}`, { status }).then(r => r.data)

// Meetings
export const listMeetings = params => api.get('/meetings', { params }).then(r => r.data)
export const createMeeting = data => api.post('/meetings', data).then(r => r.data)
export const updateMeeting = (id, data) => api.patch(`/meetings/${id}`, data).then(r => r.data)

// Leave
export const listLeave = params => api.get('/leave', { params }).then(r => r.data)
export const listBalances = params => api.get('/leave/balances', { params }).then(r => r.data)
export const createLeave = data => api.post('/leave', data).then(r => r.data)
export const approveLeave = id => api.post(`/leave/${id}/approve`).then(r => r.data)
export const rejectLeave = id => api.post(`/leave/${id}/reject`).then(r => r.data)

// Policy
export const queryPolicy = question => api.post('/policy/query', { question }).then(r => r.data)

// Agents
export const getAgentLogs = (limit = 100) => api.get('/agent/logs', { params: { limit } }).then(r => r.data)
export const getAgentStatus = () => api.get('/agent/status').then(r => r.data)
export const runAgent = data => api.post('/agent/run', data).then(r => r.data)

// Dashboard
export const getDashboard = () => api.get('/dashboard/stats').then(r => r.data)

export default api