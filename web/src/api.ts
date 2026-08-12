import type { DashboardData, Entity, Law, NewsArticle, Registration, Donation, StockSeries } from './types'

const FILES = ['meta', 'entities', 'laws', 'registrations', 'donations', 'stocks', 'news', 'influence', 'alerts'] as const

export async function loadData(base = ''): Promise<DashboardData> {
  const entries = await Promise.all(
    FILES.map(async (f) => {
      const res = await fetch(`${base}data/${f}.json`)
      if (!res.ok) throw new Error(`data/${f}.json → HTTP ${res.status}`)
      return [f, await res.json()] as const
    }),
  )
  const raw = Object.fromEntries(entries)
  return {
    meta: raw.meta ?? { updated_at: '', counts: {}, sources: [] },
    entities: raw.entities?.entities ?? [],
    laws: raw.laws ?? [],
    registrations: raw.registrations ?? [],
    donations: raw.donations ?? [],
    stocks: raw.stocks ?? {},
    news: raw.news ?? [],
    influence: raw.influence ?? {},
    alerts: raw.alerts ?? [],
  } as DashboardData
}

// ------------------------- index de confort -------------------------

export function entityIndex(d: DashboardData): Map<string, Entity> {
  return new Map(d.entities.map((e) => [e.id, e]))
}

export function lawIndex(d: DashboardData): Map<string, Law> {
  return new Map(d.laws.map((l) => [l.id, l]))
}

export function influenceTotal(d: DashboardData, entityId: string): number {
  const edges = d.influence[entityId] ?? []
  return edges.reduce((acc, e) => acc + e.score, 0)
}

export function newsByEntity(d: DashboardData): Map<string, NewsArticle[]> {
  const m = new Map<string, NewsArticle[]>()
  for (const n of d.news) {
    for (const id of n.entity_ids) {
      if (!m.has(id)) m.set(id, [])
      m.get(id)!.push(n)
    }
  }
  return m
}

export function regsByEntity(d: DashboardData): Map<string, Registration[]> {
  const m = new Map<string, Registration[]>()
  for (const r of d.registrations) {
    if (!m.has(r.entity_id)) m.set(r.entity_id, [])
    m.get(r.entity_id)!.push(r)
  }
  return m
}

export function donationsByEntity(d: DashboardData): Map<string, Donation[]> {
  const m = new Map<string, Donation[]>()
  for (const r of d.donations) {
    if (!m.has(r.entity_id)) m.set(r.entity_id, [])
    m.get(r.entity_id)!.push(r)
  }
  return m
}

export function stockOf(d: DashboardData, entityId: string): StockSeries | undefined {
  return d.stocks[entityId]
}

export function fmtDate(iso: string): string {
  if (!iso) return '—'
  const dt = new Date(iso)
  if (Number.isNaN(dt.getTime())) return iso.slice(0, 10)
  return dt.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function fmtMoney(usd: number): string {
  if (usd >= 1_000_000) return `${(usd / 1_000_000).toFixed(1)} M$`
  if (usd >= 1_000) return `${(usd / 1_000).toFixed(0)} k$`
  return `${usd} $`
}

export function scoreColor(score: number): string {
  if (score >= 60) return 'var(--red)'
  if (score >= 30) return 'var(--amber)'
  return 'var(--cyan)'
}
