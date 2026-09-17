import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-line bg-surface ${className}`}>{children}</div>
  )
}

export function StatCard({
  label,
  value,
  unit,
  hint,
}: {
  label: string
  value: string
  unit?: string
  hint?: string
}) {
  return (
    <Card className="p-4">
      <div className="text-[13px] text-muted">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="tabular text-[28px] leading-none font-semibold">{value}</span>
        {unit && <span className="tabular text-base text-muted">{unit}</span>}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </Card>
  )
}

export function Notice({
  tone = 'amber',
  children,
}: {
  tone?: 'amber' | 'teal'
  children: ReactNode
}) {
  const tones = {
    amber: 'border-amber/30 bg-amber-soft text-[#6b3a06]',
    teal: 'border-teal/20 bg-teal-soft text-teal-deep',
  }
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm leading-relaxed ${tones[tone]}`}>
      {children}
    </div>
  )
}
