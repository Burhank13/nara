export type Shift = {
  id: string
  status: 'open' | 'closed'
  started_at: string
  ended_at: string | null
  hours: number
  location_id: string | null
  location_name: string | null
  start_distance_m: number
  start_accuracy_m: number
  end_distance_m: number | null
  end_accuracy_m: number | null
  needs_attention: boolean
}

export type ShiftPeriod = {
  period: 'week' | 'fortnight' | 'month'
  starts_at: string
  ends_at: string
  total_hours: number
  shift_count: number
  shifts: Shift[]
}

export type Zone = {
  id: string
  name: string
  address: string | null
  latitude: number
  longitude: number
  radius_m: number
}
