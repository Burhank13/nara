import { createContext, use } from 'react'

import type { Session } from '../lib/api'

export type AuthContextValue = {
  session: Session | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  adopt: (session: Session) => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = use(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

export function useSession(): Session {
  const { session } = useAuth()
  if (!session) throw new Error('useSession must be used inside a signed-in route')
  return session
}
