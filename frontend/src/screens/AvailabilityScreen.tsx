import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { ApiError, request } from '../lib/api'
import { WEEKDAYS } from '../lib/format'
import type { AvailabilityDay } from '../lib/types'

type Row = { enabled: boolean; start: string; end: string }

const DEFAULT_ROW: Row = { enabled: false, start: '09:00', end: '17:00' }

function toRows(days: AvailabilityDay[]): Row[] {
  return WEEKDAYS.map((_, weekday) => {
    const day = days.find((entry) => entry.weekday === weekday)
    return day
      ? { enabled: true, start: day.start_time.slice(0, 5), end: day.end_time.slice(0, 5) }
      : { ...DEFAULT_ROW }
  })
}

export function AvailabilityScreen() {
  const { data } = useQuery({
    queryKey: ['availability', 'mine'],
    queryFn: () => request<{ days: AvailabilityDay[] }>('/availability/mine'),
  })

  return (
    <section className="grid max-w-2xl gap-4">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">My availability</h1>
        <p className="mt-1 text-muted">
          The days and hours you can work. Your manager sees this when planning the week.
        </p>
      </div>

      {/* The editor mounts once the saved week is known, so it starts from the real values
          without an effect copying data into state. */}
      {data ? <Editor saved={data.days} /> : <Card className="p-5 text-sm text-muted">Loading…</Card>}
    </section>
  )
}

function Editor({ saved }: { saved: AvailabilityDay[] }) {
  const queryClient = useQueryClient()
  const [rows, setRows] = useState<Row[]>(() => toRows(saved))
  const [error, setError] = useState<string | null>(null)
  const [justSaved, setJustSaved] = useState(false)

  const save = useMutation({
    mutationFn: () =>
      request<{ days: AvailabilityDay[] }>('/availability/mine', {
        method: 'PUT',
        body: {
          days: rows
            .map((row, weekday) => ({ ...row, weekday }))
            .filter((row) => row.enabled)
            .map((row) => ({ weekday: row.weekday, start_time: row.start, end_time: row.end })),
        },
      }),
    onSuccess: () => {
      setError(null)
      setJustSaved(true)
      queryClient.invalidateQueries({ queryKey: ['availability'] })
    },
    onError: (caught) =>
      setError(
        caught instanceof ApiError && caught.code !== 'invalid_request'
          ? caught.message
          : 'Each finish time has to be after its start time.',
      ),
  })

  function update(weekday: number, patch: Partial<Row>) {
    setJustSaved(false)
    setRows((current) =>
      current.map((row, index) => (index === weekday ? { ...row, ...patch } : row)),
    )
  }

  return (
    <>
      <Card className="divide-y divide-line-soft">
        {rows.map((row, weekday) => (
          <div key={WEEKDAYS[weekday]} className="flex flex-wrap items-center gap-3 px-4 py-3">
            <label className="flex min-w-28 flex-1 items-center gap-3 font-medium">
              <input
                type="checkbox"
                className="h-5 w-5 accent-[#0e6b5c]"
                checked={row.enabled}
                onChange={(event) => update(weekday, { enabled: event.target.checked })}
              />
              {WEEKDAYS[weekday]}
            </label>

            {row.enabled ? (
              <span className="flex items-center gap-2">
                <input
                  type="time"
                  aria-label={`${WEEKDAYS[weekday]} start`}
                  className="input tabular w-32"
                  value={row.start}
                  onChange={(event) => update(weekday, { start: event.target.value })}
                />
                <span className="text-muted">to</span>
                <input
                  type="time"
                  aria-label={`${WEEKDAYS[weekday]} finish`}
                  className="input tabular w-32"
                  value={row.end}
                  onChange={(event) => update(weekday, { end: event.target.value })}
                />
              </span>
            ) : (
              <span className="text-sm text-muted">Not available</span>
            )}
          </div>
        ))}
      </Card>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <div className="flex items-center gap-3">
        <Button onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save availability'}
        </Button>
        {justSaved && <span className="text-sm text-teal">Saved.</span>}
      </div>
    </>
  )
}
