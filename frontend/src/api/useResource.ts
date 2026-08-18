import { useCallback, useEffect, useState } from 'react'

import { ApiError, api } from './client'

interface Resource<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

/**
 * Loads a GET endpoint and re-runs when `path` changes.
 *
 * A null path means "not ready to ask yet" — it stays in the loading state
 * without firing a request. That is what a screen needs while it still does
 * not know which zone, or which id, it is about to load.
 *
 * Deliberately small: this project has no data-fetching library, and a handful
 * of admin screens does not justify one.
 */
export function useResource<T>(path: string | null): Resource<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  const reload = useCallback(() => setTick((value) => value + 1), [])

  useEffect(() => {
    if (path === null) {
      setLoading(true)
      return
    }

    let cancelled = false
    setLoading(true)

    api
      .get<T>(path)
      .then((result) => {
        if (cancelled) return
        setData(result)
        setError(null)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        // A 401 already told the auth layer to drop the session, which sends
        // the panel back to the login screen. Setting an error here too would
        // flash a message on the way out.
        if (cause instanceof ApiError && cause.status === 401) {
          setData(null)
          return
        }
        setError(cause instanceof Error ? cause.message : 'Error inesperado')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [path, tick])

  return { data, error, loading, reload }
}
