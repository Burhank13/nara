import type { ReactNode } from 'react'
import { NavLink } from 'react-router'

import { useAuth } from '../auth/context'
import { initials } from '../lib/format'

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
  hours: (
    <>
      <path d="M5 20V10M12 20V4M19 20v-7" />
    </>
  ),
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
      <path d="M17 8.5a3 3 0 1 0 0-1M18 20c0-2.5-1-4.2-2.5-5.2" />
    </>
  ),
  zone: (
    <>
      <path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
} as const

export type TabKey = keyof typeof ICONS

export type Tab = { to: string; label: string; icon: TabKey }

export function Logo() {
  return (
    <span className="flex items-center gap-2">
      <Icon path={ICONS.shift} className="h-6 w-6 text-teal" />
      <span className="font-display text-xl font-bold tracking-tight">nara</span>
    </span>
  )
}

export function AppShell({ tabs, children }: { tabs: Tab[]; children: ReactNode }) {
  const { session } = useAuth()

  return (
    <div className="min-h-dvh bg-paper">
      <header className="hidden border-b border-line bg-surface sm:block">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          <Logo />
          <nav className="flex items-center gap-1">
            {tabs.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={({ isActive }) =>
                  [
                    'rounded-lg px-3 py-2 text-[15px] font-medium transition-colors',
                    isActive ? 'bg-teal-soft text-teal-deep' : 'text-muted hover:text-ink',
                  ].join(' ')
                }
              >
                {tab.label}
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

      <main className="mx-auto w-full max-w-6xl px-4 pt-5 pb-28 sm:px-6 sm:pb-10">{children}</main>

      <nav
        className="fixed inset-x-0 bottom-0 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] sm:hidden"
        aria-label="Sections"
      >
        <div
          className="grid"
          style={{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }}
        >
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
