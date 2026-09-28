import { useState } from 'react'
import { Activity, CheckCircle2, AlertTriangle, XCircle, RefreshCw } from 'lucide-react'
import { getAgentLogs } from '../services/api'
import { usePoll } from '../hooks/useFetch'
import { PageHeader, Empty } from '../components/ui'

const AGENT_COLORS = {
  Supervisor: 'text-violet-300',
  ResumeAgent: 'text-blue-300',
  OnboardingAgent: 'text-indigo-300',
  CalendarAgent: 'text-cyan-300',
  LeaveAgent: 'text-amber-300',
  PolicyAgent: 'text-emerald-300',
  API: 'text-gray-300',
  System: 'text-gray-400',
}

function StatusIcon({ status }) {
  if (status === 'error') return <XCircle size={15} className="text-red-400" />
  if (status === 'warning') return <AlertTriangle size={15} className="text-amber-400" />
  return <CheckCircle2 size={15} className="text-emerald-400" />
}

export default function AgentActivity() {
  const [live, setLive] = useState(true)
  const logs = usePoll(() => getAgentLogs(200), live ? 4000 : 10 ** 9)

  return (
    <div>
      <PageHeader
        title="Agent Activity"
        subtitle="Live log of every agent execution, pulled from the backend agent_logs table"
        actions={
          <button className={live ? 'btn-primary' : 'btn-ghost'} onClick={() => setLive(!live)}>
            <Activity size={15} className={live ? 'animate-pulse' : ''} />
            {live ? 'Live' : 'Paused'}
          </button>
        }
      />

      {!logs && <div className="card text-sm text-gray-500">Loading agent activity…</div>}
      {logs && logs.length === 0 && (
        <Empty icon={Activity} title="No agent activity yet" hint="Upload a resume or submit a leave request to see the agents work." />
      )}

      {logs && logs.length > 0 && (
        <div className="card !p-0">
          <div className="divide-y divide-edge/50">
            {logs.map(l => (
              <div key={l.id} className="flex items-start gap-4 px-5 py-3 hover:bg-panel/60">
                <span className="font-mono text-xs text-gray-500 pt-0.5 w-16 shrink-0">
                  {l.timestamp.slice(11, 19)}
                </span>
                <div className="w-36 shrink-0">
                  <span className={`text-sm font-medium ${AGENT_COLORS[l.agent] || 'text-gray-300'}`}>
                    {l.agent}
                  </span>
                  <div className="text-[11px] text-gray-500">{l.action.replaceAll('_', ' ')}</div>
                </div>
                <div className="flex-1 min-w-0 text-sm text-gray-300 break-words">
                  {l.detail || '—'}
                  {l.employee_id && <span className="ml-2 text-xs font-mono text-gray-500">[{l.employee_id}]</span>}
                </div>
                <StatusIcon status={l.status} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
