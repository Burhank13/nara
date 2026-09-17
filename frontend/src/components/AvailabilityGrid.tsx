import { useState } from 'react'

import { WEEKDAYS, windowLabel } from '../lib/format'
import type { TeamAvailability } from '../lib/types'
import { Card } from './Card'

/**
 * The whole week at a glance on a desktop; on a phone you pick a day and see who is free,
 * because seven columns of pills is unreadable at 390 px.
 */
export function AvailabilityGrid({ data }: { data: TeamAvailability }) {
  const [day, setDay] = useState(() => (new Date().getDay() + 6) % 7)

  if (data.members.length === 0) {
    return (
      <Card className="p-5">
        <p className="text-sm text-muted">No staff have joined yet.</p>
      </Card>
    )
  }

  const freeToday = data.members
    .map((member) => ({ member, window: member.days.find((entry) => entry.weekday === day) }))
    .filter((row) => row.window)

  return (
    <Card>
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <h2 className="font-display text-xl font-bold">Availability this week</h2>
        <span className="text-sm text-muted">Set by staff</span>
      </div>

      <div className="hidden overflow-x-auto border-t border-line-soft lg:block">
        <table className="w-full text-left">
          <thead>
            <tr className="text-xs tracking-wide text-muted uppercase">
              <th className="px-4 py-2 font-semibold">Person</th>
              {WEEKDAYS.map((label) => (
                <th key={label} className="px-2 py-2 text-center font-semibold">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.members.map((member) => (
              <tr key={member.user_id} className="border-t border-line-soft">
                <td className="px-4 py-2 font-medium whitespace-nowrap">{member.full_name}</td>
                {WEEKDAYS.map((label, weekday) => {
                  const window = member.days.find((entry) => entry.weekday === weekday)
                  return (
                    <td key={label} className="px-1.5 py-2">
                      <span
                        className={[
                          'tabular block rounded-lg py-1.5 text-center text-xs',
                          window
                            ? 'bg-teal-soft text-teal-deep'
                            : 'border border-dashed border-line text-transparent',
                        ].join(' ')}
                      >
                        {window ? windowLabel(window.start_time, window.end_time) : '·'}
                      </span>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border-t border-line-soft lg:hidden">
        <div className="flex gap-1 overflow-x-auto px-3 py-3">
          {WEEKDAYS.map((label, weekday) => (
            <button
              key={label}
              onClick={() => setDay(weekday)}
              aria-pressed={day === weekday}
              className={[
                'min-h-10 flex-1 rounded-lg px-2 text-sm font-medium',
                day === weekday ? 'bg-ink text-white' : 'bg-line-soft text-muted',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>

        {freeToday.length === 0 ? (
          <p className="px-4 pb-4 text-sm text-muted">Nobody has marked themselves free.</p>
        ) : (
          <ul className="divide-y divide-line-soft border-t border-line-soft">
            {freeToday.map(({ member, window }) => (
              <li key={member.user_id} className="flex items-center justify-between px-4 py-3">
                <span className="font-medium">{member.full_name}</span>
                <span className="tabular rounded-lg bg-teal-soft px-2.5 py-1 text-sm text-teal-deep">
                  {windowLabel(window!.start_time, window!.end_time)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}
