import { useCallback, useEffect, useRef, useState } from 'react'

/** Fetch data with loading/error state and manual refetch. */
export function useFetch(fetcher, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await fetcherRef.current()
      setData(result)
      setError(null)
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => { load() }, [load])
  return { data, loading, error, refetch: load, setData }
}

/** Poll an endpoint every `intervalMs` (used by Agent Activity). */
export function usePoll(fetcher, intervalMs = 5000) {
  const [data, setData] = useState(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const result = await fetcherRef.current()
        if (alive) setData(result)
      } catch { /* keep last data on transient errors */ }
    }
    tick()
    const t = setInterval(tick, intervalMs)
    return () => { alive = false; clearInterval(t) }
  }, [intervalMs])

  return data
}
