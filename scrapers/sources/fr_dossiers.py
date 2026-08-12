"""Source : Assemblée nationale — dossiers législatifs open data (législature 17).

Zip de ~10 Mo, un JSON par dossier. On dérive le statut du dernier acte daté
de l'arbre `actesLegislatifs` et on ne garde que les dossiers actifs récents.
"""
from __future__ import annotations

import glob
import io
import json
import time
import zipfile
from pathlib import Path

import lib

URL = "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip"
CACHE_ZIP = lib.RAW_DIR / "an_dossiers.zip"
EXTRACT_DIR = lib.RAW_DIR / "an_dossiers"
MAX_AGE = 3 * 86400
WINDOW_DAYS = 540


def _download() -> Path:
    if CACHE_ZIP.exists() and (time.time() - CACHE_ZIP.stat().st_mtime) < MAX_AGE:
        lib.log.info("AN : zip en cache (%d Mo)", CACHE_ZIP.stat().st_size // 1_000_000)
        return CACHE_ZIP
    lib.log.info("téléchargement dossiers AN (10 Mo)…")
    lib.RAW_DIR.mkdir(parents=True, exist_ok=True)
    resp = lib.http_get(URL, timeout=300, retries=2)
    resp.raise_for_status()
    tmp = CACHE_ZIP.with_suffix(".part")
    tmp.write_bytes(resp.content)
    tmp.replace(CACHE_ZIP)
    # purge l'extraction précédente
    import shutil

    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)
    with zipfile.ZipFile(CACHE_ZIP) as zf:
        zf.extractall(EXTRACT_DIR)
    return CACHE_ZIP


def _walk_acts(node) -> list[tuple[str, str]]:
    """Parcours récursif : [(dateActe, nomCanonique)]."""
    out: list[tuple[str, str]] = []
    if isinstance(node, dict):
        if node.get("dateActe") and node.get("libelleActe"):
            out.append((node["dateActe"], node["libelleActe"].get("nomCanonique", "")))
        for v in node.values():
            out.extend(_walk_acts(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(_walk_acts(v))
    return out


def run() -> dict:
    _download()
    files = glob.glob(str(EXTRACT_DIR / "json" / "dossierParlementaire" / "*.json"))
    from match import tag_law

    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - WINDOW_DAYS * 86400))
    laws: list[dict] = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))["dossierParlementaire"]
        except (KeyError, json.JSONDecodeError, OSError):
            continue
        if d.get("legislature") != "17":
            continue
        acts = sorted(_walk_acts(d.get("actesLegislatifs")), key=lambda a: a[0])
        dated = [a for a in acts if a[0]]
        if not dated:
            continue
        updated = dated[-1][0][:10]
        if updated < cutoff:
            continue
        introduced = dated[0][0][:10]
        titre = (d.get("titreDossier") or {}).get("titre") or ""
        laws.append({
            "id": d["uid"],
            "jurisdiction": "FR",
            "title": titre,
            "status": dated[-1][1] or "En cours",
            "type": (d.get("procedureParlementaire") or {}).get("libelle"),
            "dates": {"introduced": introduced, "updated": updated, "next_step": None},
            "committee": None,
            "tags": tag_law(titre),
            "url": f"https://www.assemblee-nationale.fr/dyn/17/dossiers/{(d.get('titreDossier') or {}).get('titreChemin') or ''}",
        })
    laws.sort(key=lambda l: l["dates"]["updated"], reverse=True)
    laws = lib.dedupe(laws, key_fn=lambda l: l["id"])[:1200]
    lib.save_json(lib.DATA_DIR / "laws" / "fr.json", laws)
    return {"summary": f"{len(laws)} dossiers AN actifs", "count": len(laws)}
