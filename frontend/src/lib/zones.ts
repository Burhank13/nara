import { distanceTo, type Fix } from './geolocation'
import type { Zone } from './types'

export type ZoneCheck = { zone: Zone; distanceM: number; inside: boolean; bearing: number }

/** Mirrors the server's rule: the nearest zone containing you, else the nearest one overall. */
export function nearestZone(fix: Fix, zones: Zone[]): ZoneCheck | null {
  if (zones.length === 0) return null

  const checks = zones.map((zone) => {
    const distanceM = distanceTo(fix, zone.latitude, zone.longitude)
    return {
      zone,
      distanceM,
      inside: distanceM <= zone.radius_m,
      bearing: Math.atan2(fix.latitude - zone.latitude, fix.longitude - zone.longitude),
    }
  })

  const inside = checks.filter((check) => check.inside)
  return (inside.length ? inside : checks).reduce((best, check) =>
    check.distanceM < best.distanceM ? check : best,
  )
}
