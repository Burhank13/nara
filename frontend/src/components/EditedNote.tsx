import type { ShiftEdit } from '../lib/types'

/** Hours never change quietly: wherever a shift is shown, the last edit's reason is shown with it. */
export function EditedNote({ edits }: { edits: ShiftEdit[] }) {
  if (edits.length === 0) return null
  const last = edits[edits.length - 1]

  return (
    <p className="mt-0.5 text-xs text-muted">
      <span className="font-semibold text-amber">Edited</span> · {last.reason}
      <span className="text-muted/70"> — {last.edited_by}</span>
    </p>
  )
}
