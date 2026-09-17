import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { useSession } from '../auth/context'
import { Button } from '../components/Button'
import { Card, Notice, StatCard } from '../components/Card'
import { EditedNote } from '../components/EditedNote'
import { EditShiftSheet } from '../components/EditShiftSheet'
import { PeriodTabs } from '../components/PeriodTabs'
import { download, request } from '../lib/api'
import { clockTime, dayAndDate, hours, rangeLabel } from '../lib/format'
import type { Period } from '../lib/periods'
import type { Timesheet, TimesheetShift } from '../lib/types'

const ALL_STAFF = 'all'

export function TimesheetsScreen() {
  const session = useSession()
  const timeZone = session.business.timezone
  const [period, setPeriod] = useState<Period>('fortnight')
  const [staffId, setStaffId] = useState<string>(ALL_STAFF)
  const [editing, setEditing] = useState<TimesheetShift | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)

  const query = staffId === ALL_STAFF ? `period=${period}` : `period=${period}&user_id=${staffId}`
  const { data, isPending } = useQuery({
    queryKey: ['timesheet', period, staffId],
    queryFn: () => request<Timesheet>(`/timesheets?${query}`),
  })

  async function exportCsv() {
    setExportError(null)
    try {
      await download(`/timesheets/export.csv?${query}`, 'timesheet.csv')
    } catch {
      setExportError('The export could not be downloaded. Try again.')
    }
  }

  return (
    <section className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">Timesheets</h1>
          {data && (
            <p className="mt-1 text-muted">{rangeLabel(data.starts_at, data.ends_at, timeZone)}</p>
          )}
        </div>
        <Button variant="secondary" onClick={exportCsv} disabled={!data || data.shift_count === 0}>
          Export CSV
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <PeriodTabs value={period} onChange={setPeriod} />
        <label className="flex items-center gap-2 text-sm text-muted">
          <span className="sr-only sm:not-sr-only">Staff</span>
          <select
            className="input min-w-44"
            value={staffId}
            onChange={(event) => setStaffId(event.target.value)}
          >
            <option value={ALL_STAFF}>Everyone</option>
            {data?.staff.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.full_name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {exportError && (
        <p role="alert" className="text-sm text-danger">
          {exportError}
        </p>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Total hours" value={hours(data.total_hours)} unit="h" />
            <StatCard label="Shifts" value={String(data.shift_count)} />
            <StatCard label="People" value={String(data.hours_by_employee.length)} />
            <StatCard
              label="Still open"
              value={String(data.open_count)}
              hint={data.open_count > 0 ? 'Needs a finish time' : undefined}
            />
          </div>

          {data.open_count > 0 && (
            <Notice>
              {data.open_count === 1 ? 'One shift has' : `${data.open_count} shifts have`} no finish
              time. Edit the shift to set when they actually left, then export.
            </Notice>
          )}

          {data.shifts.length === 0 ? (
            <Card className="p-5 text-sm text-muted">No shifts in this period.</Card>
          ) : (
            <ShiftTable shifts={data.shifts} timeZone={timeZone} onEdit={setEditing} />
          )}

          {data.hours_by_employee.length > 0 && (
            <Card className="p-5">
              <h2 className="text-xs font-semibold tracking-wide text-muted uppercase">
                Totals by person
              </h2>
              <ul className="mt-3 divide-y divide-line-soft">
                {data.hours_by_employee.map((row) => (
                  <li key={row.user_id} className="flex items-baseline justify-between gap-4 py-2">
                    <span className="font-medium">{row.full_name}</span>
                    <span className="text-sm text-muted">
                      {row.shift_count} {row.shift_count === 1 ? 'shift' : 'shifts'}
                      <span className="tabular ml-3 text-base font-semibold text-ink">
                        {hours(row.hours)} h
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}

      {!data && <Card className="p-5 text-sm text-muted">{isPending ? 'Loading…' : 'No data.'}</Card>}

      {editing && (
        <EditShiftSheet shift={editing} timeZone={timeZone} onClose={() => setEditing(null)} />
      )}
    </section>
  )
}

function ShiftTable({
  shifts,
  timeZone,
  onEdit,
}: {
  shifts: TimesheetShift[]
  timeZone: string
  onEdit: (shift: TimesheetShift) => void
}) {
  return (
    <Card className="overflow-hidden">
      <ul className="divide-y divide-line-soft lg:hidden">
        {shifts.map((shift) => (
          <li key={shift.id} className="flex items-start justify-between gap-3 px-4 py-3">
            <div className="min-w-0">
              <p className="truncate font-semibold">{shift.full_name}</p>
              <p className="tabular mt-0.5 text-sm text-muted">
                {dayAndDate(shift.started_at, timeZone)} · {times(shift, timeZone)}
              </p>
              <EditedNote edits={shift.edits} />
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <span className="tabular text-lg font-semibold">{hoursCell(shift)}</span>
              <Button variant="ghost" onClick={() => onEdit(shift)}>
                Edit
              </Button>
            </div>
          </li>
        ))}
      </ul>

      <table className="hidden w-full text-left lg:table">
        <thead>
          <tr className="border-b border-line text-xs tracking-wide text-muted uppercase">
            <th className="px-4 py-3 font-semibold">Employee</th>
            <th className="px-4 py-3 font-semibold">Date</th>
            <th className="px-4 py-3 font-semibold">Start</th>
            <th className="px-4 py-3 font-semibold">Finish</th>
            <th className="px-4 py-3 text-right font-semibold">Hours</th>
            <th className="px-4 py-3 text-right font-semibold">
              <span className="sr-only">Edit</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {shifts.map((shift) => (
            <tr key={shift.id} className="border-b border-line-soft last:border-0">
              <td className="px-4 py-3 font-medium">
                {shift.full_name}
                <EditedNote edits={shift.edits} />
              </td>
              <td className="px-4 py-3">{dayAndDate(shift.started_at, timeZone)}</td>
              <td className="tabular px-4 py-3">{clockTime(shift.started_at, timeZone)}</td>
              <td className="tabular px-4 py-3">
                {shift.ended_at ? (
                  clockTime(shift.ended_at, timeZone)
                ) : (
                  <span className="text-amber">Open</span>
                )}
              </td>
              <td className="tabular px-4 py-3 text-right font-semibold">{hoursCell(shift)}</td>
              <td className="px-4 py-3 text-right">
                <Button variant="ghost" onClick={() => onEdit(shift)}>
                  Edit
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

function times(shift: TimesheetShift, timeZone: string): string {
  const start = clockTime(shift.started_at, timeZone)
  return shift.ended_at ? `${start}–${clockTime(shift.ended_at, timeZone)}` : `${start} – open`
}

function hoursCell(shift: TimesheetShift): string {
  return shift.status === 'open' ? '–' : hours(shift.hours)
}
