import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { Logo } from '../components/AppShell'
import { Button } from '../components/Button'
import { Field } from '../components/Field'
import { request } from '../lib/api'

export function ForgotPasswordScreen() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      await request<void>('/auth/forgot-password', { method: 'POST', body: { email } })
    } finally {
      // Shown whatever happened: telling someone the address is unknown would be a way to
      // find out who has an account.
      setSent(true)
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center gap-8 px-5 py-10">
      <Logo />

      {sent ? (
        <>
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight">Check your email</h1>
            <p className="mt-2 text-muted">
              If {email} has an account, a link to set a new password is on its way. It works once
              and expires in an hour.
            </p>
          </div>
          <p className="text-sm text-muted">
            Nothing arrived? Check the spam folder, or ask your manager to confirm the address on
            your account.
          </p>
          <Link to="/login" className="text-sm text-teal underline underline-offset-4">
            Back to sign in
          </Link>
        </>
      ) : (
        <>
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight">Forgot your password?</h1>
            <p className="mt-1 text-muted">We'll email you a link to set a new one.</p>
          </div>

          <form className="grid gap-4" onSubmit={onSubmit}>
            <Field label="Email" htmlFor="email">
              <input
                id="email"
                type="email"
                className="input"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>

            <Button type="submit" full disabled={busy}>
              {busy ? 'Sending…' : 'Email me a link'}
            </Button>

            <Link to="/login" className="text-center text-sm text-teal underline underline-offset-4">
              Back to sign in
            </Link>
          </form>
        </>
      )}
    </main>
  )
}
