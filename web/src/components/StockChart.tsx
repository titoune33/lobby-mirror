import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import type { StockSeries } from '../types'

export default function StockChart({ stock }: { stock: StockSeries }) {
  const data = stock.series.map((p) => ({ ...p, d: p.date.slice(5) }))
  const first = stock.series[0]?.close ?? 0
  const last = stock.series[stock.series.length - 1]?.close ?? 0
  const up = last >= first
  const color = up ? '#4ade80' : '#f87171'
  return (
    <div style={{ width: '100%', height: 260 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#1e1e2a" strokeDasharray="3 3" />
          <XAxis dataKey="d" tick={{ fill: '#8b8b9d', fontSize: 11 }} tickLine={false} minTickGap={40} />
          <YAxis
            domain={['auto', 'auto']}
            tick={{ fill: '#8b8b9d', fontSize: 11 }}
            tickLine={false}
            width={52}
            tickFormatter={(v: number) => v.toFixed(v < 10 ? 2 : 1)}
          />
          <Tooltip
            contentStyle={{ background: '#0e0e15', border: '1px solid #23232f', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#8b8b9d' }}
            formatter={(v: number) => [`${v}`, stock.symbol]}
          />
          <Line type="monotone" dataKey="close" stroke={color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
