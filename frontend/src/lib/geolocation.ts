import { useCallback, useEffect, useState } from 'react'

export type Fix = {
  latitude: number
  longitude: number
  accuracy_m: number
}

export type GeoState =
  | { status: 'unsupported' }
  | { status: 'locating' }
  | { status: 'denied' }
  | { status: 'unavailable'; message: string }
  | { status: 'located'; fix: Fix }

const OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  timeout: 15_000,
  maximumAge: 10_000,
}

function toState(position: GeolocationPosition): GeoState {
  return {
    status: 'located',
    fix: {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy_m: position.coords.accuracy,
    },
  }
}

function toError(error: GeolocationPositionError): GeoState {
  if (error.code === error.PERMISSION_DENIED) return { status: 'denied' }
  return {
    status: 'unavailable',
    message:
      error.code === error.TIMEOUT
        ? "Couldn't get a location in time. Try again outside or near a window."
        : "Your device couldn't work out where it is.",
  }
}

/** Watches the device position so the shift screen can show live distance to the zone. */
export function useGeolocation(active = true): { state: GeoState; retry: () => void } {
  const [state, setState] = useState<GeoState>(() =>
    'geolocation' in navigator ? { status: 'locating' } : { status: 'unsupported' },
  )
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!active || !('geolocation' in navigator)) return

    const id = navigator.geolocation.watchPosition(
      (position) => setState(toState(position)),
      (error) => setState(toError(error)),
      OPTIONS,
    )
    return () => navigator.geolocation.clearWatch(id)
  }, [active, attempt])

  const retry = useCallback(() => {
    setState({ status: 'locating' })
    setAttempt((value) => value + 1)
  }, [])
  return { state, retry }
}

/** One-shot read, used at the moment a shift ends. */
export function readPosition(): Promise<Fix | null> {
  if (!('geolocation' in navigator)) return Promise.resolve(null)
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      ({ coords }) =>
        resolve({
          latitude: coords.latitude,
          longitude: coords.longitude,
          accuracy_m: coords.accuracy,
        }),
      // Ending a shift must never be blocked by a location problem.
      () => resolve(null),
      OPTIONS,
    )
  })
}

const EARTH_RADIUS_M = 6_371_008.8

/** Same haversine the server uses; here only to show distance before the tap. */
export function distanceTo(fix: Fix, latitude: number, longitude: number): number {
  const toRad = (value: number) => (value * Math.PI) / 180
  const phi1 = toRad(fix.latitude)
  const phi2 = toRad(latitude)
  const deltaPhi = phi2 - phi1
  const deltaLambda = toRad(longitude - fix.longitude)

  const a =
    Math.sin(deltaPhi / 2) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(a))
}
