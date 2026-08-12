# ◼ LOBBY·MIRROR — « Le Black Mirror des Lobbying »

Plateforme d'analyse en temps réel des influences lobbyistes sur les lois (UE · France · États-Unis).

## Principe

1. **Collecte** — sources publiques officielles uniquement (parlements, registres de lobbying, FEC, GDELT/NewsAPI, Yahoo Finance).
2. **Croisement** — moteur de matching d'entités (alias, normalisation, fuzzy) + scoring de pression entreprise ↔ texte de loi sur 4 signaux (presse, registre, dons, marché).
3. **Diffusion** — tableau de bord React + alertes automatiques.

## Architecture

```
lobby-mirror/
├── scrapers/            # Pipeline Python (spec hub: rate-limit, retry, cache, dédup)
│   ├── lib.py           #   framework commun (HTTP, cache, matching d'entités)
│   ├── entities.json    #   watchlist : 34 entreprises/lobbies (alias, tickers, domaines)
│   ├── pipeline.py      #   orchestrateur CLI
│   ├── match.py         #   moteur de croisement → influence.json
│   ├── alerts.py        #   générateur d'alertes
│   ├── meta.py          #   méta-données du run
│   └── sources/         #   un module par source de données
├── data/                #   sorties normalisées (schémas stables)
│   ├── laws/ lobby/ finance/ news/
│   ├── influence.json · alerts.json · meta.json
│   └── raw/             #   bruts + cache (gitignoré)
├── api/                 #   fonctions serverless Vercel (proxy Yahoo, push webhook)
└── web/                 #   tableau de bord React + Vite (thème "Black Mirror")
│   └── api/yahoo.ts     #   fonction serverless Vercel (proxy cours live)
    └── public/data/     #   copie des sorties pour le déploiement statique
```

## Démarrage rapide

```bash
# 1. Pipeline de données (Python 3.10+)
cd scrapers
uv venv .venv && uv pip install -r requirements.txt
env -u PYTHONPATH .venv/bin/python pipeline.py --all

# 2. Tableau de bord
cd ../web
npm install && npm run dev      # http://localhost:5173
```

Mise à jour quotidienne : cron GitHub Actions (`.github/workflows/update.yml`) ou `pipeline.py --all` local.

## Données & schémas

| Fichier | Contenu | Clés |
|---|---|---|
| `data/laws/laws.json` | Textes législatifs normalisés | `id, jurisdiction, title, status, tags, dates, entities, score` |
| `data/lobby/registrations.json` | Entrées registres de lobbying matchées | `registry, entity_id, confidence, domains, cost_band` |
| `data/lobby/donations.json` | Dons politiques (FEC, US) | `entity_id, recipient, amount_usd, cycle` |
| `data/finance/stocks.json` | Séries boursières + anomalies | `symbol, series[], change_1m_pct, anomaly_pct` |
| `data/news/news.json` | Articles matchés | `entity_ids, tags, date, url` |
| `data/influence.json` | Score de pression entreprise ↔ loi | `score, signals{news,register,donations,stock}, reasons` |
| `data/alerts.json` | Alertes générées | `severity, kind, title, body` |
| `data/meta.json` | État du run | `updated_at, counts, sources` |

## Sources

| Source | Juridiction | Accès |
|---|---|---|
| Parlement européen — procédure search API / procédure feed | UE | gratuit |
| Transparency Register UE | UE | gratuit |
| data.assemblee-nationale.fr (dossiers législatifs) | FR | gratuit |
| HATVP — répertoire des représentants d'intérêts | FR | gratuit |
| Congress.gov API v3 | US | clé gratuite |
| LDA (Lobbying Disclosure Act) bulk data | US | gratuit |
| FEC API (dons) | US | clé gratuite |
| Yahoo Finance chart API (bourse) | — | gratuit |
| GDELT 2.0 / NewsAPI (presse) | — | gratuit / clé |

## Score de pression

```
score = 45·presse + 25·registre + 15·dons + 15·marché   (normalisé 0–100)
```

Estimation heuristique de pression probable — pas une accusation. Chaque signal est traçable.

## Gouvernance (hub ai-ecosystem)

- Un produit = un repo = un nom : `lobby-mirror`.
- Sorties normalisées, schémas stables (voir tableaux ci-dessus) — réutilisables comme dataset du hub.
- Secrets (`CONGRESS_API_KEY`, `FEC_API_KEY`, `NEWSAPI_KEY`, `RESEND_API_KEY`) dans `~/.hermes/.env` / `.env.local`, jamais committés.
- Licence : MIT (données : licences respectives des producteurs, citées dans `web/src/views/Methodo.tsx`).
