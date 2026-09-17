import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { renewSession, request, setAccessToken, type Session } from '../lib/api'
import { AuthContext } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  // The access token lives in memory only; the refresh cookie is what survives a reload.
  useEffect(() => {
    let cancelled = false
    renewSession().then((restored) => {
      if (cancelled) return
      setSession(restored)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const adopt = useCallback((next: Session) => {
    setAccessToken(next.access_token)
    setSession(next)
  }, [])

  const signIn = useCallback(
    async (email: string, password: string) => {
      const next = await request<Session>('/auth/login', {
        method: 'POST',
        body: { email, password },
      })
      adopt(next)
    },
    [adopt],
  )

  const signOut = useCallback(async () => {
    try {
      await request<void>('/auth/logout', { method: 'POST' })
    } finally {
      setAccessToken(null)
      setSession(null)
    }
  }, [])

  const value = useMemo(
    () => ({ session, loading, signIn, signOut, adopt }),
    [session, loading, signIn, signOut, adopt],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
