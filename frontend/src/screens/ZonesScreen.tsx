import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '../components/Button'
import { Card, Notice } from '../components/Card'
import { Field } from '../components/Field'
import { ApiError, request } from '../lib/api'
import { readPosition } from '../lib/geolocation'
import type { Zone } from '../lib/types'

const MIN_RADIUS = 50
const MAX_RADIUS = 300

export function ZonesScreen() {
  const queryClient = useQueryClient()
  const zones = useQuery({ queryKey: ['locations'], queryFn: () => request<Zone[]>('/locations') })

  const [name, setName] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [radius, setRadius] = useState(150)
  const [error, setError] = useState<string | null>(null)

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['locations'] })

  const create = useMutation({
    mutationFn: () =>
      request<Zone>('/locations', {
        method: 'POST',
        body: {
          name,
          latitude: Number(latitude),
          longitude: Number(longitude),
          radius_m: radius,
        },
      }),
    onSuccess: () => {
      setName('')
      setLatitude('')
      setLongitude('')
      setError(null)
      invalidate()
    },
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Could not save that zone.'),
  })

  const remove = useMutation({
    mutationFn: (id: string) => request<void>(`/locations/${id}`, { method: 'DELETE' }),
    onSuccess: invalidate,
  })

  async function useMyLocation() {
    const fix = await readPosition()
    if (!fix) {
      setError("Couldn't read your location. Type the coordinates instead.")
      return
    }
    setLatitude(fix.latitude.toFixed(6))
    setLongitude(fix.longitude.toFixed(6))
    setError(null)
  }

  const ready = name.trim() !== '' && latitude !== '' && longitude !== ''

  return (
    <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
      <section className="grid gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">Shop zones</h1>
          <p className="mt-1 text-muted">
            Staff can start a shift only inside one of these. They can end one from anywhere.
          </p>
        </div>

        {zones.data?.length === 0 && (
          <Notice>No zones yet. Add one below so your staff can clock in.</Notice>
        )}

        {zones.data?.map((zone) => (
          <Card key={zone.id} className="flex items-start justify-between gap-4 p-4">
            <div className="min-w-0">
              <p className="font-display text-lg font-bold">{zone.name}</p>
              <p className="tabular mt-1 text-sm text-muted">
                {zone.latitude.toFixed(5)}, {zone.longitude.toFixed(5)} · {zone.radius_m} m radius
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={() => remove.mutate(zone.id)}
              disabled={remove.isPending}
            >
              Remove
            </Button>
          </Card>
        ))}
      </section>

      <Card className="grid gap-4 p-5">
        <h2 className="font-display text-xl font-bold">Add a zone</h2>

        <Field label="Location name" htmlFor="zone-name">
          <input
            id="zone-name"
            className="input"
            placeholder="Harbour St Car Wash"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Latitude" htmlFor="zone-lat">
            <input
              id="zone-lat"
              className="input tabular"
              inputMode="decimal"
              value={latitude}
              onChange={(event) => setLatitude(event.target.value)}
            />
          </Field>
          <Field label="Longitude" htmlFor="zone-lng">
            <input
              id="zone-lng"
              className="input tabular"
              inputMode="decimal"
              value={longitude}
              onChange={(event) => setLongitude(event.target.value)}
            />
          </Field>
        </div>

        <Button variant="secondary" onClick={useMyLocation}>
          Use my current location
        </Button>

        <Field
          label={`Zone radius — ${radius} m`}
          htmlFor="zone-radius"
          hint="Most shops use 100–200 m. A smaller zone rejects more starts when phone GPS is weak."
        >
          <input
            id="zone-radius"
            type="range"
            min={MIN_RADIUS}
            max={MAX_RADIUS}
            step={10}
            value={radius}
            onChange={(event) => setRadius(Number(event.target.value))}
            className="w-full accent-[#0e6b5c]"
          />
        </Field>

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        <Button onClick={() => create.mutate()} disabled={!ready || create.isPending}>
          {create.isPending ? 'Saving…' : 'Save zone'}
        </Button>
        <p className="text-xs text-muted">
          Searching an address and dragging a pin on a map arrives with the setup wizard.
        </p>
      </Card>
    </div>
  )
}
