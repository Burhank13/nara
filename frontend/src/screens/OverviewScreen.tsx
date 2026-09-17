import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import { useSession } from '../auth/context'
import { AvailabilityGrid } from '../components/AvailabilityGrid'
import { Card } from '../components/Card'
import { LiveBoard } from '../components/LiveBoard'
import { request } from '../lib/api'
import { hours, longDate, rangeLabel, time } from '../lib/format'
import type { Onboarding, Overview, TeamAvailability } from '../lib/types'

const PERIODS = ['week', 'fortnight', 'month'] as const
type Period = (typeof PERIODS)[number]
const LABELS: Record<Period, string> = {
  week: 'This week',
  fortnight: 'Last fortnight',
  month: 'Month',
}

const LIVE_REFRESH_MS = 15_000

export function OverviewScreen() {
  const session = useSession()
  const timeZone = session.business.timezone
  const [period, setPeriod] = useState<Period>('fortnight')
  const [now, setNow] = useState(() => Date.now())

  const overview = useQuery({
    queryKey: ['overview', period],
    queryFn: () => request<Overview>(`/overview?period=${period}`),
    // The board is "live" by polling; no websocket needed at this size.
    refetchInterval: LIVE_REFRESH_MS,
  })
  const availability = useQuery({
    queryKey: ['availability', 'team'],
    queryFn: () => request<TeamAvailability>('/availability/team'),
  })

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000)
    return () => clearInterval(id)
  }, [])

  const data = overview.data

  return (
    <div className="grid gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[13px] tracking-wide text-muted uppercase">
            Overview · {longDate(new Date(now), timeZone)}
          </p>
          <h1 className="mt-1 font-display text-3xl font-bold tracking-tight">
            {session.business.name}
          </h1>
        </div>
        <div className="flex rounded-xl bg-line-soft p-1">
          {PERIODS.map((option) => (
            <button
              key={option}
              onClick={() => setPeriod(option)}
              aria-pressed={period === option}
              className={[
                'min-h-9 rounded-lg px-3 text-sm font-medium transition-colors',
                period === option ? 'bg-surface text-ink shadow-sm' : 'text-muted hover:text-ink',
              ].join(' ')}
            >
              {LABELS[option]}
            </button>
          ))}
        </div>
      </header>

      <SetupPrompt />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi
          label="Employees"
          value={String(data?.staff_count ?? 0)}
          hint={`${data?.active_count ?? 0} active · ${data?.invited_count ?? 0} invites pending`}
        />
        <Kpi
          label="On shift now"
          value={String(data?.on_shift.length ?? 0)}
          hint={`Updated ${time(new Date(now).toISOString(), timeZone)}`}
          tone="teal"
        />
        <Kpi
          label="Team hours"
          value={hours(data?.team_hours ?? 0)}
          unit="h"
          hint={
            data ? `${rangeLabel(data.starts_at, data.ends_at, timeZone)} · ${data.shift_count} shifts` : ''
          }
        />
        <Kpi
          label="Needs attention"
          value={String(data?.needs_attention.length ?? 0)}
          hint={
            data?.needs_attention.length
              ? `${data.needs_attention[0].full_name}: shift still open`
              : 'Nothing to fix'
          }
          tone={data?.needs_attention.length ? 'amber' : 'plain'}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2 xl:items-start">
        <LiveBoard
          shifts={data?.on_shift ?? []}
          staffCount={data?.staff_count ?? 0}
          timeZone={timeZone}
          now={now}
        />
        {availability.data && <AvailabilityGrid data={availability.data} />}
      </div>

      <Card>
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <h2 className="font-display text-xl font-bold">Hours by employee</h2>
          <span className="text-sm text-muted">
            {data ? rangeLabel(data.starts_at, data.ends_at, timeZone) : ''}
          </span>
        </div>

        {data && data.hours_by_employee.length > 0 ? (
          <ul className="divide-y divide-line-soft border-t border-line-soft">
            {data.hours_by_employee.map((row) => (
              <li key={row.user_id} className="px-4 py-3">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-medium">{row.full_name}</span>
                  <span className="tabular text-lg font-semibold">{hours(row.hours)}</span>
                </div>
                <div className="mt-2 flex items-center gap-3">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-line-soft">
                    <div
                      className="h-full rounded-full bg-teal"
                      style={{ width: `${percent(row.hours, data.hours_by_employee[0].hours)}%` }}
                    />
                  </div>
                  <span className={`shrink-0 text-xs ${row.flagged ? 'text-amber' : 'text-muted'}`}>
                    {row.flagged ? 'Open shift' : `${row.shift_count} shifts`}
                  </span>
                </div>
              </li>
            ))}
            <li className="flex items-baseline justify-between px-4 py-3 font-semibold">
              <span>All {data.hours_by_employee.length} employees</span>
              <span className="tabular">{hours(data.team_hours)} h</span>
            </li>
          </ul>
        ) : (
          <p className="border-t border-line-soft px-4 py-6 text-sm text-muted">
            No shifts logged in this period yet.
          </p>
        )}
      </Card>
    </div>
  )
}

function percent(value: number, max: number): number {
  return max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0
}

function Kpi({
  label,
  value,
  unit,
  hint,
  tone = 'plain',
}: {
  label: string
  value: string
  unit?: string
  hint?: string
  tone?: 'plain' | 'teal' | 'amber'
}) {
  const tones = {
    plain: 'border-line bg-surface',
    teal: 'border-line bg-surface',
    amber: 'border-amber/30 bg-amber-soft',
  }
  const values = { plain: '', teal: 'text-teal', amber: 'text-amber' }

  return (
    <div className={`rounded-2xl border p-4 ${tones[tone]}`}>
      <p className="text-[13px] text-muted">{label}</p>
      <p className={`tabular mt-1 text-3xl leading-none font-bold ${values[tone]}`}>
        {value}
        {unit && <span className="ml-1 text-lg">{unit}</span>}
      </p>
      {hint && <p className="mt-2 text-xs leading-snug text-muted">{hint}</p>}
    </div>
  )
}

/** The first-day nudge: it disappears on its own once the required steps are actually done. */
function SetupPrompt() {
  const { data } = useQuery({
    queryKey: ['onboarding'],
    queryFn: () => request<Onboarding>('/business/onboarding'),
  })

  if (!data || data.complete) return null
  const remaining = data.steps.filter((step) => !step.done && !step.optional)

  return (
    <Card className="flex flex-wrap items-center justify-between gap-3 border-teal/30 bg-teal-soft p-4">
      <div>
        <p className="font-display text-lg font-bold text-teal-deep">Finish setting up</p>
        <p className="text-sm text-teal-deep/80">
          {remaining.length} {remaining.length === 1 ? 'step' : 'steps'} left:{' '}
          {remaining.map((step) => step.title.toLowerCase()).join(', ')}.
        </p>
      </div>
      <Link
        to="/setup"
        className="inline-flex min-h-11 items-center rounded-xl bg-teal px-5 font-semibold text-white"
      >
        Continue setup
      </Link>
    </Card>
  )
}
