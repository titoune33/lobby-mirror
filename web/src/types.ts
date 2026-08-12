export interface Entity {
  id: string
  name: string
  aliases: string[]
  tickers: string[] | null
  jurisdiction_hq: string
  domains: string[]
  keywords: string[]
}

export interface Law {
  id: string
  jurisdiction: 'EU' | 'FR' | 'US'
  title: string
  status: string
  type?: string
  dates: { introduced?: string; updated?: string; next_step?: string }
  committee?: string
  tags: string[]
  url?: string
  entities: string[]
  score?: number
}

export interface Registration {
  id: string
  registry: string
  entity_id: string
  name: string
  match_field: string
  confidence: number
  registrant_type?: string
  clients?: string[]
  domains: string[]
  raw_domains?: string[]
  cost_band?: string
  declared_activities?: string[]
  year?: string
  url?: string
}

export interface Donation {
  id: string
  entity_id: string
  recipient: string
  office?: string
  amount_usd: number
  cycle: string
  source: string
}

export interface StockPoint {
  date: string
  close: number
}

export interface StockSeries {
  symbol: string
  series: StockPoint[]
  change_1m_pct?: number
  change_1w_pct?: number
  anomaly_pct?: number
}

export interface NewsArticle {
  id: string
  date: string
  title: string
  url: string
  source: string
  entity_ids: string[]
  tags: string[]
}

export interface InfluenceSignals {
  news: number
  register: boolean
  donations: number
  stock: number
}

export interface InfluenceEdge {
  law_id: string
  score: number
  signals: InfluenceSignals
  reasons: string[]
}

export type Influence = Record<string, InfluenceEdge[]>

export interface AlertItem {
  id: string
  date: string
  severity: 'info' | 'warning' | 'critical'
  kind: string
  title: string
  body: string
  entity_id?: string
  law_id?: string
}

export interface Meta {
  updated_at: string
  counts: Record<string, number>
  sources: string[]
}

export interface DashboardData {
  meta: Meta
  entities: Entity[]
  laws: Law[]
  registrations: Registration[]
  donations: Donation[]
  stocks: Record<string, StockSeries>
  news: NewsArticle[]
  influence: Influence
  alerts: AlertItem[]
}
