import { Cpu, Database, Sparkles, AlertTriangle } from 'lucide-react'
import { getAgentStatus } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { Loading, ErrorBox, PageHeader } from '../components/ui'

function Row({ ok, label, value }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-edge/50 last:border-0">
      <span className="text-sm text-gray-300">{label}</span>
      <span className={`text-sm font-mono ${ok ? 'text-emerald-300' : 'text-amber-300'}`}>{value}</span>
    </div>
  )
}

export default function Settings() {
  const { data, loading, error } = useFetch(getAgentStatus)

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} />

  return (
    <div className="max-w-2xl">
      <PageHeader title="Settings" subtitle="System health and LLM configuration" />

      {!data.llm_enabled && (
        <div className="card border-amber-500/40 bg-amber-500/5 flex gap-3 text-amber-200 mb-4">
          <AlertTriangle size={18} className="shrink-0 mt-0.5" />
          <div className="text-sm">
            <span className="font-medium">GEMINI_API_KEY is not configured.</span>{' '}
            The system runs in deterministic fallback mode: resume extraction uses heuristics and
            policy answers quote retrieved documents directly. Add the key to
            <code className="mx-1 px-1.5 py-0.5 bg-base border border-edge rounded">backend/.env</code>
            and restart the backend to enable Gemini reasoning + FAISS embeddings.
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="font-semibold text-white flex items-center gap-2 mb-2">
          <Cpu size={16} className="text-indigo-400" /> Agent Runtime
        </h2>
        <Row ok label="LLM enabled" value={data.llm_enabled ? 'yes' : 'no (fallback mode)'} />
        <Row ok={!!data.llm_model} label="Chat model" value={data.llm_model || '—'} />
        <Row ok={!!data.embedding_model} label="Embedding model" value={data.embedding_model || '—'} />
        <Row ok={data.vector_store_ready} label="FAISS vector store" value={data.vector_store_ready ? 'ready' : 'not built'} />
        <Row ok label="Retrieval mode" value={data.retrieval_mode} />
      </div>

      <div className="card mt-4">
        <h2 className="font-semibold text-white flex items-center gap-2 mb-2">
          <Database size={16} className="text-indigo-400" /> Storage
        </h2>
        <Row ok label="Database" value="SQLite (backend/data/onboarding.db)" />
        <Row ok label="Graph checkpoints" value="SQLite (backend/data/checkpoints.db)" />
        <Row ok label="Policy documents" value="backend/data/policies/*.txt" />
      </div>

      <div className="card mt-4">
        <h2 className="font-semibold text-white flex items-center gap-2 mb-2">
          <Sparkles size={16} className="text-indigo-400" /> Agents
        </h2>
        {[
          ['Supervisor', 'Routes requests via LangGraph conditional edges'],
          ['ResumeAgent', 'PDF → structured profile → employee record'],
          ['OnboardingAgent', 'Role-aware task plan generation'],
          ['CalendarAgent', 'Mock calendar with availability & conflict checks'],
          ['LeaveAgent', 'Deterministic leave rules + human-in-the-loop approval'],
          ['PolicyAgent', 'FAISS/Gemini RAG with grounded answers'],
        ].map(([name, desc]) => (
          <Row key={name} ok label={name} value={desc} />
        ))}
      </div>
    </div>
  )
}
