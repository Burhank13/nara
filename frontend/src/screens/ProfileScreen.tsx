import { useNavigate } from 'react-router'

import { useAuth, useSession } from '../auth/context'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { initials } from '../lib/format'

const ROLES = { owner: 'Owner', manager: 'Manager', employee: 'Employee' } as const

export function ProfileScreen() {
  const session = useSession()
  const { signOut } = useAuth()
  const navigate = useNavigate()

  return (
    <section className="grid max-w-lg gap-5">
      <h1 className="font-display text-3xl font-bold tracking-tight">Profile</h1>

      <Card className="flex items-center gap-4 p-5">
        <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-ink text-lg font-semibold text-white">
          {initials(session.user.full_name)}
        </span>
        <div className="min-w-0">
          <p className="truncate font-display text-xl font-bold">{session.user.full_name}</p>
          <p className="truncate text-sm text-muted">{session.user.email}</p>
        </div>
      </Card>

      <Card className="divide-y divide-line-soft">
        <Detail label="Business" value={session.business.name} />
        <Detail label="Role" value={ROLES[session.user.role]} />
        <Detail label="Time zone" value={session.business.timezone} />
      </Card>

      <Button
        variant="secondary"
        full
        onClick={async () => {
          await signOut()
          navigate('/login', { replace: true })
        }}
      >
        Sign out
      </Button>

      <p className="text-sm text-muted">
        Your location is only recorded when you start or end a shift, never in between.
      </p>
    </section>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3">
      <span className="text-muted">{label}</span>
      <span className="truncate font-medium">{value}</span>
    </div>
  )
}
