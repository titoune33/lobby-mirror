"""Source : Parlement européen — votes récents en plénière + procédures actives.

Stratégie (API Open Data v2, en-tête User-Agent requis) :
  A. /meetings?year=2026            → séances plénières de l'année
     /meetings/{sitting}/vote-results → rapports votés (titres FR, ids A-10-…)
  B. /procedures/feed?timeframe=one-month → procédures avec activité récente
     /procedures/{process-id}            → détail (titre, étape, dates)
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import lib

BASE = "https://data.europarl.europa.eu/api/v2"
HEADERS = {
    "Accept": "application/ld+json",
    "User-Agent": "lobby-mirror/0.1 (analyse influence législative; contact: github.com/titoune33)",
}

STAGE_FR = {
    "RDG1": "1ère lecture",
    "RDG2": "2ème lecture",
    "RDG3": "3ème lecture",
    "APPR": "Approbation",
    "AVIS": "Avis",
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fr(activity_label: dict) -> str | None:
    return activity_label.get("fr") or activity_label.get("mul") or activity_label.get("en")


def _votes_recentes(days: int = 60) -> list[dict]:
    laws: list[dict] = []
    year = datetime.now(timezone.utc).year
    meetings = lib.http_get_json(
        f"{BASE}/meetings",
        params={"year": year, "limit50": 80},
        headers=HEADERS,
        cache_ttl=6 * 3600,
    ).get("data", [])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    sittings = [
        m for m in meetings
        if m.get("activity_start_date", "")[:10] >= cutoff
        and m.get("activity_start_date", "")[:10] <= _today()
    ]
    for m in sittings[-4:]:  # ~1 mois de séances
        sid = m.get("activity_id")
        if not sid:
            continue
        try:
            votes = lib.http_get_json(
                f"{BASE}/meetings/{sid}/vote-results",
                params={"limit50": 100},
                headers=HEADERS,
                cache_ttl=24 * 3600,
            ).get("data", [])
        except Exception as err:
            lib.log.warning("votes %s : %s", sid, err)
            continue
        for v in votes:
            label = _fr(v.get("activity_label") or {}) or ""
            if not label:
                continue
            reports = v.get("based_on_a_realization_of") or []
            law_id = reports[0] if reports else v.get("id", "")
            pv = (v.get("recorded_in_a_realization_of") or [None])[0]
            laws.append({
                "id": law_id,
                "jurisdiction": "EU",
                "title": label.replace("***I", "").replace("***", "").strip(),
                "status": "Voté en plénière",
                "type": "COD" if "***I" in label else "RSP",
                "dates": {
                    "introduced": None,
                    "updated": (v.get("activity_date") or "")[:10] or None,
                    "next_step": None,
                },
                "committee": None,
                "tags": [],
                "url": f"https://www.europarl.europa.eu/doceo/document/{pv}_EN.html" if pv else None,
            })
    return laws


def _procedures_feed() -> list[dict]:
    laws: list[dict] = []
    feed = lib.http_get_json(
        f"{BASE}/procedures/feed",
        params={"timeframe": "one-month"},
        headers=HEADERS,
        cache_ttl=6 * 3600,
    )
    proc_ids: set[str] = set()
    for item in feed.get("data", []):
        m = re.match(r"eli/dl/proc/(\d{4}-\d{4})", item.get("id", ""))
        if m:
            proc_ids.add(m.group(1))
        elif item.get("process_id"):
            proc_ids.add(item["process_id"])
    for pid in sorted(proc_ids)[:60]:
        try:
            det = lib.http_get_json(
                f"{BASE}/procedures/{pid}", headers=HEADERS, cache_ttl=24 * 3600
            ).get("data", [None])[0]
        except Exception:
            continue
        if not det:
            continue
        title = _fr(det.get("process_title") or {}) or det.get("label", "")
        activities = det.get("consists_of", [])
        dates = sorted((a.get("activity_date") for a in activities if a.get("activity_date")))
        stage = (det.get("current_stage") or "").split("/")[-1]
        laws.append({
            "id": det.get("label") or pid,
            "jurisdiction": "EU",
            "title": title,
            "status": STAGE_FR.get(stage, stage or "En cours"),
            "type": (det.get("process_type") or "").split("/")[-1],
            "dates": {
                "introduced": dates[0] if dates else None,
                "updated": dates[-1] if dates else None,
                "next_step": None,
            },
            "committee": None,
            "tags": [],
            "url": f"https://oeil.secure.europarl.europa.eu/oeil/popups/ficheprocedure.do?reference={det.get('label', '')}",
        })
    return laws


def run() -> dict:
    from match import tag_law

    laws = lib.dedupe(_votes_recentes() + _procedures_feed(), key_fn=lambda l: l["id"])
    for l in laws:
        if not l.get("tags"):
            l["tags"] = tag_law(l["title"])
    laws.sort(key=lambda l: l["dates"].get("updated") or "", reverse=True)
    lib.save_json(lib.DATA_DIR / "laws" / "eu.json", laws)
    return {"summary": f"{len(laws)} lois/votes UE", "count": len(laws)}
