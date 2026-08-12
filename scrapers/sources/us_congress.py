"""Source : Congress.gov API v3 — projets de loi récents (congrès 119).

Clé : env CONGRESS_API_KEY (gratuite, api.congress.gov/sign-up) sinon DEMO_KEY
(30 req/h, suffisant pour ce volume).
"""
from __future__ import annotations

import os

import lib

BASE = "https://api.congress.gov/v3"
KEY = os.environ.get("CONGRESS_API_KEY", "DEMO_KEY")
CONGRESS = 119  # 2025-2026


def _bills(offset: int, limit: int = 250) -> list[dict]:
    data = lib.http_get_json(
        f"{BASE}/bill/{CONGRESS}",
        params={
            "api_key": KEY,
            "limit": limit,
            "offset": offset,
            "fromDateTime": "2025-01-03T00:00:00Z",
            "toDateTime": "2026-12-31T23:59:59Z",
            "sort": "updateDate+desc",
        },
        cache_ttl=24 * 3600,
    )
    return data.get("bills", [])


def run() -> dict:
    from match import tag_law

    laws: list[dict] = []
    for offset in (0, 250):
        try:
            batch = _bills(offset)
        except Exception as err:
            lib.log.warning("congress.gov offset %d : %s", offset, err)
            break
        if not batch:
            break
        for b in batch:
            la = b.get("latestAction") or {}
            laws.append({
                "id": f"{CONGRESS}-{b.get('type', '').upper()}{b.get('number', '')}",
                "jurisdiction": "US",
                "title": b.get("title") or "(titre indisponible)",
                "status": la.get("text") or "—",
                "type": b.get("type"),
                "dates": {
                    "introduced": (b.get("introducedDate") or "")[:10] or None,
                    "updated": (b.get("updateDate") or "")[:10] or None,
                    "next_step": (la.get("actionDate") or "")[:10] or None,
                },
                "committee": None,
                "tags": tag_law(b.get("title") or ""),
                "url": f"https://www.congress.gov/bill/{CONGRESS}th-congress/{b.get('type', '')}-bill/{b.get('number', '')}",
            })
        if len(batch) < 250:
            break
    laws = lib.dedupe(laws, key_fn=lambda l: l["id"])
    lib.save_json(lib.DATA_DIR / "laws" / "us.json", laws)
    return {"summary": f"{len(laws)} bills US", "count": len(laws)}
