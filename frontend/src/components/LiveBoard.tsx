import { Card } from './Card'
import { distance, duration, initials, time } from '../lib/format'
import type { LiveShift } from '../lib/types'

export function LiveBoard({
  shifts,
  staffCount,
  timeZone,
  now,
}: {
  shifts: LiveShift[]
  staffCount: number
  timeZone: string
  now: number
}) {
  return (
    <Card>
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <h2 className="font-display text-xl font-bold">On shift now</h2>
        <span className="tabular rounded-full bg-teal-soft px-3 py-1 text-sm text-teal-deep">
          {shifts.length} of {staffCount}
        </span>
      </div>

      {shifts.length === 0 ? (
        <p className="border-t border-line-soft px-4 py-6 text-sm text-muted">
          Nobody is on shift right now.
        </p>
      ) : (
        <ul className="divide-y divide-line-soft border-t border-line-soft">
          {shifts.map((shift) => (
            <li key={shift.shift_id} className="flex items-center gap-3 px-4 py-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-line-soft text-xs font-semibold">
                {initials(shift.full_name)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{shift.full_name}</p>
                <p className="truncate text-sm text-muted">
                  {shift.needs_attention ? (
                    <span className="text-amber">No clock-out since </span>
                  ) : (
                    <span className="text-teal">✓ </span>
                  )}
                  Started {time(shift.started_at, timeZone)} · {distance(shift.start_distance_m)} from
                  shop
                </p>
              </div>
              <span className="tabular shrink-0 font-semibold">
                {duration(shift.started_at, now)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
