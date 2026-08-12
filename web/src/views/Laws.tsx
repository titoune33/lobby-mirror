import { useMemo, useState } from 'react'
import type { DashboardData } from '../types'
import { entityIndex, fmtDate } from '../api'

const STATUS_ORDER = ['En cours', 'Adopté', 'Rejeté', 'Inconnu']

export default function Laws({ data }: { data: DashboardData }) {
  const [q, setQ] = useState('')
  const [jur, setJur] = useState('')
  const entities = entityIndex(data)

  const rows = useMemo(() => {
    const query = q.trim().toLowerCase()
    return data.laws
      .filter((l) => (jur ? l.jurisdiction === jur : true))
      .filter((l) => (query ? l.title.toLowerCase().includes(query) || l.tags.some((t) => t.includes(query)) || l.id.toLowerCase().includes(query) : true))
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
  }, [q, jur, data])

  return (
    <>
      <div className="section-title">
        Textes de loi suivis <span className="sub">{data.laws.length} textes · triés par pression détectée</span>
      </div>
      <div className="toolbar">
        <input type="text" placeholder="Rechercher un texte, un sujet…" value={q} onChange={(e) => setQ(e.target.value)} style={{ minWidth: 260 }} />
        <select value={jur} onChange={(e) => setJur(e.target.value)}>
          <option value="">Toutes juridictions</option>
          <option value="EU">Union européenne</option>
          <option value="FR">France</option>
          <option value="US">États-Unis</option>
        </select>
      </div>
      <div className="card" style={{ padding: 6 }}>
        <table className="data">
          <thead>
            <tr>
              <th>Réf.</th><th>Texte</th><th>Statut</th><th>Entités liées</th><th>Pression</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((l) => (
              <tr key={l.id}>
                <td className="mono small" style={{ whiteSpace: 'nowrap' }}>
                  {l.url ? <a href={l.url} target="_blank" rel="noreferrer">{l.id}</a> : l.id}
                </td>
                <td>
                  <div style={{ fontWeight: 600 }}>{l.title}</div>
                  <div className="mt">{l.tags.map((t) => <span key={t} className="chip">{t}</span>)}</div>
                  <div className="small dim mt">{l.committee ?? ''} · dépôt : {fmtDate(l.dates.introduced ?? '')} · maj : {fmtDate(l.dates.updated ?? '')}</div>
                </td>
                <td className="small">{l.status}</td>
                <td>
                  {l.entities.length === 0 && <span className="dim small">—</span>}
                  {l.entities.map((id) => {
                    const e = entities.get(id)
                    return e ? <a key={id} href={`#/entreprise/${id}`} className="chip cyan">{e.name}</a> : <span key={id} className="chip">{id}</span>
                  })}
                </td>
                <td className="mono" style={{ color: l.score && l.score >= 60 ? 'var(--red)' : l.score && l.score >= 30 ? 'var(--amber)' : 'var(--text-dim)' }}>
                  {l.score !== undefined && l.score > 0 ? l.score.toFixed(0) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
