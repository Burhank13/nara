import { Card } from '../components/Card'

export function AvailabilityScreen() {
  return (
    <section className="grid gap-4">
      <h1 className="font-display text-3xl font-bold tracking-tight">Availability</h1>
      <Card className="p-5">
        <p className="text-muted">
          Setting the days and hours you can work is next on the build plan. For now, tell your
          manager directly.
        </p>
      </Card>
    </section>
  )
}
