import { useEffect, useState } from 'react'
import { loadData, entityIndex, lawIndex } from './api'
import type { DashboardData } from './types'
import Header from './components/Header'
import Home from './views/Home'
import Entities from './views/Entities'
import EntityDetail from './views/EntityDetail'
import Laws from './views/Laws'
import Alerts from './views/Alerts'
import Methodo from './views/Methodo'

function useHashRoute(): string {
  const [route, setRoute] = useState(() => window.location.hash || '#/')
  useEffect(() => {
    const onChange = () => setRoute(window.location.hash || '#/')
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export default function App() {
  const route = useHashRoute()
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    loadData(import.meta.env.BASE_URL)
      .then((d) => { if (!cancelled) { setData(d); setError(null) } })
      .catch((e) => { if (!cancelled) setError(String(e?.message ?? e)) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) return <div className="app"><Header route={route} /><div className="loading">▚ chargement des données…</div></div>

  if (error || !data) {
    return (
      <div className="app">
        <Header route={route} />
        <div className="error-box">
          Impossible de charger les données du tableau de bord : <b>{error}</b>
          <div className="small mt">Lance d'abord le pipeline de données :
            <code className="mono"> scrapers/.venv/bin/python scrapers/pipeline.py --all</code>
          </div>
        </div>
      </div>
    )
  }

  const entities = entityIndex(data)
  const laws = lawIndex(data)

  const [path, arg] = route.slice(2).split('/')

  let view: React.ReactNode
  if (path === 'entreprise' && arg && entities.has(arg)) {
    view = <EntityDetail data={data} entity={entities.get(arg)!} />
  } else if (path === 'entreprises') {
    view = <Entities data={data} />
  } else if (path === 'lois') {
    view = <Laws data={data} />
  } else if (path === 'alertes') {
    view = <Alerts data={data} />
  } else if (path === 'methode') {
    view = <Methodo />
  } else {
    view = <Home data={data} entities={entities} laws={laws} />
  }

  return (
    <div className="app">
      <Header route={route} />
      <main>{view}</main>
      <footer className="page">
        <span>LobbyMirror v0.1 — données publiques agrégées, dernière mise à jour : <b className="mono">{data.meta.updated_at || '—'}</b></span>
        <a href="#/methode">Méthodologie &amp; sources</a>
        <a href="https://github.com/titoune33" target="_blank" rel="noreferrer">titoune33</a>
      </footer>
    </div>
  )
}
