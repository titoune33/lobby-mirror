import type { StockPoint } from '../types'

export default function Sparkline({ points, width = 120, height = 34, up }: { points: StockPoint[]; width?: number; height?: number; up?: boolean }) {
  if (!points || points.length < 2) return <span className="dim small">—</span>
  const closes = points.map((p) => p.close)
  const min = Math.min(...closes)
  const max = Math.max(...closes)
  const span = max - min || 1
  const step = width / (closes.length - 1)
  const path = closes
    .map((c, i) => `${(i * step).toFixed(1)},${(height - 3 - ((c - min) / span) * (height - 6)).toFixed(1)}`)
    .join(' ')
  const color = up === undefined ? 'var(--cyan)' : up ? 'var(--green)' : 'var(--red)'
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <polyline points={path} fill="none" stroke={color} strokeWidth="1.6" />
    </svg>
  )
}
