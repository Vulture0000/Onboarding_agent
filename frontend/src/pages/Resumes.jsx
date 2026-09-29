import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { UploadCloud, FileText, CheckCircle2, Loader2 } from 'lucide-react'
import { listResumes, uploadResume, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { ErrorBox, PageHeader, StatusBadge } from '../components/ui'

const STEPS = ['Resume Agent', 'Employee Extraction', 'Profile Creation', 'Onboarding Plan', 'Meetings Scheduled']

export default function Resumes() {
  const { data: resumes, refetch } = useFetch(listResumes)
  const [dragOver, setDragOver] = useState(false)
  const [phase, setPhase] = useState('idle') // idle | processing | done | error
  const [stepIdx, setStepIdx] = useState(-1)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef()
  const timerRef = useRef()

  const process = useCallback(async file => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF resumes are supported.'); setPhase('error'); return
    }
    setPhase('processing'); setError(null); setResult(null); setStepIdx(0)

    // Advance the visual steps while the backend works (real result comes from the API)
    timerRef.current = setInterval(() => {
      setStepIdx(i => (i < STEPS.length - 1 ? i + 1 : i))
    }, 2500)

    try {
      const res = await uploadResume(file)
      clearInterval(timerRef.current)
      setStepIdx(STEPS.length)
      setResult(res)
      setPhase('done')
      refetch()
    } catch (e) {
      clearInterval(timerRef.current)
      setError(errMsg(e))
      setPhase('error')
    }
  }, [refetch])

  const onDrop = e => {
    e.preventDefault(); setDragOver(false)
    process(e.dataTransfer.files?.[0])
  }

  const emp = result?.employee_data
  const rd = result?.resume_data

  return (
    <div>
      <PageHeader title="Resumes" subtitle="Upload a PDF resume — the agent pipeline extracts the profile, builds an onboarding plan and schedules meetings" />

      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => phase !== 'processing' && inputRef.current?.click()}
        className={`card cursor-pointer border-2 border-dashed flex flex-col items-center justify-center py-14 transition-colors ${
          dragOver ? 'border-accent bg-accent/5' : 'border-edge hover:border-accent/50'
        }`}
      >
        <UploadCloud size={36} className="text-indigo-400 mb-3" />
        <div className="text-white font-medium">Upload Resume</div>
        <div className="text-sm text-gray-500 mt-1">Drop PDF here, or click to choose a file</div>
        <input ref={inputRef} type="file" accept="application/pdf" className="hidden"
               onChange={e => process(e.target.files?.[0])} />
      </div>

      {phase === 'processing' && (
        <div className="card mt-4">
          <div className="flex items-center gap-2 text-sm text-gray-300 mb-4">
            <Loader2 className="animate-spin text-indigo-400" size={16} /> Processing resume…
          </div>
          <div className="space-y-2">
            {STEPS.map((s, i) => (
              <div key={s} className="flex items-center gap-3 text-sm">
                {i < stepIdx ? <CheckCircle2 size={16} className="text-emerald-400" /> :
                 i === stepIdx ? <Loader2 size={16} className="animate-spin text-indigo-400" /> :
                 <div className="w-4 h-4 rounded-full border border-edge" />}
                <span className={i <= stepIdx ? 'text-gray-200' : 'text-gray-600'}>{s}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {phase === 'error' && (
        <div className="mt-4"><ErrorBox message={error} /></div>
      )}

      {phase === 'done' && result && (
        <div className="card mt-4 border-emerald-500/30">
          <div className="flex items-center gap-2 text-emerald-300 font-medium mb-4">
            <CheckCircle2 size={18} /> Pipeline complete
            {emp && <Link to={`/employees/${emp.id}`} className="ml-auto btn-ghost !py-1 !px-3 text-xs">View {emp.id} →</Link>}
          </div>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <div className="label">Extracted profile {result.result?.extraction_method === 'fallback' && <span className="normal-case text-gray-500">(heuristic — no LLM key)</span>}</div>
              <div><span className="text-gray-500">Name:</span> <span className="text-white">{rd?.name}</span></div>
              <div><span className="text-gray-500">Email:</span> <span className="text-gray-200">{rd?.email || '—'}</span></div>
              <div><span className="text-gray-500">Role:</span> <span className="text-gray-200">{rd?.role || '—'}</span></div>
              <div><span className="text-gray-500">Department:</span> <span className="text-gray-200">{rd?.department || '—'}</span></div>
              <div><span className="text-gray-500">Experience:</span> <span className="text-gray-200">{rd?.experience || '—'}</span></div>
              <div><span className="text-gray-500">Education:</span> <span className="text-gray-200">{rd?.education || '—'}</span></div>
              {rd?.skills?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {rd.skills.map(s => <span key={s} className="badge bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">{s}</span>)}
                </div>
              )}
            </div>
            <div className="space-y-2">
              <div className="label">Agent messages</div>
              {result.messages?.filter(m => m.agent !== 'Supervisor').map((m, i) => (
                <div key={i} className="bg-panel border border-edge rounded-lg p-3">
                  <div className="text-xs text-indigo-300 font-medium mb-1">{m.agent}</div>
                  <div className="text-xs text-gray-300">{m.content}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <h2 className="font-semibold text-white mt-8 mb-3">Processed Resumes</h2>
      <div className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-edge">
              <th className="px-5 py-3">File</th>
              <th className="px-5 py-3">Employee</th>
              <th className="px-5 py-3">Extraction</th>
              <th className="px-5 py-3">Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {(resumes || []).map(r => (
              <tr key={r.id} className="border-b border-edge/50 hover:bg-panel/60">
                <td className="px-5 py-3 text-gray-200">
                  <div className="flex items-center gap-2"><FileText size={14} className="text-gray-500" />{r.filename}</div>
                </td>
                <td className="px-5 py-3">
                  {r.employee_id
                    ? <Link to={`/employees/${r.employee_id}`} className="text-indigo-300 hover:text-indigo-200">{r.extracted_data?.name || r.employee_id}</Link>
                    : <span className="text-gray-500">—</span>}
                </td>
                <td className="px-5 py-3"><StatusBadge status={r.extraction_method === 'llm' ? 'COMPLETED' : 'TODO'} /> <span className="text-xs text-gray-500 ml-1">{r.extraction_method}</span></td>
                <td className="px-5 py-3 text-gray-400 text-xs">{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {resumes?.length === 0 && (
              <tr><td colSpan={4} className="px-5 py-10 text-center text-gray-500">No resumes uploaded yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
