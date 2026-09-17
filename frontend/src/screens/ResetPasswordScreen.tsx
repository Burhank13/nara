import { useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { Logo } from '../components/AppShell'
import { Button } from '../components/Button'
import { Field } from '../components/Field'
import { ApiError, request } from '../lib/api'

const MIN_PASSWORD = 10

type Preview = { email: string; full_name: string }

export function ResetPasswordScreen() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Checked up front so a dead link says so immediately, rather than after typing a password.
  const preview = useQuery({
    queryKey: ['reset', token],
    queryFn: () => request<Preview>(`/auth/reset/${token}`),
    retry: false,
  })

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await request<void>('/auth/reset-password', { method: 'POST', body: { token, password } })
      navigate('/login', { replace: true, state: { reset: true } })
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'Could not set that password. Try again.',
      )
      setBusy(false)
    }
  }

  if (preview.isPending) return <Shell>{null}</Shell>

  if (preview.isError) {
    return (
      <Shell>
        <h1 className="font-display text-3xl font-bold tracking-tight">This link has expired</h1>
        <p className="mt-2 text-muted">
          {preview.error instanceof ApiError
            ? preview.error.message
            : 'Ask for a new link and try again.'}
        </p>
        <Link to="/forgot" className="mt-4 inline-block text-sm text-teal underline underline-offset-4">
          Send me a new link
        </Link>
      </Shell>
    )
  }

  return (
    <Shell>
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">Set a new password</h1>
        <p className="mt-2 text-muted">For {preview.data.email}.</p>
      </div>

      <form className="mt-7 grid gap-4" onSubmit={onSubmit}>
        <Field
          label="New password"
          htmlFor="password"
          hint={`At least ${MIN_PASSWORD} characters. This signs you out on your other devices.`}
        >
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

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        <Button type="submit" full disabled={busy || password.length < MIN_PASSWORD}>
          {busy ? 'Saving…' : 'Save password'}
        </Button>
      </form>
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center gap-7 px-5 py-10">
      <Logo />
      <div>{children}</div>
    </main>
  )
}
