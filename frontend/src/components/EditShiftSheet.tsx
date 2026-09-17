import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { ApiError, request } from '../lib/api'
import { clockTime, dateInput, dayAndDate, timeInput } from '../lib/format'
import type { ShiftEdit, TimesheetShift } from '../lib/types'
import { Button } from './Button'
import { Field } from './Field'

const MIN_REASON = 4

function nextDay(date: string): string {
  const [year, month, day] = date.split('-').map(Number)
  const rolled = new Date(year, month - 1, day + 1)
  return [
    rolled.getFullYear(),
    String(rolled.getMonth() + 1).padStart(2, '0'),
    String(rolled.getDate()).padStart(2, '0'),
  ].join('-')
}

export function EditShiftSheet({
  shift,
  timeZone,
  onClose,
}: {
  shift: TimesheetShift
  timeZone: string
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [date, setDate] = useState(() => dateInput(shift.started_at, timeZone))
  const [start, setStart] = useState(() => timeInput(shift.started_at, timeZone))
  const [end, setEnd] = useState(() => (shift.ended_at ? timeInput(shift.ended_at, timeZone) : ''))
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () =>
      request<TimesheetShift>(`/shifts/${shift.id}`, {
        method: 'PATCH',
        body: {
          started_at: `${date}T${start}:00`,
          // A finish earlier than the start means the shift ran past midnight.
          ...(end ? { ended_at: `${end <= start ? nextDay(date) : date}T${end}:00` } : {}),
          reason: reason.trim(),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheet'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
      queryClient.invalidateQueries({ queryKey: ['shifts'] })
      onClose()
    },
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'That change could not be saved.'),
  })

  const ready = reason.trim().length >= MIN_REASON && date !== '' && start !== ''

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 p-0 sm:items-center sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={`Edit ${shift.full_name}'s shift`}
      onClick={(event) => event.target === event.currentTarget && onClose()}
    >
      <div className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-surface p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] sm:rounded-2xl sm:pb-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl font-bold tracking-tight">Edit shift</h2>
            <p className="mt-0.5 text-sm text-muted">
              {shift.full_name} · {dayAndDate(shift.started_at, timeZone)}
            </p>
          </div>
          <Button variant="secondary" onClick={onClose} aria-label="Close">
            Cancel
          </Button>
        </div>

        <div className="mt-5 grid gap-4">
          <Field label="Date" htmlFor="edit-date">
            <input
              id="edit-date"
              type="date"
              className="input tabular w-full"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Start" htmlFor="edit-start">
              <input
                id="edit-start"
                type="time"
                className="input tabular w-full"
                value={start}
                onChange={(event) => setStart(event.target.value)}
              />
            </Field>
            <Field
              label="Finish"
              htmlFor="edit-end"
              hint={shift.status === 'open' ? 'Setting this ends the shift' : undefined}
            >
              <input
                id="edit-end"
                type="time"
                className="input tabular w-full"
                value={end}
                onChange={(event) => setEnd(event.target.value)}
              />
            </Field>
          </div>

          <Field
            label="Reason"
            htmlFor="edit-reason"
            hint="Saved to the shift's history, and your staff can see it."
          >
            <textarea
              id="edit-reason"
              className="input min-h-20 w-full resize-y"
              placeholder="Forgot to clock out, left at 4pm"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </Field>

          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}

          <Button full disabled={!ready || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? 'Saving…' : 'Save change'}
          </Button>
        </div>

        {shift.edits.length > 0 && <History edits={shift.edits} timeZone={timeZone} />}
      </div>
    </div>
  )
}

function History({ edits, timeZone }: { edits: ShiftEdit[]; timeZone: string }) {
  return (
    <div className="mt-6 border-t border-line pt-4">
      <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">Edit history</h3>
      <ul className="mt-3 grid gap-3">
        {[...edits].reverse().map((edit) => (
          <li key={edit.id} className="text-sm">
            <p className="tabular text-muted">
              {clockTime(edit.previous_started_at, timeZone)}
              {edit.previous_ended_at ? `–${clockTime(edit.previous_ended_at, timeZone)}` : '–open'}
              {' → '}
              <span className="font-semibold text-ink">
                {clockTime(edit.new_started_at, timeZone)}
                {edit.new_ended_at ? `–${clockTime(edit.new_ended_at, timeZone)}` : '–open'}
              </span>
            </p>
            <p className="mt-0.5">{edit.reason}</p>
            <p className="mt-0.5 text-xs text-muted">
              {edit.edited_by} · {dayAndDate(edit.created_at, timeZone)}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
