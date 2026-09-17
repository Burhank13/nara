import { PERIOD_LABELS, PERIODS, type Period } from '../lib/periods'

export function PeriodTabs({
  value,
  onChange,
}: {
  value: Period
  onChange: (period: Period) => void
}) {
  return (
    <div className="flex rounded-xl bg-line-soft p-1" role="tablist" aria-label="Period">
      {PERIODS.map((option) => (
        <button
          key={option}
          role="tab"
          aria-selected={value === option}
          onClick={() => onChange(option)}
          className={[
            'min-h-9 rounded-lg px-3 text-sm font-medium transition-colors',
            value === option ? 'bg-surface text-ink shadow-sm' : 'text-muted hover:text-ink',
          ].join(' ')}
        >
          {PERIOD_LABELS[option]}
        </button>
      ))}
    </div>
  )
}
