import type { ReactNode } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router'

import { useAuth } from './auth/context'
import { AppShell, type Tab } from './components/AppShell'
import { AvailabilityScreen } from './screens/AvailabilityScreen'
import { HoursScreen } from './screens/HoursScreen'
import { JoinScreen } from './screens/JoinScreen'
import { LoginScreen } from './screens/LoginScreen'
import { ProfileScreen } from './screens/ProfileScreen'
import { ShiftScreen } from './screens/ShiftScreen'
import { ZonesScreen } from './screens/ZonesScreen'

const STAFF_TABS: Tab[] = [
  { to: '/shift', label: 'Shift', icon: 'shift' },
  { to: '/hours', label: 'Hours', icon: 'hours' },
  { to: '/availability', label: 'Availability', icon: 'availability' },
  { to: '/profile', label: 'Profile', icon: 'profile' },
]

const OWNER_TABS: Tab[] = [
  { to: '/zones', label: 'Zones', icon: 'zone' },
  { to: '/shift', label: 'My shift', icon: 'shift' },
  { to: '/hours', label: 'Hours', icon: 'hours' },
  { to: '/profile', label: 'Profile', icon: 'profile' },
]

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

function SignedInLayout() {
  const { session } = useAuth()
  const tabs = session?.user.role === 'owner' ? OWNER_TABS : STAFF_TABS

  return (
    <AppShell tabs={tabs}>
      <Outlet />
    </AppShell>
  )
}

function Landing() {
  const { session, loading } = useAuth()
  if (loading) return <Loading />
  if (!session) return <Navigate to="/login" replace />
  return <Navigate to={session.user.role === 'owner' ? '/zones' : '/shift'} replace />
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
        <Route path="/zones" element={<ZonesScreen />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
