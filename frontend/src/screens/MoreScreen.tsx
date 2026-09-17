import { Link, useNavigate } from 'react-router'

import { useAuth, useSession } from '../auth/context'
import { Button } from '../components/Button'
import { Card } from '../components/Card'

export function MoreScreen() {
  const session = useSession()
  const { signOut } = useAuth()
  const navigate = useNavigate()
  const isOwner = session.user.role === 'owner'

  const links = [
    ...(isOwner
      ? [
          { to: '/payroll', label: 'Payroll', hint: 'Daily hours for your accountant' },
          { to: '/setup', label: 'Setup and billing', hint: 'Business details, zones, seats' },
          { to: '/zones', label: 'Shop zones', hint: 'Where staff can clock in' },
        ]
      : []),
    { to: '/shift', label: 'My shift', hint: 'Start or end your own shift' },
    { to: '/hours', label: 'My hours', hint: 'What you have worked' },
    ...(isOwner ? [] : [{ to: '/availability', label: 'My availability', hint: 'Days you can work' }]),
    { to: '/profile', label: 'Profile', hint: session.user.email },
  ]

  return (
    <section className="grid max-w-lg gap-4">
      <h1 className="font-display text-3xl font-bold tracking-tight">More</h1>

      <Card className="divide-y divide-line-soft">
        {links.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className="flex items-center justify-between gap-3 px-4 py-4 hover:bg-line-soft"
          >
            <span>
              <span className="block font-medium">{link.label}</span>
              <span className="block truncate text-sm text-muted">{link.hint}</span>
            </span>
            <span aria-hidden="true" className="text-muted">
              ›
            </span>
          </Link>
        ))}
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
    </section>
  )
}
