import { useMemo, useState } from 'react'
import type { DashboardData } from '../types'
import { entityIndex, fmtDate } from '../api'

const ICON: Record<string, string> = { critical: '●', warning: '▲', info: '▪' }
const LABEL: Record<string, string> = { critical: 'CRITIQUE', warning: 'ALERTE', info: 'INFO' }
const COLOR: Record<string, string> = { critical: 'var(--red)', warning: 'var(--amber)', info: 'var(--cyan)' }

export default function Alerts({ data }: { data: DashboardData }) {
  const [sev, setSev] = useState('')
  const entities = entityIndex(data)
  const rows = useMemo(
    () => data.alerts.filter((a) => (sev ? a.severity === sev : true)).sort((a, b) => b.date.localeCompare(a.date)),
    [data, sev],
  )
  return (
    <>
      <div className="section-title">
        Alertes <span className="sub">{rows.length} alerte(s)</span>
      </div>
      <div className="toolbar">
        <select value={sev} onChange={(e) => setSev(e.target.value)}>
          <option value="">Toutes les sévérités</option>
          <option value="critical">Critiques</option>
          <option value="warning">Avertissements</option>
          <option value="info">Informations</option>
        </select>
      </div>
      {rows.length === 0 && <div className="card dim">Aucune alerte ne correspond au filtre.</div>}
      {rows.map((a) => (
        <div key={a.id} className={`alert ${a.severity}`}>
          <div className="head">
            <span style={{ color: COLOR[a.severity], fontWeight: 700 }}>
              {ICON[a.severity]} {LABEL[a.severity]}
            </span>
            <span>{a.kind}</span>
            <span>{fmtDate(a.date)}</span>
            {a.entity_id && entities.has(a.entity_id) && (
              <a href={`#/entreprise/${a.entity_id}`}>{entities.get(a.entity_id)!.name} →</a>
            )}
          </div>
          <div className="title">{a.title}</div>
          <div className="body">{a.body}</div>
        </div>
      ))}
    </>
  )
}
