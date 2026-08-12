"""Source : Transparency Register UE — export complet des organisations (XML).

114 Mo : téléchargement avec cache (7 j), puis parse en streaming (lxml
recover=True : le fichier contient des caractères XML invalides).
"""
from __future__ import annotations

import time
from pathlib import Path

import lib
from lxml import etree

URL = "https://ec.europa.eu/transparencyregister/public/files/ODP/download/XML/latest"
CACHE_FILE = lib.RAW_DIR / "eu_register.xml"
MAX_AGE = 7 * 86400


def _download() -> Path:
    if CACHE_FILE.exists() and (time.time() - CACHE_FILE.stat().st_mtime) < MAX_AGE:
        lib.log.info("registre UE : fichier en cache (%d Mo)", CACHE_FILE.stat().st_size // 1_000_000)
        return CACHE_FILE
    lib.log.info("téléchargement du registre UE (114 Mo)…")
    import requests

    lib.RAW_DIR.mkdir(parents=True, exist_ok=True)
    with requests.get(URL, stream=True, headers={"User-Agent": lib._ua()}, timeout=600) as r:
        r.raise_for_status()
        tmp = CACHE_FILE.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(CACHE_FILE)
    return CACHE_FILE


def _find_text(el, tag: str) -> str | None:
    for child in el.iter():
        if child.tag.endswith(tag):
            return (child.text or "").strip() or None
    return None


def _clients(el) -> list[str]:
    out = []
    for c in el.iter():
        if not c.tag.endswith("client"):
            continue
        cn = None
        name_el = c.find("name")
        if name_el is not None:
            cn = (name_el.text or "").strip()
        if not cn:
            cn = (c.text or "").strip()
        if cn:
            out.append(cn)
    return out


def _interests(el) -> list[str]:
    out = []
    for i in el.iter("interest"):
        name_el = i.find("name")
        if name_el is not None and (name_el.text or "").strip():
            out.append((name_el.text or "").strip())
    return out


def _cost_band(el) -> str | None:
    for child in el.iter():
        if child.tag.endswith("max"):
            v = (child.text or "").strip()
            if v:
                return v
    return None


def _match(reg_name: str | None, clients: list[str]) -> tuple[str | None, str, int]:
    if reg_name:
        hit = lib.match_entity_loose(reg_name)
        if hit:
            return hit[0], "name", hit[1]
    for c in clients:
        hit = lib.match_entity_loose(c)
        if hit:
            return hit[0], "client", hit[1]
    return None, "", 0


def run() -> dict:
    path = _download()
    registrations: list[dict] = []
    context = etree.iterparse(str(path), events=("end",), tag="interestRepresentative", recover=True, huge_tree=True)
    for _ev, el in context:
        # --- extraction complète AVANT el.clear() ---
        name = _find_text(el, "originalName")
        clients = _clients(el)
        interests = _interests(el)
        eid, field, conf = _match(name, clients)
        if eid:
            code = _find_text(el, "identificationCode") or "unknown"
            proposals_text = None
            for p in el.iter():
                if p.tag.endswith("EULegislativeProposals"):
                    proposals_text = (p.text or "")[:2000]
                    break
            registrations.append({
                "id": f"EU_TR-{code}",
                "registry": "EU_TR",
                "entity_id": eid,
                "name": name or (clients[0] if clients else ""),
                "match_field": field,
                "confidence": conf,
                "registrant_type": _find_text(el, "registrationCategory"),
                "clients": clients,
                "domains": lib.map_eu_interests(interests),
                "cost_band": _cost_band(el),
                "year": (_find_text(el, "lastUpdateDate") or "")[:4] or None,
                "eu_proposals_text": proposals_text,
                "url": f"https://transparency-register.europa.eu/searchregister-or-update/organisation-detail_en?id={code}",
            })
        el.clear()
    lib.save_json(lib.DATA_DIR / "lobby" / "eu_registrations.json", registrations)
    return {"summary": f"{len(registrations)} organisations matchées (registre UE)", "count": len(registrations)}
