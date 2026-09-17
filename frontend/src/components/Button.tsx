import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'danger' | 'secondary' | 'ghost'
type Size = 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-teal text-white hover:bg-teal-deep disabled:bg-line disabled:text-muted',
  danger: 'bg-danger text-white hover:bg-danger-deep disabled:bg-line disabled:text-muted',
  secondary:
    'bg-surface text-ink border border-line hover:border-ink disabled:text-muted disabled:border-line',
  ghost: 'bg-transparent text-teal hover:text-teal-deep underline underline-offset-4',
}

const SIZES: Record<Size, string> = {
  // Tap targets never go under 44px.
  md: 'min-h-11 px-5 text-[15px] rounded-xl',
  lg: 'min-h-16 px-6 text-xl rounded-2xl',
}

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
  full?: boolean
}

export function Button({
  variant = 'primary',
  size = 'md',
  full = false,
  className = '',
  ...props
}: Props) {
  return (
    <button
      className={[
        'inline-flex items-center justify-center gap-2 font-semibold transition-colors',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal',
        'disabled:cursor-not-allowed',
        VARIANTS[variant],
        variant === 'ghost' ? '' : SIZES[size],
        full ? 'w-full' : '',
        className,
      ].join(' ')}
      {...props}
    />
  )
}
