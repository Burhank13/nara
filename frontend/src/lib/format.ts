/** Hours as a decimal, the way payroll reads them: 8.25 = 8 h 15 m. */
export function hours(value: number): string {
  return value.toFixed(2)
}

export function elapsed(fromIso: string, now: number): string {
  const seconds = Math.max(0, Math.floor((now - new Date(fromIso).getTime()) / 1000))
  const hh = Math.floor(seconds / 3600)
  const mm = Math.floor((seconds % 3600) / 60)
  const ss = seconds % 60
  return `${hh}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

export function distance(metres: number): string {
  return metres >= 1000 ? `${(metres / 1000).toFixed(1)} km` : `${Math.round(metres)} m`
}

/** Compact running time for the live board: "3h 12m". */
export function duration(fromIso: string, now: number): string {
  const minutes = Math.max(0, Math.floor((now - new Date(fromIso).getTime()) / 60000))
  return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`
}

export const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const

function hourLabel(value: string): string {
  const [rawHour, rawMinute] = value.split(':').map(Number)
  const hour = rawHour % 12 === 0 ? 12 : rawHour % 12
  return rawMinute ? `${hour}:${String(rawMinute).padStart(2, '0')}` : String(hour)
}

/** "07:00:00"–"15:00:00" reads as "7–3", the way a roster is written up on a wall. */
export function windowLabel(start: string, end: string): string {
  return `${hourLabel(start)}–${hourLabel(end)}`
}

function formatter(timeZone: string, options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  return new Intl.DateTimeFormat('en-AU', { timeZone, ...options })
}

export function time(iso: string, timeZone: string): string {
  return formatter(timeZone, { hour: 'numeric', minute: '2-digit', hour12: true })
    .format(new Date(iso))
    .toLowerCase()
}

export function clockTime(iso: string, timeZone: string): string {
  return formatter(timeZone, { hour: '2-digit', minute: '2-digit', hour12: false }).format(
    new Date(iso),
  )
}

export function dayAndDate(iso: string, timeZone: string): string {
  return formatter(timeZone, { weekday: 'short', day: 'numeric', month: 'short' }).format(
    new Date(iso),
  )
}

export function longDate(date: Date, timeZone: string): string {
  return formatter(timeZone, { weekday: 'short', day: 'numeric', month: 'short' }).format(date)
}

export function rangeLabel(startIso: string, endIso: string, timeZone: string): string {
  const start = new Date(startIso)
  // The period end is exclusive midnight, so show the last day people actually worked.
  const end = new Date(new Date(endIso).getTime() - 1)
  const day = (date: Date) => formatter(timeZone, { day: 'numeric' }).format(date)
  const dayMonth = (date: Date) =>
    formatter(timeZone, { day: 'numeric', month: 'short' }).format(date)
  const sameMonth =
    formatter(timeZone, { month: 'short' }).format(start) ===
    formatter(timeZone, { month: 'short' }).format(end)

  return sameMonth ? `${day(start)}–${dayMonth(end)}` : `${dayMonth(start)} – ${dayMonth(end)}`
}

/**
 * Shift times are edited in the shop's clock, not the browser's, so an owner in another state
 * still types the hours their staff actually worked. These feed <input type="date"|"time">.
 */
export function dateInput(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(iso))
}

export function timeInput(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date(iso))
}

export function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/)
  const letters = parts.length > 1 ? [parts[0][0], parts[parts.length - 1][0]] : [parts[0]?.[0] ?? '']
  return letters.join('').toUpperCase()
}
