"""Source : HATVP — répertoire des représentants d'intérêts (JSON complet, ~137 Mo).

Fichier cache 7 j. Match sur denomination / nomUsage / sigle / ancienNom,
affiliations, puis clients (cabinets de lobbying).
"""
from __future__ import annotations

import time
from pathlib import Path

import lib

URL = "https://www.hatvp.fr/agora/opendata/agora_repertoire_opendata.json"
CACHE_FILE = lib.RAW_DIR / "hatvp_repertoire.json"
MAX_AGE = 7 * 86400


def _download() -> Path:
    if CACHE_FILE.exists() and (time.time() - CACHE_FILE.stat().st_mtime) < MAX_AGE:
        lib.log.info("HATVP : fichier en cache (%d Mo)", CACHE_FILE.stat().st_size // 1_000_000)
        return CACHE_FILE
    lib.log.info("téléchargement HATVP (137 Mo)…")
    lib.RAW_DIR.mkdir(parents=True, exist_ok=True)
    resp = lib.http_get(URL, timeout=600, retries=2)
    resp.raise_for_status()
    tmp = CACHE_FILE.with_suffix(".part")
    tmp.write_bytes(resp.content)
    tmp.replace(CACHE_FILE)
    return CACHE_FILE


def _match(pub: dict) -> tuple[str | None, str, int]:
    for key, field in [
        ("denomination", "name"),
        ("nomUsageHatvp", "name"),
        ("sigleHatvp", "name"),
        ("ancienNomHatvp", "name"),
    ]:
        val = pub.get(key)
        if val:
            hit = lib.match_entity_loose(str(val))
            if hit:
                return hit[0], field, hit[1]
    for aff in pub.get("affiliations", []) or []:
        hit = lib.match_entity_loose(aff.get("denomination", ""))
        if hit:
            return hit[0], "affiliation", hit[1]
    for c in pub.get("clients", []) or []:
        hit = lib.match_entity_loose(c.get("denomination", "") if isinstance(c, dict) else str(c))
        if hit:
            return hit[0], "client", hit[1]
    return None, "", 0


def run() -> dict:
    path = _download()
    data = lib.load_json(path, {"publications": []})
    pubs = data.get("publications", [])
    registrations = []
    for pub in pubs:
        eid, field, conf = _match(pub)
        if not eid:
            continue
        secteurs = (pub.get("activites") or {}).get("listSecteursActivites") or []
        labels = [s.get("label") for s in secteurs if s.get("label")]
        tags = lib.map_eu_interests(labels)
        if not tags:
            tags = [lib.normalize_name(l) for l in labels if len(labels) < 5]
        registrations.append({
            "id": f"HATVP-{pub.get('identifiantNational') or 'inconnu'}",
            "registry": "HATVP",
            "entity_id": eid,
            "name": pub.get("denomination") or pub.get("nomUsageHatvp") or "",
            "match_field": field,
            "confidence": conf,
            "registrant_type": (pub.get("categorieOrganisation") or {}).get("label"),
            "clients": [c.get("denomination") if isinstance(c, dict) else str(c) for c in (pub.get("clients") or [])],
            "domains": tags,
            "cost_band": None,
            "year": (pub.get("dateDernierePublicationActivite") or "")[:4] or None,
            "url": f"https://www.hatvp.fr/fiche-organisation/?organisation={pub.get('identifiantNational', '')}",
        })
    lib.save_json(lib.DATA_DIR / "lobby" / "fr_hatvp.json", registrations)
    return {"summary": f"{len(registrations)} organisations matchées (HATVP)", "count": len(registrations)}
