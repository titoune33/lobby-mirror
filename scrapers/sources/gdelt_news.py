"""Source : GDELT 2.0 — presse mondiale.

2 requêtes par entité (thème lobbying + thème législatif), fenêtre 30 j,
intervalle obligatoire de 5 s entre requêtes (politesse GDELT).
Chaque article est ré-assigné à toutes les entités mentionnées dans son titre.
"""
from __future__ import annotations

import time
import urllib.parse

import lib

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
SLEEP = 5.2


def _query(q: str) -> list[dict]:
    data = lib.http_get_json(
        BASE,
        params={
            "query": q,
            "mode": "artlist",
            "maxrecords": 50,
            "timespan": "30d",
            "format": "json",
            "sort": "datedesc",
        },
        cache_ttl=6 * 3600,
        retries=2,
    )
    return data.get("articles", [])


def _search_term(e: dict) -> str:
    """Terme de recherche : nom court (sinon l'alias le plus long si nom < 3 chars).

    'Alphabet / Google' → 'Google' ; 'BP' → 'British Petroleum'.
    GDELT exige des phrases ≥ 3 caractères et matche en phrase exacte :
    un alias long type « LVMH Moët Hennessy… » ne renverrait rien.
    """
    name = e["name"].split("/")[-1].strip()
    if len(lib.normalize_name(name)) >= 3:
        return name
    candidates = [c for c in e.get("aliases", []) if len(lib.normalize_name(c)) >= 3]
    return max(candidates, key=lambda c: len(lib.normalize_name(c)))


def _iso(seendate: str) -> str:
    if not seendate or len(seendate) < 8:
        return ""
    d = seendate[:8]
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}"


# Médias jugés sérieux : un article n'y mentionnant pas l'entité dans le titre
# reste crédible (GDELT matche le corps du texte).
REPUTABLE_DOMAINS = {
    "reuters.com", "apnews.com", "bloomberg.com", "ft.com", "wsj.com", "nytimes.com",
    "washingtonpost.com", "theguardian.com", "bbc.co.uk", "bbc.com", "cnn.com",
    "nbcnews.com", "cbsnews.com", "abcnews.go.com", "politico.com", "politico.eu",
    "euractiv.com", "thehill.com", "rollcall.com", "axios.com", "propublica.org",
    "theintercept.com", "opensecrets.org", "lobbyfacts.eu", "corporateeurope.org",
    "lemonde.fr", "lefigaro.fr", "lesechos.fr", "liberation.fr", "mediapart.fr",
    "la-croix.com", "lepoint.fr", "lexpress.fr", "challenges.fr", "latribune.fr",
    "franceinfo.fr", "francetvinfo.fr", "20minutes.fr", "ouest-france.fr",
    "leparisien.fr", "la-croix.com", "humanite.fr", "publicsenat.fr", "lcp.fr",
    "capital.fr", "bfmtv.com", "radiofrance.fr", "contexte.com", "lagazettedescommunes.com",
}


def _credible(term: str, title: str, domain: str) -> bool:
    """L'article mentionne l'entité dans le titre OU vient d'un média sérieux."""
    if domain in REPUTABLE_DOMAINS:
        return True
    tn = lib.normalize_name(term)
    return len(tn) >= 5 and tn in lib.normalize_name(title)


def run() -> dict:
    from match import tag_law

    articles: dict[str, dict] = {}
    queries_done = 0
    for e in lib.entities_list():
        term = _search_term(e)
        q_lobby = f'"{term}" (lobbying OR lobbyist OR "representants d\'interets" OR influence)'
        q_legis = f'"{term}" (loi OR directive OR legislation OR "projet de loi" OR bill OR congress OR parlement OR senate)'
        for q in (q_lobby, q_legis):
            # sommeil intelligent : inutile d'attendre 5 s si la réponse est en cache
            cache_probe = lib.CACHE_DIR / (
                __import__("hashlib").sha1((BASE + __import__("json").dumps({
                    "query": q, "mode": "artlist", "maxrecords": 50,
                    "timespan": "30d", "format": "json", "sort": "datedesc",
                }, sort_keys=True)).encode()).hexdigest() + ".bin"
            )
            try:
                items = _query(q)
            except Exception as err:
                lib.log.warning("gdelt %s : %s", term, err)
                items = []
            for it in items:
                title = it.get("title") or ""
                url = it.get("url") or ""
                domain = (it.get("domain") or "").replace("www.", "")
                if not url or not title or not _credible(term, title, domain):
                    continue
                eids = []
                for cand in lib.entities_list():
                    hit = lib.match_entity(title)
                    if hit and hit[0] not in eids:
                        eids.append(hit[0])
                if not eids and term in lib.normalize_name(title):
                    eids = [e["id"]]
                if not eids:
                    continue
                key = url
                if key not in articles:
                    articles[key] = {
                        "id": f"GDELT-{key[-30:]}",
                        "date": _iso(it.get("seendate", "")),
                        "title": title,
                        "url": url,
                        "source": (it.get("domain") or "").replace("www.", ""),
                        "entity_ids": eids,
                        "tags": tag_law(title),
                    }
                else:
                    articles[key]["entity_ids"] = sorted(set(articles[key]["entity_ids"] + eids))
            queries_done += 1
            time.sleep(0.2 if cache_probe.exists() else SLEEP)
    news = sorted(articles.values(), key=lambda a: a["date"], reverse=True)
    lib.save_json(lib.DATA_DIR / "news" / "news.json", news)
    return {"summary": f"{len(news)} articles ({queries_done} requêtes GDELT)", "count": len(news)}
