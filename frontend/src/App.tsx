import type { ReactNode } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router'

import { useAuth } from './auth/context'
import { AppShell, type NavItem } from './components/AppShell'
import { AvailabilityScreen } from './screens/AvailabilityScreen'
import { BoardScreen } from './screens/BoardScreen'
import { HoursScreen } from './screens/HoursScreen'
import { JoinScreen } from './screens/JoinScreen'
import { LoginScreen } from './screens/LoginScreen'
import { MoreScreen } from './screens/MoreScreen'
import { OverviewScreen } from './screens/OverviewScreen'
import { PayrollScreen } from './screens/PayrollScreen'
import { ProfileScreen } from './screens/ProfileScreen'
import { SetupScreen } from './screens/SetupScreen'
import { ShiftScreen } from './screens/ShiftScreen'
import { TeamScreen } from './screens/TeamScreen'
import { TimesheetsScreen } from './screens/TimesheetsScreen'
import { ZonesScreen } from './screens/ZonesScreen'

type Role = 'owner' | 'manager' | 'employee'

const NAV: Record<Role, { nav: NavItem[]; tabs: NavItem[]; home: string }> = {
  owner: {
    nav: [
      { to: '/overview', label: 'Overview', icon: 'overview' },
      { to: '/timesheets', label: 'Timesheets', icon: 'timesheet' },
      { to: '/payroll', label: 'Payroll', icon: 'payroll' },
      { to: '/team', label: 'Team', icon: 'team' },
      { to: '/zones', label: 'Locations', icon: 'zone' },
      { to: '/shift', label: 'My shift', icon: 'shift' },
      { to: '/profile', label: 'Profile', icon: 'profile' },
    ],
    tabs: [
      { to: '/overview', label: 'Overview', icon: 'overview' },
      { to: '/timesheets', label: 'Timesheets', icon: 'timesheet' },
      { to: '/team', label: 'Team', icon: 'team' },
      { to: '/more', label: 'More', icon: 'more' },
    ],
    home: '/overview',
  },
  manager: {
    nav: [
      { to: '/shift', label: 'Shift', icon: 'shift' },
      { to: '/hours', label: 'Hours', icon: 'hours' },
      { to: '/board', label: 'Team', icon: 'team' },
      { to: '/availability', label: 'Availability', icon: 'availability' },
      { to: '/profile', label: 'Profile', icon: 'profile' },
    ],
    tabs: [
      { to: '/shift', label: 'Shift', icon: 'shift' },
      { to: '/hours', label: 'Hours', icon: 'hours' },
      { to: '/board', label: 'Team', icon: 'team' },
      { to: '/more', label: 'More', icon: 'more' },
    ],
    home: '/shift',
  },
  employee: {
    nav: [
      { to: '/shift', label: 'Shift', icon: 'shift' },
      { to: '/hours', label: 'Hours', icon: 'hours' },
      { to: '/availability', label: 'Availability', icon: 'availability' },
      { to: '/profile', label: 'Profile', icon: 'profile' },
    ],
    tabs: [
      { to: '/shift', label: 'Shift', icon: 'shift' },
      { to: '/hours', label: 'Hours', icon: 'hours' },
      { to: '/availability', label: 'Availability', icon: 'availability' },
      { to: '/profile', label: 'Profile', icon: 'profile' },
    ],
    home: '/shift',
  },
}

function Loading() {
  return (
    <div className="grid min-h-dvh place-items-center text-muted" aria-busy="true">
      Loading…
    </div>
  )
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth()
  const location = useLocation()

  if (loading) return <Loading />
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <>{children}</>
}

/** Owner-only pages send everyone else back to their own home. */
function OwnerOnly({ children }: { children: ReactNode }) {
  const { session } = useAuth()
  if (session && session.user.role !== 'owner') return <Navigate to={NAV[session.user.role].home} replace />
  return <>{children}</>
}

function SignedInLayout() {
  const { session } = useAuth()
  const role = (session?.user.role ?? 'employee') as Role
  const { nav, tabs } = NAV[role]

  return (
    <AppShell nav={nav} tabs={tabs} variant={role === 'owner' ? 'sidebar' : 'topbar'}>
      <Outlet />
    </AppShell>
  )
}

function Landing() {
  const { session, loading } = useAuth()
  if (loading) return <Loading />
  if (!session) return <Navigate to="/login" replace />
  return <Navigate to={NAV[session.user.role].home} replace />
}

export default function App() {
  const { session, loading } = useAuth()

  return (
    <Routes>
      <Route
        path="/login"
        element={!loading && session ? <Navigate to="/" replace /> : <LoginScreen />}
      />
      <Route path="/join/:token" element={<JoinScreen />} />
      <Route path="/" element={<Landing />} />

      <Route
        element={
          <RequireAuth>
            <SignedInLayout />
          </RequireAuth>
        }
      >
        <Route path="/shift" element={<ShiftScreen />} />
        <Route path="/hours" element={<HoursScreen />} />
        <Route path="/availability" element={<AvailabilityScreen />} />
        <Route path="/profile" element={<ProfileScreen />} />
        <Route path="/more" element={<MoreScreen />} />
        <Route path="/board" element={<BoardScreen />} />
        <Route
          path="/overview"
          element={
            <OwnerOnly>
              <OverviewScreen />
            </OwnerOnly>
          }
        />
        <Route
          path="/setup"
          element={
            <OwnerOnly>
              <SetupScreen />
            </OwnerOnly>
          }
        />
        <Route
          path="/timesheets"
          element={
            <OwnerOnly>
              <TimesheetsScreen />
            </OwnerOnly>
          }
        />
        <Route
          path="/payroll"
          element={
            <OwnerOnly>
              <PayrollScreen />
            </OwnerOnly>
          }
        />
        <Route
          path="/team"
          element={
            <OwnerOnly>
              <TeamScreen />
            </OwnerOnly>
          }
        />
        <Route
          path="/zones"
          element={
            <OwnerOnly>
              <ZonesScreen />
            </OwnerOnly>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
