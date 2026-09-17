import { useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router'

import { useAuth } from '../auth/context'
import { Logo } from '../components/AppShell'
import { Button } from '../components/Button'
import { Field } from '../components/Field'
import { ApiError, request, type Session } from '../lib/api'
import { useGeolocation } from '../lib/geolocation'

const MIN_PASSWORD = 10

type Preview = {
  business_name: string
  invited_by: string | null
  email: string
  full_name: string
  role: 'manager' | 'employee'
  expires_at: string
}

export function JoinScreen() {
  const { token = '' } = useParams()
  const { adopt } = useAuth()
  const [joined, setJoined] = useState(false)

  const preview = useQuery({
    queryKey: ['invite', token],
    queryFn: () => request<Preview>(`/invites/${token}`),
    retry: false,
  })

  if (preview.isPending) {
    return <Shell>{null}</Shell>
  }

  if (preview.isError) {
    return (
      <Shell>
        <h1 className="font-display text-3xl font-bold tracking-tight">This invite has expired</h1>
        <p className="mt-2 text-muted">
          {preview.error instanceof ApiError
            ? preview.error.message
            : 'Ask your manager to send a new link.'}
        </p>
      </Shell>
    )
  }

  if (joined) return <AllowLocation />

  return <JoinForm token={token} preview={preview.data} adopt={adopt} onJoined={() => setJoined(true)} />
}

function Shell({ children, step }: { children: React.ReactNode; step?: string }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col gap-7 px-5 py-8">
      <div className="flex items-center justify-between">
        <Logo />
        {step && <span className="tabular text-sm text-muted">{step}</span>}
      </div>
      {children}
    </main>
  )
}

function JoinForm({
  token,
  preview,
  adopt,
  onJoined,
}: {
  token: string
  preview: Preview
  adopt: (session: Session) => void
  onJoined: () => void
}) {
  const [fullName, setFullName] = useState(preview.full_name)
  const [password, setPassword] = useState('')
  const [consented, setConsented] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const session = await request<Session>(`/invites/${token}/accept`, {
        method: 'POST',
        body: { full_name: fullName, password },
      })
      adopt(session)
      onJoined()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not join. Try again.')
      setBusy(false)
    }
  }

  const addedBy = preview.invited_by ? `${preview.invited_by} added you` : 'You have been added'

  return (
    <Shell step="Step 1 of 2">
      <div>
        <span className="grid h-16 w-16 place-items-center rounded-2xl bg-ink font-display text-2xl font-bold text-white">
          {preview.business_name.charAt(0).toUpperCase()}
        </span>
        <h1 className="mt-5 font-display text-3xl font-bold tracking-tight">
          Join {preview.business_name}
        </h1>
        <p className="mt-2 text-muted">
          {addedBy} as {preview.role === 'manager' ? 'a manager' : 'an employee'}. Set up your
          account to start logging shifts.
        </p>
      </div>

      <form className="grid gap-4" onSubmit={onSubmit}>
        <Field label="Email" htmlFor="email">
          <input id="email" className="input" value={preview.email} disabled />
        </Field>

        <Field label="Your name" htmlFor="name">
          <input
            id="name"
            className="input"
            autoComplete="name"
            required
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
        </Field>

        <Field label="Create a password" htmlFor="password" hint={`At least ${MIN_PASSWORD} characters`}>
          <input
            id="password"
            type="password"
            className="input"
            autoComplete="new-password"
            required
            minLength={MIN_PASSWORD}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>

        <label className="flex items-start gap-3 rounded-xl border border-line bg-surface p-4 text-sm">
          <input
            type="checkbox"
            className="mt-0.5 h-5 w-5 shrink-0 accent-[#0e6b5c]"
            checked={consented}
            onChange={(event) => setConsented(event.target.checked)}
          />
          <span>
            I understand my location is checked only when I start or end a shift, never in between.
          </span>
        </label>

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        <Button type="submit" size="lg" full disabled={busy || !consented || password.length < MIN_PASSWORD}>
          {busy ? 'Joining…' : 'Join team'}
        </Button>
      </form>

      <p className="text-center text-sm text-muted">
        Next: allow location, then add Nara to your home screen.
      </p>
    </Shell>
  )
}

function AllowLocation() {
  const navigate = useNavigate()
  const [asked, setAsked] = useState(false)
  const { state } = useGeolocation(asked)

  const granted = state.status === 'located'

  return (
    <Shell step="Step 2 of 2">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">Allow location</h1>
        <p className="mt-2 text-muted">
          Nara checks you're at the shop when you start a shift, and records where you were when you
          end one. It never tracks you in between.
        </p>
      </div>

      {granted ? (
        <p className="rounded-xl border border-teal/20 bg-teal-soft px-4 py-3 text-sm text-teal-deep">
          Location is on. You're ready to start shifts.
        </p>
      ) : (
        <Button size="lg" full onClick={() => setAsked(true)} disabled={state.status === 'locating' && asked}>
          {asked && state.status === 'locating' ? 'Asking…' : 'Allow location'}
        </Button>
      )}

      {state.status === 'denied' && (
        <p className="text-sm text-muted">
          Location is blocked for this site. You can turn it on in your browser settings whenever
          you're ready — you'll need it to start a shift.
        </p>
      )}

      <Button variant="secondary" full onClick={() => navigate('/shift', { replace: true })}>
        {granted ? 'Go to my shift' : 'Skip for now'}
      </Button>

      <p className="text-center text-sm text-muted">
        Tip: add Nara to your home screen from your browser's share menu, so it opens like an app.
      </p>
    </Shell>
  )
}
