import { useRef, useState } from 'react'
import { Send, Bot, User, BookOpen, FileText } from 'lucide-react'
import { queryPolicy, errMsg } from '../services/api'
import { PageHeader } from '../components/ui'

const SUGGESTIONS = [
  'How many casual leave days can I take?',
  'When is manager approval required for leave?',
  'What is the work from home policy for new hires?',
  'What are the standard working hours?',
  'What security training must new employees complete?',
]

export default function Policies() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef()

  const ask = async question => {
    const q = (question ?? input).trim()
    if (!q || busy) return
    setInput('')
    setMessages(m => [...m, { role: 'user', content: q }])
    setBusy(true)
    try {
      const res = await queryPolicy(q)
      setMessages(m => [...m, { role: 'assistant', content: res.answer, sources: res.sources }])
    } catch (e) {
      setMessages(m => [...m, { role: 'assistant', error: errMsg(e) }])
    } finally {
      setBusy(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <PageHeader title="HR Policy Assistant" subtitle="Grounded answers from company policy documents via FAISS + Gemini embeddings — no hallucinations" />

      <div className="card !p-0 flex flex-col h-[65vh]">
        <div className="px-5 py-3 border-b border-edge flex items-center gap-2">
          <Bot size={16} className="text-indigo-400" />
          <span className="text-sm font-medium text-white">Policy Agent</span>
          <span className="text-xs text-gray-500 ml-auto">RAG over backend/data/policies/</span>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <BookOpen size={36} className="text-gray-600 mb-3" />
              <div className="text-gray-400 text-sm mb-4">Ask anything about company policy. Try:</div>
              <div className="flex flex-wrap gap-2 justify-center max-w-md">
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => ask(s)}
                          className="text-xs px-3 py-1.5 rounded-full bg-panel border border-edge text-gray-300 hover:border-accent/50 hover:text-white">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
              {m.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center shrink-0">
                  <Bot size={15} className="text-indigo-300" />
                </div>
              )}
              <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                m.role === 'user' ? 'bg-accent/20 border border-accent/30 text-white' : 'bg-panel border border-edge text-gray-200'
              }`}>
                <div className="whitespace-pre-wrap">{m.error ? <span className="text-red-300">{m.error}</span> : m.content}</div>
                {m.sources?.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-edge/60">
                    <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">Sources</div>
                    <div className="flex flex-wrap gap-1.5">
                      {[...new Set(m.sources.map(s => s.source))].map(src => (
                        <span key={src} className="badge bg-base border border-edge text-gray-400">
                          <FileText size={10} /> {src}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              {m.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-panel border border-edge flex items-center justify-center shrink-0">
                  <User size={15} className="text-gray-400" />
                </div>
              )}
            </div>
          ))}
          {busy && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center shrink-0">
                <Bot size={15} className="text-indigo-300 animate-pulse" />
              </div>
              <div className="bg-panel border border-edge rounded-xl px-4 py-3 text-sm text-gray-500">Retrieving policy…</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form
          className="p-4 border-t border-edge flex gap-2"
          onSubmit={e => { e.preventDefault(); ask() }}
        >
          <input
            className="input flex-1"
            placeholder="Ask HR policy…"
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={busy}
          />
          <button className="btn-primary" disabled={busy || !input.trim()}>
            <Send size={15} /> Send
          </button>
        </form>
      </div>
    </div>
  )
}
