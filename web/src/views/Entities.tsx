import { useMemo, useState } from 'react'
import type { DashboardData } from '../types'
import { influenceTotal } from '../api'
import Sparkline from '../components/Sparkline'

export default function Entities({ data }: { data: DashboardData }) {
  const [q, setQ] = useState('')
  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase()
    if (!query) return data.entities
    return data.entities.filter(
      (e) => e.name.toLowerCase().includes(query) || e.domains.some((d) => d.includes(query)),
    )
  }, [q, data])

  return (
    <>
      <div className="section-title">
        Entreprises &amp; lobbies suivis <span className="sub">{data.entities.length} entités · score d'influence agrégé</span>
      </div>
      <div className="toolbar">
        <input type="text" placeholder="Rechercher (nom, domaine…)" value={q} onChange={(e) => setQ(e.target.value)} style={{ minWidth: 260 }} />
      </div>
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
        {filtered.map((e) => {
          const total = influenceTotal(data, e.id)
          const s = data.stocks[e.id]
          return (
            <a key={e.id} href={`#/entreprise/${e.id}`} className="card" style={{ color: 'inherit' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                <b style={{ fontSize: 16 }}>{e.name}</b>
                <span className="score" style={{ fontSize: 14 }}>{total.toFixed(0)}</span>
              </div>
              <div className="mt">
                {e.domains.map((d) => <span key={d} className="chip">{d}</span>)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 12 }}>
                <div>
                  <div className="small dim">{e.jurisdiction_hq} · {e.tickers?.[0] ?? 'non coté'}</div>
                  {s && (
                    <div className="mono small" style={{ color: (s.change_1m_pct ?? 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>
                      {(s.change_1m_pct ?? 0) >= 0 ? '▲' : '▼'} {Math.abs(s.change_1m_pct ?? 0).toFixed(1)}% (1m)
                    </div>
                  )}
                </div>
                {s && <Sparkline points={s.series} width={110} height={32} up={(s.change_1m_pct ?? 0) >= 0} />}
              </div>
            </a>
          )
        })}
      </div>
    </>
  )
}
