import { useSession } from '../auth/context'
import { HoursPanel } from '../components/HoursPanel'

export function HoursScreen() {
  const session = useSession()
  return <HoursPanel timeZone={session.business.timezone} />
}
