import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import { useSession } from '../auth/context'
import { Button } from '../components/Button'
import { Card, Notice, StatCard } from '../components/Card'
import { HoursPanel } from '../components/HoursPanel'
import { ZoneMap } from '../components/ZoneMap'
import { ApiError, request } from '../lib/api'
import { distance, elapsed, hours, longDate, time } from '../lib/format'
import { readPosition, useGeolocation, type Fix } from '../lib/geolocation'
import type { Shift, ShiftPeriod, Zone } from '../lib/types'
import { nearestZone } from '../lib/zones'

const MAX_ACCURACY_M = 100

export function ShiftScreen() {
  const session = useSession()
  const timeZone = session.business.timezone
  const queryClient = useQueryClient()
  const [now, setNow] = useState(() => Date.now())
  const [failure, setFailure] = useState<string | null>(null)

  const current = useQuery({
    queryKey: ['shift', 'current'],
    queryFn: () => request<{ shift: Shift | null }>('/shifts/current'),
  })
  const zones = useQuery({ queryKey: ['locations'], queryFn: () => request<Zone[]>('/locations') })
  const week = useQuery({
    queryKey: ['shifts', 'week'],
    queryFn: () => request<ShiftPeriod>('/shifts/mine?period=week'),
  })

  const openShift = current.data?.shift ?? null
  const { state: geo, retry } = useGeolocation(!openShift)

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const check = useMemo(
    () => (geo.status === 'located' && zones.data ? nearestZone(geo.fix, zones.data) : null),
    [geo, zones.data],
  )

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['shift'] })
    queryClient.invalidateQueries({ queryKey: ['shifts'] })
  }

  const startShift = useMutation({
    mutationFn: (fix: Fix) => request<Shift>('/shifts/start', { method: 'POST', body: fix }),
    onSuccess: () => {
      setFailure(null)
      refresh()
    },
    onError: (error) => setFailure(error instanceof ApiError ? error.message : 'Could not start.'),
  })

  const endShift = useMutation({
    mutationFn: async () => {
      // Location is best-effort here: a refusal must never block the end of a shift.
      const fix = await readPosition()
      return request<Shift>('/shifts/end', { method: 'POST', body: fix ?? {} })
    },
    onSuccess: () => {
      setFailure(null)
      refresh()
    },
    onError: (error) => setFailure(error instanceof ApiError ? error.message : 'Could not end.'),
  })

  const accurate = geo.status === 'located' && geo.fix.accuracy_m <= MAX_ACCURACY_M
  const canStart = Boolean(check?.inside) && accurate && !startShift.isPending

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] lg:items-start">
      <div className="grid gap-4">
        <header>
          <p className="text-[13px] tracking-wide text-muted uppercase">
            {longDate(new Date(now), timeZone)} · {time(new Date(now).toISOString(), timeZone)}
          </p>
          <h1 className="mt-1 text-4xl font-bold tracking-tight">
            {openShift ? 'On shift' : `Hi ${session.user.full_name.split(' ')[0]}`}
          </h1>
        </header>

        {openShift ? (
          <OnShift
            shift={openShift}
            now={now}
            timeZone={timeZone}
            weekHours={week.data?.total_hours ?? 0}
            onEnd={() => endShift.mutate()}
            ending={endShift.isPending}
          />
        ) : (
          <Idle
            zonesLoaded={zones.isSuccess}
            zoneCount={zones.data?.length ?? 0}
            geo={geo}
            check={check}
            accurate={accurate}
            canStart={canStart}
            starting={startShift.isPending}
            onRetry={retry}
            onStart={() => geo.status === 'located' && startShift.mutate(geo.fix)}
          />
        )}

        {failure && <Notice>{failure}</Notice>}

        {!openShift && (
          <div className="grid grid-cols-2 gap-3">
            <StatCard label="This week" value={hours(week.data?.total_hours ?? 0)} unit="h" />
            <StatCard
              label="Shifts this week"
              value={String(week.data?.shift_count ?? 0)}
              hint={week.data?.shift_count === 1 ? 'shift logged' : 'shifts logged'}
            />
          </div>
        )}
      </div>

      <div className="hidden lg:block">
        <HoursPanel timeZone={timeZone} />
      </div>
    </div>
  )
}

function OnShift({
  shift,
  now,
  timeZone,
  weekHours,
  onEnd,
  ending,
}: {
  shift: Shift
  now: number
  timeZone: string
  weekHours: number
  onEnd: () => void
  ending: boolean
}) {
  return (
    <>
      <div className="rounded-2xl bg-ink px-6 py-7 text-center text-white">
        <p className="text-sm text-white/70">Time on this shift</p>
        <p className="tabular mt-2 text-5xl font-bold sm:text-6xl">
          {elapsed(shift.started_at, now)}
        </p>
        <p className="mt-3 text-sm text-white/70">
          Started {time(shift.started_at, timeZone)}
          {shift.location_name ? ` at ${shift.location_name}` : ''}
        </p>
      </div>

      <Card className="divide-y divide-line-soft">
        <Row label="Start check">
          <span className="text-teal">✓ In zone · {distance(shift.start_distance_m)}</span>
        </Row>
        <Row label="This week incl. today">
          <span className="tabular">{hours(weekHours)} h</span>
        </Row>
      </Card>

      <Button variant="danger" size="lg" full onClick={onEnd} disabled={ending}>
        {ending ? 'Ending…' : 'End shift'}
      </Button>
      <p className="text-center text-sm text-muted">
        You can end your shift from anywhere. Your location is saved with the end time.
      </p>
    </>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 text-[15px]">
      <span className="text-muted">{label}</span>
      {children}
    </div>
  )
}

type GeoState = ReturnType<typeof useGeolocation>['state']

function Idle({
  zonesLoaded,
  zoneCount,
  geo,
  check,
  accurate,
  canStart,
  starting,
  onRetry,
  onStart,
}: {
  zonesLoaded: boolean
  zoneCount: number
  geo: GeoState
  check: ReturnType<typeof nearestZone>
  accurate: boolean
  canStart: boolean
  starting: boolean
  onRetry: () => void
  onStart: () => void
}) {
  return (
    <>
      <Card className="overflow-hidden">
        <ZoneMap
          distanceM={check?.distanceM ?? null}
          radiusM={check?.zone.radius_m ?? 150}
          bearing={check?.bearing}
        />
        <div className="flex items-start gap-3 border-t border-line px-4 py-4">
          <StatusDot
            ok={Boolean(check?.inside) && accurate}
            pending={geo.status === 'locating' || !zonesLoaded}
          />
          <div>
            <p className="font-display text-lg font-bold">
              {headline(geo, check, accurate, zonesLoaded)}
            </p>
            <p className="mt-0.5 text-sm text-muted">{detail(geo, check)}</p>
          </div>
        </div>
      </Card>

      {zonesLoaded && zoneCount === 0 && (
        <Notice>The owner hasn't set up a shop zone yet, so shifts can't be started.</Notice>
      )}

      {geo.status === 'denied' && (
        <Notice>
          MAF needs your location to check you're at the shop. Turn location on for this site in
          your browser settings, then{' '}
          <button className="underline underline-offset-2" onClick={onRetry}>
            try again
          </button>
          .
        </Notice>
      )}

      {geo.status === 'located' && !accurate && (
        <Notice>
          Your location is only accurate to ±{Math.round(geo.fix.accuracy_m)} m. On a laptop this
          comes from Wi-Fi and can be far out — use your phone for a reliable check.
        </Notice>
      )}

      <Button size="lg" full onClick={onStart} disabled={!canStart}>
        {starting ? 'Starting…' : 'Start shift'}
      </Button>
      <p className="text-center text-sm text-muted">
        Your location is checked only when you start or end a shift.
      </p>
    </>
  )
}

function StatusDot({ ok, pending }: { ok: boolean; pending: boolean }) {
  const tone = pending ? 'bg-line text-muted' : ok ? 'bg-teal-soft text-teal' : 'bg-amber-soft text-amber'
  return (
    <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full text-lg ${tone}`}>
      {pending ? '…' : ok ? '✓' : '!'}
    </span>
  )
}

function headline(
  geo: GeoState,
  check: ReturnType<typeof nearestZone>,
  accurate: boolean,
  zonesLoaded: boolean,
): string {
  if (geo.status === 'locating') return 'Finding your location…'
  if (geo.status === 'denied') return 'Location is switched off'
  if (geo.status === 'unsupported') return 'This device has no location'
  if (geo.status === 'unavailable') return "Couldn't get your location"
  // Zones still in flight is not the same as none existing: saying "no zone" here tells an owner
  // who just drew one that it never saved.
  if (!zonesLoaded) return 'Checking the shop zone…'
  if (!check) return 'No shop zone set up'
  if (!accurate) return 'Location is not accurate enough'
  return check.inside ? `You're at ${check.zone.name}` : `You're too far from ${check.zone.name}`
}

function detail(geo: GeoState, check: ReturnType<typeof nearestZone>): string {
  if (geo.status === 'unavailable') return geo.message
  if (geo.status !== 'located' || !check) return 'Your shift can start once you are inside the zone.'
  return `${distance(check.distanceM)} from the shop · GPS ±${Math.round(geo.fix.accuracy_m)} m`
}
