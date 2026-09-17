export type ShiftEdit = {
  id: string
  edited_by: string
  reason: string
  created_at: string
  previous_started_at: string
  previous_ended_at: string | null
  new_started_at: string
  new_ended_at: string | null
}

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
  edits: ShiftEdit[]
}

export type TimesheetShift = Shift & { user_id: string; full_name: string }

export type Timesheet = {
  period: 'week' | 'fortnight' | 'month'
  starts_at: string
  ends_at: string
  total_hours: number
  shift_count: number
  open_count: number
  hours_by_employee: EmployeeHours[]
  shifts: TimesheetShift[]
  staff: { user_id: string; full_name: string }[]
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

export type LiveShift = {
  shift_id: string
  user_id: string
  full_name: string
  started_at: string
  hours: number
  start_distance_m: number
  location_name: string | null
  needs_attention: boolean
}

export type LiveBoard = {
  on_shift: LiveShift[]
  staff_count: number
}

export type EmployeeHours = {
  user_id: string
  full_name: string
  shift_count: number
  hours: number
  flagged: boolean
}

export type Overview = {
  period: 'week' | 'fortnight' | 'month'
  starts_at: string
  ends_at: string
  staff_count: number
  active_count: number
  invited_count: number
  on_shift: LiveShift[]
  needs_attention: LiveShift[]
  team_hours: number
  shift_count: number
  hours_by_employee: EmployeeHours[]
}

export type AvailabilityDay = {
  weekday: number
  start_time: string
  end_time: string
}

export type TeamAvailability = {
  members: {
    user_id: string
    full_name: string
    role: string
    days: AvailabilityDay[]
  }[]
}

export type PayrollLine = {
  user_id: string
  full_name: string
  payroll_code: string | null
  work_date: string
  hours: number
  shift_count: number
}

export type Payroll = {
  period: 'week' | 'fortnight' | 'month'
  starts_at: string
  ends_at: string
  rounding_minutes: number
  total_hours: number
  ready: boolean
  lines: PayrollLine[]
  open_shifts: { full_name: string; started_at: string }[]
  missing_codes: string[]
}

export type Member = {
  id: string
  email: string
  full_name: string
  payroll_code: string | null
  role: 'owner' | 'manager' | 'employee'
  status: 'invited' | 'active' | 'archived'
  invited_at: string | null
  invite_expires_at: string | null
  accepted_at: string | null
  archived_at: string | null
}

export type Seats = { used: number; limit: number; available: number }

export type OnboardingStep = {
  key: 'details' | 'zones' | 'staff' | 'billing'
  title: string
  description: string
  done: boolean
  optional: boolean
}

export type Onboarding = {
  steps: OnboardingStep[]
  complete: boolean
  next_step: OnboardingStep['key'] | null
  days_left: number | null
  trial_ends_at: string | null
  seats_used: number
  seat_limit: number
}

export type Team = { members: Member[]; seats: Seats }
