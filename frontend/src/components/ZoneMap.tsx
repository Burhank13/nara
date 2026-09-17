type Props = {
  /** Metres from the shop, or null while the device is still locating. */
  distanceM: number | null
  radiusM: number
  /** Direction from the shop to the phone, in radians; 0 when unknown. */
  bearing?: number
}

const VIEW = 320
const CENTRE = VIEW / 2
const ZONE_RADIUS_PX = 96

/**
 * A schematic of the zone rather than a real map: it only has to answer
 * "am I inside, and roughly how far out?" — and it works offline.
 */
export function ZoneMap({ distanceM, radiusM, bearing = 0.9 }: Props) {
  const ratio = distanceM === null ? 0 : distanceM / radiusM
  // Past the edge the dot keeps moving out, but stays on screen.
  const pixels = Math.min(ratio, 1.45) * ZONE_RADIUS_PX
  const x = CENTRE + Math.cos(bearing) * pixels
  const y = CENTRE - Math.sin(bearing) * pixels
  const inside = distanceM !== null && distanceM <= radiusM

  return (
    <svg
      viewBox={`0 0 ${VIEW} ${VIEW}`}
      className="h-52 w-full sm:h-60"
      role="img"
      aria-label={
        distanceM === null
          ? 'Locating you'
          : `You are ${Math.round(distanceM)} metres from the shop, in a ${radiusM} metre zone`
      }
    >
      <rect width={VIEW} height={VIEW} fill="#eaf0ed" />
      {[56, 152, 248].map((offset) => (
        <g key={offset}>
          <rect x={offset} y="0" width="14" height={VIEW} fill="#ffffff" />
          <rect x="0" y={offset} width={VIEW} height="14" fill="#ffffff" />
        </g>
      ))}

      <circle
        cx={CENTRE}
        cy={CENTRE}
        r={ZONE_RADIUS_PX}
        fill="#0e6b5c"
        fillOpacity="0.08"
        stroke="#0e6b5c"
        strokeWidth="2"
        strokeDasharray="7 7"
      />

      {/* The shop itself. */}
      <rect x={CENTRE - 9} y={CENTRE - 9} width="18" height="18" rx="4" fill="#1c1f1d" />

      {distanceM !== null && (
        <circle
          cx={x}
          cy={y}
          r="9"
          fill={inside ? '#2563eb' : '#b45309'}
          stroke="#ffffff"
          strokeWidth="3"
        />
      )}

      <text x={VIEW - 12} y="26" textAnchor="end" fontSize="13" fill="#0b5a4d" fontFamily="IBM Plex Mono, monospace">
        {radiusM} m zone
      </text>
    </svg>
  )
}
