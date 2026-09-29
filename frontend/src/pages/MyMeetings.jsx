import { useState } from 'react'
import { CalendarDays, CheckCircle2, Loader2 } from 'lucide-react'
import { useFetch } from '../hooks/useFetch'
import { errMsg, listMyMeetings, updateMeeting } from '../services/api'
import { Empty, ErrorBox, Loading, PageHeader, StatusBadge } from '../components/ui'

export default function MyMeetings() {
  const { data, loading, error, refetch, setData } = useFetch(listMyMeetings, [])
  const [busyId, setBusyId] = useState(null)
  const [actionError, setActionError] = useState(null)

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={refetch} />

  const meetings = data || []
  const today = new Date().toISOString().slice(0, 10)
  const active = meetings.filter(m => m.status === 'SCHEDULED')
  const past = meetings.filter(m => m.status !== 'SCHEDULED')

  const markDone = async m => {
    setBusyId(m.id)
    setActionError(null)
    try {
      const updated = await updateMeeting(m.id, { status: 'COMPLETED' })
      setData(prev => prev.map(x => (x.id === m.id ? updated : x)))
    } catch (e) {
      setActionError(errMsg(e))
    } finally {
      setBusyId(null)
    }
  }

  const Card = ({ m, actionable }) => (
    <div className="flex items-center gap-4 p-4 bg-panel border border-edge rounded-lg">
      <div className="w-14 shrink-0 text-center">
        <div className="text-xs uppercase text-gray-500">
          {new Date(m.date + 'T00:00:00').toLocaleString('en', { month: 'short' })}
        </div>
        <div className="text-xl font-bold text-white leading-none">
          {new Date(m.date + 'T00:00:00').getDate()}
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm text-gray-100">{m.title}</div>
        <div className="text-xs text-gray-500 mt-0.5">
          {m.start_time}–{m.end_time}
          {m.participants?.length ? ` · ${m.participants.join(', ')}` : ''}
        </div>
      </div>
      <StatusBadge status={m.status} />
      {actionable && (
        <button
          className="btn-ghost !py-1.5 text-xs"
          disabled={busyId === m.id}
          onClick={() => markDone(m)}
        >
          {busyId === m.id ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          Mark done
        </button>
      )}
    </div>
  )

  return (
    <div>
      <PageHeader
        title="My Meetings"
        subtitle="Meetings scheduled for you by the Calendar Agent. You can mark your own as completed."
      />

      {actionError && <div className="mb-4"><ErrorBox message={actionError} /></div>}

      <div className="space-y-6">
        <div>
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Scheduled</h2>
          {active.length === 0 ? (
            <Empty icon={CalendarDays} title="No upcoming meetings" hint="Your onboarding plan has no meetings scheduled." />
          ) : (
            <div className="space-y-2">
              {active.map(m => (
                <Card key={m.id} m={m} actionable={m.date <= today} />
              ))}
            </div>
          )}
        </div>

        {past.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-gray-300 mb-3">Past / cancelled</h2>
            <div className="space-y-2">
              {past.map(m => <Card key={m.id} m={m} actionable={false} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}