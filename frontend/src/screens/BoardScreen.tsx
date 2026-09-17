import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { useSession } from '../auth/context'
import { AvailabilityGrid } from '../components/AvailabilityGrid'
import { LiveBoard } from '../components/LiveBoard'
import { request } from '../lib/api'
import type { LiveBoard as LiveBoardData, TeamAvailability } from '../lib/types'

const LIVE_REFRESH_MS = 15_000

/** The manager's read-only view of the team: who is on now, and who can work this week. */
export function BoardScreen() {
  const session = useSession()
  const [now, setNow] = useState(() => Date.now())

  const board = useQuery({
    queryKey: ['shifts', 'live'],
    queryFn: () => request<LiveBoardData>('/shifts/live'),
    refetchInterval: LIVE_REFRESH_MS,
  })
  const availability = useQuery({
    queryKey: ['availability', 'team'],
    queryFn: () => request<TeamAvailability>('/availability/team'),
  })

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="grid gap-4">
      <h1 className="font-display text-3xl font-bold tracking-tight">Team</h1>
      <LiveBoard
        shifts={board.data?.on_shift ?? []}
        staffCount={board.data?.staff_count ?? 0}
        timeZone={session.business.timezone}
        now={now}
      />
      {availability.data && <AvailabilityGrid data={availability.data} />}
    </div>
  )
}
