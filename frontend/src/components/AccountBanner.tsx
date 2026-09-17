import { Link } from 'react-router'

import { useAuth } from '../auth/context'
import type { Session } from '../lib/api'

type Business = Session['business']
type Tone = 'info' | 'warn' | 'stop'

const TONES: Record<Tone, string> = {
  info: 'bg-teal-soft text-teal-deep',
  warn: 'bg-amber-soft text-[#6b3a06]',
  stop: 'bg-danger text-white',
}

function daysLeft(deadline: string | null): number | null {
  if (!deadline) return null
  return Math.max(0, Math.ceil((new Date(deadline).getTime() - Date.now()) / 86_400_000))
}

/** A trial that runs out silently is how a shop loses a morning's timesheets. */
function message(business: Business, isOwner: boolean): { tone: Tone; text: string } | null {
  const left = daysLeft(business.grace_ends_at)

  switch (business.status) {
    case 'trialing':
      if (left === null || left > 3) return null
      return {
        tone: 'warn',
        text:
          left === 0
            ? 'Your trial ends today. Add a card to keep clocking in tomorrow.'
            : `Your trial ends in ${left} ${left === 1 ? 'day' : 'days'}.`,
      }
    case 'past_due':
      return {
        tone: 'warn',
        text: isOwner
          ? `That last payment didn't go through. Update your card within ${left ?? 0} ${left === 1 ? 'day' : 'days'} to stay open.`
          : 'There is a billing problem. Your owner has been notified.',
      }
    case 'read_only':
      return {
        tone: 'stop',
        text: isOwner
          ? 'Your trial has ended. Nobody can start a shift until you add a card.'
          : "New shifts are paused. Ask your owner to sort out the account — you can still end a shift you've started.",
      }
    case 'suspended':
    case 'cancelled':
      return {
        tone: 'stop',
        text: isOwner
          ? 'This account is suspended. Add a payment method to reopen it; your data is safe.'
          : 'This account is suspended. Ask your owner to reopen it.',
      }
    default:
      return null
  }
}

export function AccountBanner() {
  const { session } = useAuth()
  if (!session) return null

  const isOwner = session.user.role === 'owner'
  const notice = message(session.business, isOwner)
  if (!notice) return null

  return (
    <div className={`px-4 py-2.5 text-sm font-medium sm:px-6 ${TONES[notice.tone]}`} role="status">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2">
        <span>{notice.text}</span>
        {isOwner && (
          <Link to="/setup" className="shrink-0 underline underline-offset-4">
            Set up billing
          </Link>
        )}
      </div>
    </div>
  )
}
