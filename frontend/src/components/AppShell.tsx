import type { ReactNode } from 'react'
import { NavLink } from 'react-router'

import { useAuth } from '../auth/context'
import { initials } from '../lib/format'
import { AccountBanner } from './AccountBanner'

function Icon({ path, className = 'h-5 w-5' }: { path: ReactNode; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {path}
    </svg>
  )
}

const ICONS = {
  shift: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  hours: <path d="M5 20V10M12 20V4M19 20v-7" />,
  availability: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 11h18" />
    </>
  ),
  profile: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
    </>
  ),
  team: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5" />
      <path d="M16.5 5.6a3 3 0 0 1 0 5.8M18 20c0-2.5-1-4.2-2.5-5.2" />
    </>
  ),
  zone: (
    <>
      <path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  overview: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  timesheet: (
    <>
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="M8 8h8M8 12h8M8 16h5" />
    </>
  ),
  payroll: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v10M14.5 9.5c0-1-1.1-1.6-2.5-1.6s-2.5.6-2.5 1.7 1.1 1.5 2.5 1.7 2.5.7 2.5 1.8-1.1 1.6-2.5 1.6-2.5-.6-2.5-1.6" />
    </>
  ),
  more: <path d="M4 7h16M4 12h16M4 17h16" />,
} as const

export type IconKey = keyof typeof ICONS
export type NavItem = { to: string; label: string; icon: IconKey }

export function Logo({ className = '' }: { className?: string }) {
  return (
    <span className={`flex items-center gap-2 ${className}`}>
      <Icon path={ICONS.shift} className="h-6 w-6 text-teal" />
      <span className="font-display text-xl font-bold tracking-tight">MAF</span>
    </span>
  )
}

function BusinessBadge({ inverted = false }: { inverted?: boolean }) {
  const { session } = useAuth()
  const role = session?.user.role === 'owner' ? 'Owner account' : session?.user.full_name

  return (
    <div className={`rounded-xl p-3 ${inverted ? 'bg-white/10' : 'bg-line-soft'}`}>
      <p className={`truncate text-sm font-semibold ${inverted ? 'text-white' : ''}`}>
        {session?.business.name}
      </p>
      <p className={`truncate text-xs ${inverted ? 'text-white/60' : 'text-muted'}`}>{role}</p>
    </div>
  )
}

export function AppShell({
  nav,
  tabs,
  variant = 'topbar',
  children,
}: {
  /** Full navigation, shown on desktop. */
  nav: NavItem[]
  /** The few that fit in the phone tab bar. */
  tabs: NavItem[]
  variant?: 'topbar' | 'sidebar'
  children: ReactNode
}) {
  const { session } = useAuth()

  return (
    <div className={`min-h-dvh bg-paper ${variant === 'sidebar' ? 'lg:flex' : ''}`}>
      {variant === 'sidebar' ? (
        <aside className="hidden w-56 shrink-0 flex-col gap-6 bg-ink p-5 lg:flex lg:min-h-dvh lg:sticky lg:top-0">
          <Logo className="text-white" />
          <nav className="flex flex-1 flex-col gap-1">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] font-medium transition-colors',
                    isActive ? 'bg-teal text-white' : 'text-white/70 hover:bg-white/10 hover:text-white',
                  ].join(' ')
                }
              >
                <Icon path={ICONS[item.icon]} />
                {item.label}
              </NavLink>
            ))}
          </nav>
          <BusinessBadge inverted />
        </aside>
      ) : (
        <header className="hidden border-b border-line bg-surface sm:block">
          <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
            <Logo />
            <nav className="flex items-center gap-1">
              {nav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      'rounded-lg px-3 py-2 text-[15px] font-medium transition-colors',
                      isActive ? 'bg-teal-soft text-teal-deep' : 'text-muted hover:text-ink',
                    ].join(' ')
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <div className="ml-auto flex items-center gap-3">
              <span className="text-sm text-muted">{session?.business.name}</span>
              <span className="grid h-9 w-9 place-items-center rounded-full bg-ink text-xs font-semibold text-white">
                {initials(session?.user.full_name ?? '')}
              </span>
            </div>
          </div>
        </header>
      )}

      <main
        className={
          variant === 'sidebar'
            ? 'w-full min-w-0 px-4 pt-5 pb-28 sm:px-6 lg:px-8 lg:pb-10'
            : 'mx-auto w-full max-w-6xl px-4 pt-5 pb-28 sm:px-6 sm:pb-10'
        }
      >
        <AccountBanner />
        {children}
      </main>

      <nav
        className={[
          'fixed inset-x-0 bottom-0 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)]',
          variant === 'sidebar' ? 'lg:hidden' : 'sm:hidden',
        ].join(' ')}
        aria-label="Sections"
      >
        <div className="grid" style={{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }}>
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                [
                  'flex min-h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium',
                  isActive ? 'text-teal' : 'text-muted',
                ].join(' ')
              }
            >
              <Icon path={ICONS[tab.icon]} />
              {tab.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
