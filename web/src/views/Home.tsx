import { useMemo, useState } from 'react'
import type { DashboardData, Entity, Law } from '../types'
import { influenceTotal, fmtDate, fmtMoney, newsByEntity } from '../api'
import Sparkline from '../components/Sparkline'

const SEV_ICON: Record<string, string> = { critical: '●', warning: '▲', info: '▪' }

export default function Home({ data, entities, laws }: { data: DashboardData; entities: Map<string, Entity>; laws: Map<string, Law> }) {
  const [since, setSince] = useState('')
  const news = data.news
  const news30 = useMemo(() => {
    if (!since) return news
    return news.filter((n) => n.date >= since)
  }, [news, since])

  const ranked = useMemo(
    () =>
      data.entities
        .map((e) => ({ e, total: influenceTotal(data, e.id) }))
        .sort((a, b) => b.total - a.total)
        .slice(0, 10),
    [data],
  )
  const maxTotal = ranked[0]?.total || 1

  const hotLaws = useMemo(
    () =>
      data.laws
        .filter((l) => (l.score ?? 0) > 0 || l.entities.length > 0)
        .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
        .slice(0, 8),
    [data],
  )

  const newsByEnt = useMemo(() => newsByEntity(data), [data])

  return (
    <>
      <div className="section-title">
        Vue d'ensemble <span className="sub">influence agrégée · {fmtDate(data.meta.updated_at)}</span>
      </div>

      <div className="grid kpis">
        <div className="card kpi">
          <div className="value">{data.entities.length}</div>
          <div className="label">entreprises &amp; lobbies suivis</div>
          <div className="delta">UE · FR · US</div>
        </div>
        <div className="card kpi">
          <div className="value">{data.laws.length}</div>
          <div className="label">textes de loi suivis</div>
          <div className="delta">
            {data.laws.filter((l) => (l.score ?? 0) > 0).length} avec pression détectée
          </div>
        </div>
        <div className="card kpi">
          <div className="value" style={{ color: 'var(--amber)' }}>{data.alerts.length}</div>
          <div className="label">alertes actives</div>
          <div className="delta">
            {data.alerts.filter((a) => a.severity === 'critical').length} critiques
          </div>
        </div>
        <div className="card kpi">
          <div className="value" style={{ color: 'var(--magenta)' }}>{news30.length}</div>
          <div className="label">articles de presse liés</div>
          <div className="delta">GDELT · NewsAPI</div>
        </div>
      </div>

      <div className="grid split mt">
        <div className="card">
          <h3>▸ Top 10 des pressions ce mois-ci</h3>
          <ul className="list">
            {ranked.map(({ e, total }, i) => (
              <li key={e.id}>
                <a href={`#/entreprise/${e.id}`} className="rank-row" style={{ color: 'inherit' }}>
                  <span className="rank">{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <div className="name">{e.name}</div>
                    <div className="bar">
                      <i style={{ width: `${(total / maxTotal) * 100}%` }} />
                    </div>
                  </div>
                  <span className="score">{total.toFixed(0)}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h3>▸ Lois sous pression</h3>
          <ul className="list">
            {hotLaws.length === 0 && <li className="dim small">Aucune pression détectée sur la fenêtre actuelle.</li>}
            {hotLaws.map((l) => (
              <li key={l.id} className="law-row">
                <span className={`jur ${l.jurisdiction}`}>{l.jurisdiction}</span>
                {l.score !== undefined && l.score > 0 && <span className="chip hot">pression {l.score.toFixed(0)}</span>}
                <div className="title">{l.title}</div>
                <div className="meta">
                  {l.status} · {l.entities.length > 0 ? l.entities.map((id) => entities.get(id)?.name).join(', ') : '—'}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="grid split mt">
        <div className="card">
          <h3>▸ Dernières alertes</h3>
          <ul className="list">
            {data.alerts.slice(0, 6).map((a) => (
              <li key={a.id}>
                <div className="head" style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--text-dim)' }}>
                  <span style={{ color: a.severity === 'critical' ? 'var(--red)' : a.severity === 'warning' ? 'var(--amber)' : 'var(--cyan)' }}>
                    {SEV_ICON[a.severity]} {a.severity.toUpperCase()}
                  </span>
                  <span>{fmtDate(a.date)}</span>
                </div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{a.title}</div>
                <div className="dim small">{a.body}</div>
              </li>
            ))}
          </ul>
          <div className="mt">
            <a className="small" href="#/alertes">Toutes les alertes →</a>
          </div>
        </div>

        <div className="card">
          <h3>
            ▸ Presse &amp; lobbying
            <span style={{ float: 'right', fontFamily: 'var(--mono)', fontWeight: 400 }}>
              <input type="text" placeholder="depuis (AAAA-MM-JJ)" value={since} onChange={(e) => setSince(e.target.value)} style={{ width: 160, padding: '3px 8px', fontSize: 12 }} />
            </span>
          </h3>
          <ul className="list">
            {news30.slice(0, 6).map((n) => (
              <li key={n.id} className="news-item">
                <span className="src">{n.source}</span> · <span className="date">{fmtDate(n.date)}</span>
                <div className="t"><a href={n.url} target="_blank" rel="noreferrer">{n.title}</a></div>
                <div>{n.entity_ids.map((id) => <span key={id} className="chip cyan">{entities.get(id)?.name ?? id}</span>)}</div>
              </li>
            ))}
            {news30.length === 0 && <li className="dim small">Aucun article sur la période.</li>}
          </ul>
        </div>
      </div>

      <div className="grid mt" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
        {ranked.slice(0, 8).map(({ e, total }) => {
          const s = data.stocks[e.id]
          const nbNews = (newsByEnt.get(e.id) ?? []).length
          return (
            <a key={e.id} href={`#/entreprise/${e.id}`} className="card" style={{ color: 'inherit', display: 'block' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <b>{e.name}</b>
                <span className="score">{total.toFixed(0)}</span>
              </div>
              <div className="dim small mt">{e.domains.slice(0, 3).join(' · ')}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 8 }}>
                <div>
                  {s && (
                    <span className="mono small" style={{ color: (s.change_1m_pct ?? 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>
                      {(s.change_1m_pct ?? 0) >= 0 ? '▲' : '▼'} {Math.abs(s.change_1m_pct ?? 0).toFixed(1)}% (1m)
                    </span>
                  )}
                  <div className="small dim">{nbNews} articles</div>
                </div>
                {s && <Sparkline points={s.series} width={90} height={30} up={(s.change_1m_pct ?? 0) >= 0} />}
              </div>
            </a>
          )
        })}
      </div>
    </>
  )
}
