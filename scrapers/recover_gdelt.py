"""Récupère les articles GDELT déjà présents dans le cache (sans re-quêter).

Utilitaire pour construire un news.json partiel pendant qu'un run complet
tourne encore, ou après un run interrompu.
"""
from __future__ import annotations

import glob
import json

import lib


def extract_from_cache() -> list[dict]:
    from match import tag_law
    from sources.gdelt_news import _iso, _search_term

    # rejouer les paires (entité, requête) pour retrouver la clé de cache de chacune
    import hashlib

    BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
    query_owner: dict[str, str] = {}  # clé de cache -> entity_id
    for e in lib.entities_list():
        term = _search_term(e)
        for q in (
            f'"{term}" (lobbying OR lobbyist OR "representants d\'interets" OR influence)',
            f'"{term}" (loi OR directive OR legislation OR "projet de loi" OR bill OR congress OR parlement OR senate)',
        ):
            params = {
                "query": q, "mode": "artlist", "maxrecords": 50,
                "timespan": "30d", "format": "json", "sort": "datedesc",
            }
            key = hashlib.sha1((BASE + json.dumps(params, sort_keys=True)).encode()).hexdigest() + ".bin"
            query_owner[key] = e["id"]

    articles: dict[str, dict] = {}
    for f in glob.glob(str(lib.CACHE_DIR / "*.bin")):
        owner = query_owner.get(f.rsplit("/", 1)[-1])
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for it in data.get("articles", []) or []:
            title = it.get("title") or ""
            url = it.get("url") or ""
            if not url or not title:
                continue
            eids = []
            for cand in lib.entities_list():
                hit = lib.match_entity(title)
                if hit and hit[0] not in eids:
                    eids.append(hit[0])
            if not eids and owner:
                eids = [owner]  # l'article vient de la requête de cette entité
            if not eids:
                continue
            if url not in articles:
                articles[url] = {
                    "id": f"GDELT-{url[-30:]}",
                    "date": _iso(it.get("seendate", "")),
                    "title": title,
                    "url": url,
                    "source": (it.get("domain") or "").replace("www.", ""),
                    "entity_ids": eids,
                    "tags": tag_law(title),
                }
            else:
                articles[url]["entity_ids"] = sorted(set(articles[url]["entity_ids"] + eids))
    news = sorted(articles.values(), key=lambda a: a["date"], reverse=True)
    lib.save_json(lib.DATA_DIR / "news" / "news.json", news)
    print(f"[gdelt-recover] {len(news)} articles depuis le cache")
    return news


if __name__ == "__main__":
    extract_from_cache()
