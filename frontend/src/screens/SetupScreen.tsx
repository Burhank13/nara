import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { useAuth, useSession } from '../auth/context'
import { Button } from '../components/Button'
import { Card, Notice } from '../components/Card'
import { Field } from '../components/Field'
import { ApiError, request, type Session } from '../lib/api'
import { readPosition } from '../lib/geolocation'
import type { Onboarding, OnboardingStep, Zone } from '../lib/types'

type StepKey = OnboardingStep['key']

const ORDER: StepKey[] = ['details', 'zones', 'staff', 'billing']

export function SetupScreen() {
  const { data, refetch } = useQuery({
    queryKey: ['onboarding'],
    queryFn: () => request<Onboarding>('/business/onboarding'),
  })
  const [step, setStep] = useState<StepKey | null>(null)

  if (!data) return <p className="p-6 text-muted">Loading…</p>

  const current = step ?? data.next_step ?? 'details'
  const index = ORDER.indexOf(current)

  const advance = async () => {
    await refetch()
    setStep(ORDER[Math.min(index + 1, ORDER.length - 1)])
  }

  return (
    <section className="mx-auto grid w-full max-w-2xl gap-5">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">Set up your shop</h1>
        <p className="mt-1 text-muted">
          About 15 minutes. You can stop at any point — what you've saved stays saved.
        </p>
      </div>

      <ol className="grid gap-2">
        {data.steps.map((entry, position) => (
          <li key={entry.key}>
            <button
              onClick={() => setStep(entry.key)}
              aria-current={entry.key === current ? 'step' : undefined}
              className={[
                'flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors',
                entry.key === current ? 'border-teal bg-teal-soft' : 'border-line bg-surface',
              ].join(' ')}
            >
              <span
                className={[
                  'grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold',
                  entry.done ? 'bg-teal text-white' : 'bg-line-soft text-muted',
                ].join(' ')}
              >
                {entry.done ? '✓' : position + 1}
              </span>
              <span className="min-w-0">
                <span className="block font-semibold">
                  {entry.title}
                  {entry.optional && <span className="ml-2 text-xs text-muted">Optional</span>}
                </span>
                <span className="block truncate text-sm text-muted">{entry.description}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>

      {current === 'details' && <DetailsStep onDone={advance} />}
      {current === 'zones' && <ZoneStep onDone={advance} />}
      {current === 'staff' && <StaffStep onDone={advance} />}
      {current === 'billing' && <BillingStep onboarding={data} />}
    </section>
  )
}

function DetailsStep({ onDone }: { onDone: () => void }) {
  const session = useSession()
  const { adopt } = useAuth()
  const [name, setName] = useState(session.business.name)
  const [abn, setAbn] = useState(session.business.abn ?? '')
  const [timezone, setTimezone] = useState(session.business.timezone)
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () =>
      request<Session['business']>('/business', {
        method: 'PATCH',
        body: { name, abn, timezone },
      }),
    onSuccess: (business) => {
      adopt({ ...session, business })
      onDone()
    },
    onError: (caught) =>
      setError(
        caught instanceof ApiError && caught.code !== 'invalid_request'
          ? caught.message
          : "Check the ABN — it's 11 digits and has a check digit.",
      ),
  })

  return (
    <Card className="grid gap-4 p-5">
      <h2 className="font-display text-xl font-bold">Business details</h2>

      <Field label="Business name" htmlFor="setup-name">
        <input
          id="setup-name"
          className="input"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </Field>

      <Field label="ABN" htmlFor="setup-abn" hint="11 digits. Used on your invoices.">
        <input
          id="setup-abn"
          className="input tabular"
          inputMode="numeric"
          placeholder="51 824 753 556"
          value={abn}
          onChange={(event) => setAbn(event.target.value)}
        />
      </Field>

      <Field
        label="Time zone"
        htmlFor="setup-tz"
        hint="Weeks and fortnights are counted in this zone."
      >
        <select
          id="setup-tz"
          className="input"
          value={timezone}
          onChange={(event) => setTimezone(event.target.value)}
        >
          {[
            'Australia/Sydney',
            'Australia/Melbourne',
            'Australia/Brisbane',
            'Australia/Adelaide',
            'Australia/Perth',
            'Australia/Hobart',
            'Australia/Darwin',
          ].map((zone) => (
            <option key={zone} value={zone}>
              {zone.replace('Australia/', '')}
            </option>
          ))}
        </select>
      </Field>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <Button onClick={() => save.mutate()} disabled={save.isPending || abn.trim() === ''}>
        {save.isPending ? 'Saving…' : 'Save and continue'}
      </Button>
    </Card>
  )
}

function ZoneStep({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient()
  const zones = useQuery({ queryKey: ['locations'], queryFn: () => request<Zone[]>('/locations') })
  const [name, setName] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [radius, setRadius] = useState(150)
  const [error, setError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () =>
      request<Zone>('/locations', {
        method: 'POST',
        body: { name, latitude: Number(latitude), longitude: Number(longitude), radius_m: radius },
      }),
    onSuccess: () => {
      setName('')
      setLatitude('')
      setLongitude('')
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['locations'] })
    },
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Could not save that zone.'),
  })

  async function useMyLocation() {
    const fix = await readPosition()
    if (!fix) {
      setError("Couldn't read your location. Type the coordinates instead.")
      return
    }
    setLatitude(fix.latitude.toFixed(6))
    setLongitude(fix.longitude.toFixed(6))
    setError(null)
  }

  const saved = zones.data ?? []

  return (
    <Card className="grid gap-4 p-5">
      <h2 className="font-display text-xl font-bold">Shop zones</h2>
      <p className="text-sm text-muted">
        Stand in the shop and tap “Use my location” — that is the most accurate pin you can get.
      </p>

      {saved.map((zone) => (
        <div key={zone.id} className="rounded-xl bg-line-soft px-4 py-3">
          <p className="font-semibold">{zone.name}</p>
          <p className="tabular text-sm text-muted">
            {zone.latitude.toFixed(5)}, {zone.longitude.toFixed(5)} · {zone.radius_m} m
          </p>
        </div>
      ))}

      <Field label="Location name" htmlFor="setup-zone-name">
        <input
          id="setup-zone-name"
          className="input"
          placeholder="Harbour St Car Wash"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Latitude" htmlFor="setup-lat">
          <input
            id="setup-lat"
            className="input tabular"
            inputMode="decimal"
            value={latitude}
            onChange={(event) => setLatitude(event.target.value)}
          />
        </Field>
        <Field label="Longitude" htmlFor="setup-lng">
          <input
            id="setup-lng"
            className="input tabular"
            inputMode="decimal"
            value={longitude}
            onChange={(event) => setLongitude(event.target.value)}
          />
        </Field>
      </div>

      <Button variant="secondary" onClick={useMyLocation}>
        Use my location
      </Button>

      <Field label={`Radius — ${radius} m`} htmlFor="setup-radius" hint="Most shops use 100–200 m.">
        <input
          id="setup-radius"
          type="range"
          min={50}
          max={300}
          step={10}
          value={radius}
          onChange={(event) => setRadius(Number(event.target.value))}
          className="w-full accent-[#0e6b5c]"
        />
      </Field>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <Button
          onClick={() => create.mutate()}
          disabled={create.isPending || !name.trim() || !latitude || !longitude}
        >
          {create.isPending ? 'Saving…' : 'Add zone'}
        </Button>
        <Button variant="secondary" onClick={onDone} disabled={saved.length === 0}>
          Continue
        </Button>
      </div>
    </Card>
  )
}

function StaffStep({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<'employee' | 'manager'>('employee')
  const [link, setLink] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const send = useMutation({
    mutationFn: () =>
      request<{ invite_url: string }>('/team/invites', {
        method: 'POST',
        body: { email, full_name: fullName, role },
      }),
    onSuccess: (invited) => {
      setLink(invited.invite_url)
      setEmail('')
      setFullName('')
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['team'] })
    },
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Could not send that invite.'),
  })

  return (
    <Card className="grid gap-4 p-5">
      <h2 className="font-display text-xl font-bold">Add your team</h2>
      <p className="text-sm text-muted">
        Invites last 7 days. Each person takes a seat once they accept.
      </p>

      <Field label="Their name" htmlFor="setup-staff-name">
        <input
          id="setup-staff-name"
          className="input"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
        />
      </Field>

      <Field label="Their email" htmlFor="setup-staff-email">
        <input
          id="setup-staff-email"
          type="email"
          className="input"
          autoComplete="off"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </Field>

      <Field
        label="Role"
        htmlFor="setup-staff-role"
        hint="A manager can also see who's on shift and the availability grid."
      >
        <select
          id="setup-staff-role"
          className="input"
          value={role}
          onChange={(event) => setRole(event.target.value as 'employee' | 'manager')}
        >
          <option value="employee">Employee</option>
          <option value="manager">Manager</option>
        </select>
      </Field>

      {link && (
        <Notice tone="teal">
          <p className="font-semibold">Invite ready</p>
          <p className="mt-1 break-all">{link}</p>
          <button
            className="mt-2 underline underline-offset-4"
            onClick={() => navigator.clipboard?.writeText(link)}
          >
            Copy link
          </button>
        </Notice>
      )}

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <Button
          onClick={() => send.mutate()}
          disabled={send.isPending || !email.trim() || !fullName.trim()}
        >
          {send.isPending ? 'Inviting…' : 'Send invite'}
        </Button>
        <Button variant="secondary" onClick={onDone}>
          Continue
        </Button>
      </div>
    </Card>
  )
}

function BillingStep({ onboarding }: { onboarding: Onboarding }) {
  const navigate = useNavigate()

  return (
    <Card className="grid gap-4 p-5">
      <h2 className="font-display text-xl font-bold">Seats and payment</h2>

      <div className="rounded-xl bg-line-soft p-4">
        <p className="tabular text-2xl font-bold">
          {onboarding.seats_used} / {onboarding.seat_limit} <span className="text-base">seats</span>
        </p>
        <p className="mt-1 text-sm text-muted">
          {onboarding.days_left === null
            ? 'Your plan is active.'
            : `${onboarding.days_left} ${onboarding.days_left === 1 ? 'day' : 'days'} left on your trial. No card needed until then.`}
        </p>
      </div>

      <Notice>
        Card payment isn't connected yet, so keep going on the trial for now. Your shop, zones and
        team are all set up and working.
      </Notice>

      <Button onClick={() => navigate('/overview')}>
        {onboarding.complete ? 'Finish setup' : 'Go to my dashboard'}
      </Button>
    </Card>
  )
}
