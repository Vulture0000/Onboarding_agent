import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 120000 })

export function errMsg(e) {
  return e?.response?.data?.detail || e?.message || 'Something went wrong.'
}

// Employees
export const listEmployees = () => api.get('/employees').then(r => r.data)
export const getEmployee = id => api.get(`/employees/${id}`).then(r => r.data)
export const createEmployee = data => api.post('/employees', data).then(r => r.data)

// Resumes
export const listResumes = () => api.get('/resumes').then(r => r.data)
export const uploadResume = file => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/resumes/upload', form).then(r => r.data)
}

// Tasks
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
