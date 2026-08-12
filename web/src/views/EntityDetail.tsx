import { useMemo } from 'react'
import type { DashboardData, Entity } from '../types'
import { influenceTotal, lawIndex, newsByEntity, regsByEntity, donationsByEntity, stockOf, fmtDate, fmtMoney } from '../api'
import StockChart from '../components/StockChart'

export default function EntityDetail({ data, entity }: { data: DashboardData; entity: Entity }) {
  const laws = lawIndex(data)
  const edges = data.influence[entity.id] ?? []
  const news = useMemo(() => newsByEntity(data).get(entity.id) ?? [], [data, entity.id])
  const regs = useMemo(() => regsByEntity(data).get(entity.id) ?? [], [data, entity.id])
  const dons = useMemo(() => donationsByEntity(data).get(entity.id) ?? [], [data, entity.id])
  const stock = stockOf(data, entity.id)
  const total = influenceTotal(data, entity.id)
  const totalDon = dons.reduce((acc, d) => acc + d.amount_usd, 0)

  return (
    <>
      <a className="back" href="#/entreprises">← toutes les entreprises</a>

      <div className="card">
        <div className="entity-head">
          <div style={{ flex: 1 }}>
            <h2>{entity.name}</h2>
            <div className="tickers">
              {entity.tickers?.length ? entity.tickers.join(' · ') : 'non coté'}
              {' '}· siège : {entity.jurisdiction_hq}
            </div>
            <div className="mt">
              {entity.domains.map((d) => <span key={d} className="chip cyan">{d}</span>)}
            </div>
          </div>
          <div style={{ textAlign: 'right', minWidth: 150 }}>
            <div className="kpi">
              <div className="value">{total.toFixed(0)}</div>
              <div className="label">score d'influence</div>
            </div>
            <div className="small dim mt">
              {edges.length} loi(s) liée(s) · {news.length} article(s) · {regs.length} registre(s) · {fmtMoney(totalDon)} dons
            </div>
          </div>
        </div>
      </div>

      {stock && (
        <div className="card mt">
          <h3>▸ Cours de bourse — {stock.symbol} (1 an)</h3>
          <StockChart stock={stock} />
          <div className="small dim">
            1 semaine : {(stock.change_1w_pct ?? 0) >= 0 ? '▲' : '▼'} {Math.abs(stock.change_1w_pct ?? 0).toFixed(1)}% ·
            1 mois : {(stock.change_1m_pct ?? 0) >= 0 ? '▲' : '▼'} {Math.abs(stock.change_1m_pct ?? 0).toFixed(1)}%
            {stock.anomaly_pct !== undefined && (
              <> · <b style={{ color: 'var(--magenta)' }}>anomalie de cours détectée : {stock.anomaly_pct >= 0 ? '+' : ''}{stock.anomaly_pct.toFixed(1)}%</b></>
            )}
          </div>
        </div>
      )}

      <div className="grid split mt">
        <div className="card">
          <h3>▸ Lois influencées (signaux croisés)</h3>
          <ul className="list">
            {edges.length === 0 && <li className="dim small">Aucun lien loi ↔ {entity.name} détecté sur la fenêtre actuelle.</li>}
            {edges.map((edge) => {
              const law = laws.get(edge.law_id)
              if (!law) return null
              return (
                <li key={edge.law_id} className="law-row">
                  <span className={`jur ${law.jurisdiction}`}>{law.jurisdiction}</span>
                  <span className="chip hot">pression {edge.score.toFixed(0)}</span>
                  <div className="title">{law.title}</div>
                  <div className="meta">{law.status}</div>
                  <div className="mt">
                    {edge.signals.news > 0 && <span className="chip cyan">{edge.signals.news} article(s) de presse</span>}
                    {edge.signals.register && <span className="chip magenta">registre lobbying</span>}
                    {edge.signals.donations > 0 && <span className="chip hot">{fmtMoney(edge.signals.donations)} dons politiques</span>}
                    {edge.signals.stock > 0 && <span className="chip">mouvement de stock</span>}
                  </div>
                  {edge.reasons.length > 0 && <div className="small dim mt">{edge.reasons.join(' · ')}</div>}
                </li>
              )
            })}
          </ul>
        </div>

        <div className="card">
          <h3>▸ Registres de lobbying</h3>
          <ul className="list">
            {regs.length === 0 && <li className="dim small">Non inscrit ou non détecté dans les registres analysés (UE · HATVP · LDA US).</li>}
            {regs.map((r) => (
              <li key={r.id}>
                <div className="mono small" style={{ color: 'var(--cyan)' }}>{r.registry} · confiance {r.confidence}%</div>
                <div style={{ fontWeight: 600 }}>{r.name}</div>
                <div className="small dim">{r.registrant_type ?? ''}{r.cost_band ? ` · dépenses déclarées : ${r.cost_band}` : ''}{r.year ? ` · ${r.year}` : ''}</div>
                <div className="mt">{r.domains.map((d) => <span key={d} className="chip magenta">{d}</span>)}</div>
                {r.clients && r.clients.length > 0 && (
                  <div className="small dim mt">Clients : {r.clients.slice(0, 8).join(', ')}</div>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {dons.length > 0 && (
        <div className="card mt">
          <h3>▸ Dons politiques (FEC, cycle {dons[0].cycle})</h3>
          <table className="data">
            <thead>
              <tr><th>Bénéficiaire</th><th>Poste</th><th>Montant</th><th>Source</th></tr>
            </thead>
            <tbody>
              {dons.map((d) => (
                <tr key={d.id}>
                  <td><b>{d.recipient}</b></td>
                  <td className="dim">{d.office ?? '—'}</td>
                  <td className="mono">{fmtMoney(d.amount_usd)}</td>
                  <td className="dim small">{d.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card mt">
        <h3>▸ Presse ({news.length} article(s))</h3>
        <ul className="list">
          {news.length === 0 && <li className="dim small">Aucun article indexé.</li>}
          {news.slice(0, 20).map((n) => (
            <li key={n.id} className="news-item">
              <span className="src">{n.source}</span> · <span className="date">{fmtDate(n.date)}</span>
              <div className="t"><a href={n.url} target="_blank" rel="noreferrer">{n.title}</a></div>
              <div>{n.tags.map((t) => <span key={t} className="chip">{t}</span>)}</div>
            </li>
          ))}
        </ul>
      </div>
    </>
  )
}
