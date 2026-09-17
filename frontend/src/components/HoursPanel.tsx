import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { request } from '../lib/api'
import { clockTime, dayAndDate, hours, rangeLabel } from '../lib/format'
import type { Period } from '../lib/periods'
import type { Shift, ShiftPeriod } from '../lib/types'
import { Card } from './Card'
import { EditedNote } from './EditedNote'
import { PeriodTabs } from './PeriodTabs'

export function HoursPanel({ timeZone, heading = 'My hours' }: { timeZone: string; heading?: string }) {
  const [period, setPeriod] = useState<Period>('week')
  const { data, isPending } = useQuery({
    queryKey: ['shifts', period],
    queryFn: () => request<ShiftPeriod>(`/shifts/mine?period=${period}`),
  })

  return (
    <section className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-2xl font-bold">{heading}</h2>
        <PeriodTabs value={period} onChange={setPeriod} />
      </div>

      <Card className="p-5">
        {data ? (
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <p className="text-sm text-muted">{rangeLabel(data.starts_at, data.ends_at, timeZone)}</p>
              <p className="tabular mt-1 text-4xl font-bold text-teal">
                {hours(data.total_hours)} <span className="text-2xl">h</span>
              </p>
            </div>
            <p className="text-sm text-muted">
              {data.shift_count} {data.shift_count === 1 ? 'shift' : 'shifts'}
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted">{isPending ? 'Loading…' : 'No hours yet.'}</p>
        )}
      </Card>

      {data && data.shifts.length > 0 && (
        <Card className="overflow-hidden">
          <ul className="divide-y divide-line-soft sm:hidden">
            {data.shifts.map((shift) => (
              <li key={shift.id} className="flex items-baseline justify-between gap-4 px-4 py-3">
                <div>
                  <p className="font-semibold">{dayAndDate(shift.started_at, timeZone)}</p>
                  <p className="tabular mt-0.5 text-sm text-muted">{times(shift, timeZone)}</p>
                  <EditedNote edits={shift.edits} />
                </div>
                <span className="tabular text-lg font-semibold">{hoursCell(shift)}</span>
              </li>
            ))}
          </ul>

          <table className="hidden w-full text-left sm:table">
            <thead>
              <tr className="border-b border-line text-xs tracking-wide text-muted uppercase">
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Start</th>
                <th className="px-4 py-3 font-semibold">End</th>
                <th className="px-4 py-3 text-right font-semibold">Hours</th>
              </tr>
            </thead>
            <tbody>
              {data.shifts.map((shift) => (
                <tr key={shift.id} className="border-b border-line-soft last:border-0">
                  <td className="px-4 py-3 font-medium">
                    {dayAndDate(shift.started_at, timeZone)}
                    <EditedNote edits={shift.edits} />
                  </td>
                  <td className="tabular px-4 py-3">{clockTime(shift.started_at, timeZone)}</td>
                  <td className="tabular px-4 py-3">
                    {shift.ended_at ? clockTime(shift.ended_at, timeZone) : '—'}
                  </td>
                  <td className="tabular px-4 py-3 text-right font-semibold">{hoursCell(shift)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  )
}

function times(shift: Shift, timeZone: string): string {
  const start = clockTime(shift.started_at, timeZone)
  return shift.ended_at ? `${start} – ${clockTime(shift.ended_at, timeZone)}` : `${start} – running`
}

function hoursCell(shift: Shift): string {
  return shift.status === 'open' ? '–' : hours(shift.hours)
}
