export const pct = (v: number | null | undefined, digits = 0) => (v == null ? '—' : `${(v * 100).toFixed(digits)}%`)
export const secs = (ms: number | null | undefined) => (ms == null ? '—' : `${(ms / 1000).toFixed(1)}s`)

/** Green above 85%, amber above 65%, red below. Used for accuracy-style metrics where higher is better. */
export function rateColor(v: number | null | undefined, invert = false): string {
  if (v == null) return '#8c8c8c'
  const x = invert ? 1 - v : v
  if (x >= 0.85) return '#16a34a'
  if (x >= 0.65) return '#d97706'
  return '#dc2626'
}
