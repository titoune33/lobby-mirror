const TABS = [
  { href: '#/', label: 'ACCUEIL', exact: true },
  { href: '#/entreprises', label: 'ENTREPRISES' },
  { href: '#/lois', label: 'LOIS' },
  { href: '#/alertes', label: 'ALERTES' },
  { href: '#/methode', label: 'MÉTHODE' },
]

export default function Header({ route }: { route: string }) {
  return (
    <header className="top">
      <a className="logo" href="#/">
        <span className="cube" />
        <span>LOBBY<em>·</em>MIRROR</span>
      </a>
      <span className="tagline">Le Black Mirror des Lobbying — influence temps réel sur les lois UE · FR · US</span>
      <nav className="tabs">
        {TABS.map((t) => {
          const active = t.exact ? route === '#/' : route.startsWith(t.href)
          return (
            <a key={t.href} href={t.href} className={active ? 'active' : ''}>
              {t.label}
            </a>
          )
        })}
      </nav>
    </header>
  )
}
