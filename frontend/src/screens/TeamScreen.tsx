import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '../components/Button'
import { Card, Notice } from '../components/Card'
import { Field } from '../components/Field'
import { ApiError, request } from '../lib/api'
import { initials } from '../lib/format'
import type { Member, Seats, Team } from '../lib/types'

const ROLES = { owner: 'Owner', manager: 'Manager', employee: 'Employee' } as const

export function TeamScreen() {
  const queryClient = useQueryClient()
  const team = useQuery({ queryKey: ['team'], queryFn: () => request<Team>('/team') })
  const [inviting, setInviting] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['team'] })

  const act = useMutation({
    mutationFn: ({ path, method }: { path: string; method: string }) =>
      request<unknown>(path, { method }),
    onSuccess: refresh,
  })

  const seats = team.data?.seats
  const full = seats ? seats.used >= seats.limit : false

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem] xl:items-start">
      <div className="grid gap-4">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-display text-3xl font-bold tracking-tight">People &amp; seats</h1>
          <Button onClick={() => setInviting(true)} disabled={full}>
            {full ? 'All seats in use' : 'Invite people'}
          </Button>
        </header>

        {seats && <SeatMeter seats={seats} />}

        {copied && <Notice tone="teal">Invite link copied. Paste it into a text or WhatsApp.</Notice>}

        <Card className="overflow-hidden">
          <ul className="divide-y divide-line-soft">
            {team.data?.members.map((member) => (
              <li key={member.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-line-soft text-xs font-semibold">
                  {initials(member.full_name)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold">{member.full_name}</p>
                  <p className="truncate text-sm text-muted">{member.email}</p>
                </div>
                <span className="text-sm text-muted">{ROLES[member.role]}</span>
                <StatusPill member={member} />
                <MemberActions
                  member={member}
                  busy={act.isPending}
                  onAction={(path, method) => act.mutate({ path, method })}
                />
              </li>
            ))}
          </ul>
        </Card>

        <p className="text-sm text-muted">
          A seat is one employee or manager who can clock in. The owner is free, and archiving
          someone frees their seat.
        </p>
      </div>

      {inviting && (
        <InvitePanel
          onClose={() => setInviting(false)}
          onInvited={(url) => {
            setCopied(url)
            refresh()
          }}
        />
      )}
    </div>
  )
}

function SeatMeter({ seats }: { seats: Seats }) {
  const ratio = seats.limit > 0 ? seats.used / seats.limit : 0
  const full = seats.used >= seats.limit
  const warn = ratio >= 0.8

  const tone = full
    ? 'border-amber/40 bg-amber-soft'
    : warn
      ? 'border-amber/30 bg-amber-soft'
      : 'border-line bg-surface'
  const bar = full || warn ? 'bg-amber' : 'bg-teal'

  return (
    <div className={`rounded-2xl border p-4 ${tone}`}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-semibold">{full ? 'All seats are in use' : 'Seats'}</span>
        <span className="tabular font-semibold">
          {seats.used} of {seats.limit} seats
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-line-soft">
        <div
          className={`h-full rounded-full ${bar}`}
          style={{ width: `${Math.min(100, Math.round(ratio * 100))}%` }}
        />
      </div>
      {full && (
        <p className="mt-2 text-sm text-[#6b3a06]">
          To invite someone new, archive a person who has left. Adding seats arrives with billing.
        </p>
      )}
    </div>
  )
}

function StatusPill({ member }: { member: Member }) {
  const styles = {
    active: 'bg-teal-soft text-teal-deep',
    invited: 'bg-amber-soft text-amber',
    archived: 'bg-line-soft text-muted',
  } as const

  const label =
    member.status === 'invited' && member.invite_expires_at
      ? `Invited · ${expiresIn(member.invite_expires_at)}`
      : member.status.charAt(0).toUpperCase() + member.status.slice(1)

  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles[member.status]}`}>
      {label}
    </span>
  )
}

function expiresIn(iso: string): string {
  const days = Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000)
  if (days <= 0) return 'expired'
  return days === 1 ? 'expires tomorrow' : `expires in ${days} days`
}

function MemberActions({
  member,
  busy,
  onAction,
}: {
  member: Member
  busy: boolean
  onAction: (path: string, method: string) => void
}) {
  if (member.role === 'owner') return <span className="text-xs text-muted">free</span>

  return (
    <span className="flex gap-2">
      {member.status === 'invited' && (
        <>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => onAction(`/team/members/${member.id}/resend`, 'POST')}
          >
            Resend
          </Button>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => onAction(`/team/members/${member.id}`, 'DELETE')}
          >
            Revoke
          </Button>
        </>
      )}
      {member.status === 'active' && (
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => onAction(`/team/members/${member.id}/archive`, 'POST')}
        >
          Archive
        </Button>
      )}
      {member.status === 'archived' && member.accepted_at && (
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => onAction(`/team/members/${member.id}/restore`, 'POST')}
        >
          Restore
        </Button>
      )}
    </span>
  )
}

function InvitePanel({
  onClose,
  onInvited,
}: {
  onClose: () => void
  onInvited: (url: string) => void
}) {
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<'employee' | 'manager'>('employee')
  const [error, setError] = useState<string | null>(null)
  const [link, setLink] = useState<string | null>(null)

  const invite = useMutation({
    mutationFn: () =>
      request<{ invite_url: string }>('/team/invites', {
        method: 'POST',
        body: { email, full_name: fullName, role },
      }),
    onSuccess: (result) => {
      setLink(result.invite_url)
      setError(null)
      setEmail('')
      setFullName('')
      onInvited(result.invite_url)
    },
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Could not send that invite.'),
  })

  return (
    <Card className="p-5 max-xl:fixed max-xl:inset-x-0 max-xl:bottom-0 max-xl:z-10 max-xl:rounded-b-none max-xl:pb-8 max-xl:shadow-2xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-bold">Invite someone</h2>
          <p className="mt-1 text-sm text-muted">
            They get a link that works once and expires in 7 days.
          </p>
        </div>
        <button onClick={onClose} aria-label="Close" className="min-h-11 px-2 text-xl text-muted">
          ×
        </button>
      </div>

      <div className="mt-4 grid gap-4">
        <Field label="Name" htmlFor="invite-name">
          <input
            id="invite-name"
            className="input"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
        </Field>
        <Field label="Email" htmlFor="invite-email">
          <input
            id="invite-email"
            type="email"
            className="input"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </Field>
        <Field label="Role" htmlFor="invite-role">
          <select
            id="invite-role"
            className="input"
            value={role}
            onChange={(event) => setRole(event.target.value as 'employee' | 'manager')}
          >
            <option value="employee">Employee</option>
            <option value="manager">Manager — can also see the team board</option>
          </select>
        </Field>

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        {link && (
          <div className="rounded-xl border border-line bg-line-soft p-3">
            <p className="text-xs font-semibold text-muted">Invite link</p>
            <p className="mt-1 break-all text-xs">{link}</p>
            <Button
              variant="secondary"
              className="mt-2"
              onClick={() => navigator.clipboard?.writeText(link)}
            >
              Copy link
            </Button>
          </div>
        )}

        <Button
          onClick={() => invite.mutate()}
          disabled={invite.isPending || !email || !fullName}
        >
          {invite.isPending ? 'Inviting…' : 'Send invite'}
        </Button>
        <p className="text-xs text-muted">
          Emailing the link automatically arrives with onboarding; for now, copy it across yourself.
        </p>
      </div>
    </Card>
  )
}
