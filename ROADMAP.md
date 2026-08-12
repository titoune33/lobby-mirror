# ROADMAP — LobbyMirror

## MVP livré (v0.1)

- [x] Pipeline Python : 9 sources, cache, rate-limit, dédup, sorties normalisées
- [x] Watchlist de 34 entités (alias, tickers, domaines)
- [x] Moteur de croisement (presse + registre + dons + marché → score 0-100)
- [x] Générateur d'alertes (pression forte, vote proche, texte récent, anomalie bourse, registre)
- [x] Tableau de bord React (FR) : accueil, entreprises, lois, alertes, méthode
- [x] Workflow GitHub Actions (mise à jour quotidienne) + config Vercel + proxy Yahoo live

## Limitations connues

- **Dons FEC** : clé gratuite requise (DEMO_KEY = 40 req/h). → `FEC_API_KEY` dans les secrets.
- **LDA (lobbying US)** : bulk bloqué par protection anti-bot (403). → passer par une machine résidentielle ou l'API OpenSecrets (payante).
- **Calendrier de vote précis UE** : agenda plénière profond (points OJ) pas encore miné ; votes récents OK.
- **France** : pas de dons politiques individuels (financement public) — le signal « dons » est US-only.
- **Actualisation** : quotidienne (cron). Le « temps réel » strict demanderait un streamer (NewsAPI live, push parlementaire).

## Prochaines étapes (v0.2)

1. **Alertes sortantes** : email (Resend) / webhook Slack-Discord pour les abonnés ; configuration par entité et par seuil.
2. **Sujets de lois enrichis** : sujet/thème officiel (Congress subjects, AN sortRef, EP eurovoc) au lieu des tags par mots-clés.
3. **Registres enrichis** : montants déclarés HATVP (déclarations individuelles), LDA via source alternative.
4. **Page "Loi" dédiée** : chronologie des étapes + qui a été auditionné (AN : listes d'auditions open data).
5. **Comparateur** : entité vs entité sur un texte donné (qui pousse le plus fort).
6. **Monétisation** : abonnement B2B (alertes temps réel + API), rapports premium « Top 10 des lobbies influents ».
7. **API publique** `/api/...` : JSON croisé pour la presse et les ONG.

## Gouvernance hub

- Repo `lobby-mirror` ; données publiables en dataset hub (`datasets/lobby-transparence/`) avec README + schéma + licences sources.
- Secrets : `CONGRESS_API_KEY`, `FEC_API_KEY`, `RESEND_API_KEY` (Vercel/GitHub secrets, jamais dans le repo).
