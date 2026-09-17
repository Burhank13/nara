export const PERIODS = ['week', 'fortnight', 'month'] as const

export type Period = (typeof PERIODS)[number]

export const PERIOD_LABELS: Record<Period, string> = {
  week: 'Week',
  fortnight: 'Fortnight',
  month: 'Month',
}
