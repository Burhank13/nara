import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { useSession } from '../auth/context'
import { Button } from '../components/Button'
import { Card, Notice, StatCard } from '../components/Card'
import { PeriodTabs } from '../components/PeriodTabs'
import { ApiError, download, request } from '../lib/api'
import { clockTime, dayAndDate, hours, rangeLabel } from '../lib/format'
import type { Period } from '../lib/periods'
import type { Member, Payroll, Team } from '../lib/types'

export function PayrollScreen() {
  const session = useSession()
  const timeZone = session.business.timezone
  const [period, setPeriod] = useState<Period>('fortnight')
  const [exportError, setExportError] = useState<string | null>(null)

  const { data, isPending } = useQuery({
    queryKey: ['payroll', period],
    queryFn: () => request<Payroll>(`/payroll?period=${period}`),
  })

  async function exportCsv() {
    setExportError(null)
    try {
      await download(`/payroll/export.csv?period=${period}`, 'payroll.csv')
    } catch {
      setExportError('The export could not be downloaded. Try again.')
    }
  }

  return (
    <section className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">Payroll</h1>
          <p className="mt-1 text-muted">
            One line per person per day, ready for your accountant.
            {data && ` ${rangeLabel(data.starts_at, data.ends_at, timeZone)}.`}
          </p>
        </div>
        <Button variant="secondary" onClick={exportCsv} disabled={!data?.ready || data.lines.length === 0}>
          Export CSV
        </Button>
      </div>

      <PeriodTabs value={period} onChange={setPeriod} />

      {exportError && (
        <p role="alert" className="text-sm text-danger">
          {exportError}
        </p>
      )}

      {!data && <Card className="p-5 text-sm text-muted">{isPending ? 'Loading…' : 'No data.'}</Card>}

      {data && (
        <>
          {data.open_shifts.length > 0 && (
            <Notice>
              <p className="font-semibold">
                {data.open_shifts.length === 1 ? 'A shift has' : `${data.open_shifts.length} shifts have`}{' '}
                no finish time, so this run isn't ready.
              </p>
              <ul className="mt-1">
                {data.open_shifts.map((entry) => (
                  <li key={`${entry.full_name}-${entry.started_at}`}>
                    {entry.full_name} — started {dayAndDate(entry.started_at, timeZone)} at{' '}
                    {clockTime(entry.started_at, timeZone)}
                  </li>
                ))}
              </ul>
              <Link to="/timesheets" className="mt-2 inline-block underline underline-offset-4">
                Fix these in Timesheets
              </Link>
            </Notice>
          )}

          {data.missing_codes.length > 0 && (
            <Notice>
              No payroll code for {data.missing_codes.join(', ')}. Add one below so the import matches
              the right employee.
            </Notice>
          )}

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Total hours" value={hours(data.total_hours)} unit="h" />
            <StatCard label="Day lines" value={String(data.lines.length)} />
            <StatCard
              label="Rounding"
              value={data.rounding_minutes > 0 ? `${data.rounding_minutes}` : 'Off'}
              unit={data.rounding_minutes > 0 ? 'min' : undefined}
              hint={data.rounding_minutes > 0 ? 'Each day rounded to the nearest' : 'Exact times'}
            />
            <StatCard
              label="Status"
              value={data.ready ? 'Ready' : 'Held'}
              hint={data.ready ? 'Safe to export' : 'Close the open shifts'}
            />
          </div>

          {data.lines.length > 0 && (
            <Card className="overflow-hidden">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-line text-xs tracking-wide text-muted uppercase">
                    <th className="px-4 py-3 font-semibold">Employee</th>
                    <th className="hidden px-4 py-3 font-semibold sm:table-cell">Code</th>
                    <th className="px-4 py-3 font-semibold">Date</th>
                    <th className="px-4 py-3 text-right font-semibold">Hours</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lines.map((line) => (
                    <tr
                      key={`${line.user_id}-${line.work_date}`}
                      className="border-b border-line-soft last:border-0"
                    >
                      <td className="px-4 py-3 font-medium">
                        {line.full_name}
                        <span className="tabular block text-xs text-muted sm:hidden">
                          {line.payroll_code ?? 'No code'}
                        </span>
                      </td>
                      <td className="tabular hidden px-4 py-3 sm:table-cell">
                        {line.payroll_code ?? <span className="text-amber">Not set</span>}
                      </td>
                      <td className="px-4 py-3">{dayAndDate(line.work_date, timeZone)}</td>
                      <td className="tabular px-4 py-3 text-right font-semibold">{hours(line.hours)}</td>
                    </tr>
                  ))}
                  <tr className="font-semibold">
                    <td className="px-4 py-3" colSpan={3}>
                      Total
                    </td>
                    <td className="tabular px-4 py-3 text-right">{hours(data.total_hours)}</td>
                  </tr>
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}

      <PayrollCodes />
    </section>
  )
}

function PayrollCodes() {
  const team = useQuery({ queryKey: ['team'], queryFn: () => request<Team>('/team') })
  const staff = (team.data?.members ?? []).filter((member) => member.status !== 'archived')

  return (
    <Card className="p-5">
      <h2 className="font-display text-xl font-bold">Payroll codes</h2>
      <p className="mt-1 text-sm text-muted">
        How each person is identified in your payroll system. Leave blank if you match by name.
      </p>
      <ul className="mt-4 divide-y divide-line-soft">
        {staff.map((member) => (
          <CodeRow key={member.id} member={member} />
        ))}
      </ul>
    </Card>
  )
}

function CodeRow({ member }: { member: Member }) {
  const queryClient = useQueryClient()
  const [code, setCode] = useState(member.payroll_code ?? '')
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () =>
      request<Member>(`/team/members/${member.id}`, {
        method: 'PATCH',
        body: { payroll_code: code.trim() === '' ? null : code.trim() },
      }),
    onSuccess: () => {
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['team'] })
      queryClient.invalidateQueries({ queryKey: ['payroll'] })
    },
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Could not save that code.'),
  })

  const changed = code.trim() !== (member.payroll_code ?? '')

  return (
    <li className="flex flex-wrap items-center gap-3 py-3">
      <span className="min-w-36 flex-1 font-medium">{member.full_name}</span>
      <input
        className="input tabular w-40"
        placeholder="EMP-001"
        aria-label={`Payroll code for ${member.full_name}`}
        value={code}
        onChange={(event) => setCode(event.target.value)}
      />
      <Button variant="secondary" onClick={() => save.mutate()} disabled={!changed || save.isPending}>
        {save.isPending ? 'Saving…' : 'Save'}
      </Button>
      {error && (
        <p role="alert" className="w-full text-sm text-danger">
          {error}
        </p>
      )}
    </li>
  )
}
