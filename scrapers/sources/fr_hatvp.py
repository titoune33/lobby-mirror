"""Source : HATVP — répertoire des représentants d'intérêts.

Deux fichiers :
  1. agora_repertoire_opendata.json (137 Mo) : identités des 4 065 organisations
  2. Vues_Separees_CSV.zip (14 Mo) : 15 tables détaillées — domaines d'intervention,
     décisions visées (lois ciblées !), montants de dépenses par tranche.

Jointures : siren = identifiantNational (JSON) ↔ identifiant_national (CSV 1).
décisions → 12(action_id) → 14(activite_id) → 8(exercices_id) → 15(representants_id).
"""
from __future__ import annotations

import csv
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import lib

URL_JSON = "https://www.hatvp.fr/agora/opendata/agora_repertoire_opendata.json"
URL_CSV = "https://www.hatvp.fr/agora/opendata/csv/Vues_Separees_CSV.zip"
CACHE_JSON = lib.RAW_DIR / "hatvp_repertoire.json"
CACHE_ZIP = lib.RAW_DIR / "hatvp_vues.zip"
CSV_DIR = lib.RAW_DIR / "hatvp_vues"
MAX_AGE = 7 * 86400


def _download(url: str, cache: Path) -> Path:
    if cache.exists() and (time.time() - cache.stat().st_mtime) < MAX_AGE:
        lib.log.info("HATVP %s : en cache", cache.name)
        return cache
    lib.log.info("téléchargement %s…", cache.name)
    lib.RAW_DIR.mkdir(parents=True, exist_ok=True)
    resp = lib.http_get(url, timeout=600, retries=2)
    resp.raise_for_status()
    tmp = cache.with_suffix(".part")
    tmp.write_bytes(resp.content)
    tmp.replace(cache)
    return cache


def _csv_map(name: str) -> list[dict]:
    path = CSV_DIR / name
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _extract_csv() -> None:
    """Extrait le zip et résout le sous-dossier réel (Vues_Separees/…)."""
    global CSV_DIR
    first = next(CSV_DIR.rglob("1_informations_generales.csv"), None)
    if first is not None:
        CSV_DIR = first.parent
        return
    import shutil

    if CSV_DIR.exists():
        shutil.rmtree(CSV_DIR)
    with zipfile.ZipFile(CACHE_ZIP) as zf:
        zf.extractall(CSV_DIR)
    first = next(CSV_DIR.rglob("1_informations_generales.csv"), None)
    if first is None:
        raise RuntimeError("1_informations_generales.csv introuvable dans le zip HATVP")
    CSV_DIR = first.parent


def _enrich_index() -> dict[str, dict]:
    """siren → {rep_id, domaines, montants, décisions}."""
    # 1 : representants_id ↔ identifiant_national
    siren2rep: dict[str, str] = {}
    for row in _csv_map("1_informations_generales.csv"):
        siren = (row.get("identifiant_national") or "").strip()
        if siren:
            siren2rep[siren] = row["representants_id"]

    # 8 : activite_id → exercices_id + objets d'activité (texte libre) ;
    # 15 : exercices_id → representants_id + montants
    act2ex: dict[str, str] = {}
    objs: list[tuple[str, str]] = []
    for row in _csv_map("8_objets_activites.csv"):
        act2ex[row["activite_id"]] = row["exercices_id"]
        objs.append((row["exercices_id"], (row.get("objet_activite") or "").strip()))
    ex2rep: dict[str, str] = {}
    ex_montants: dict[str, tuple[str, str]] = {}
    for row in _csv_map("15_exercices.csv"):
        ex2rep[row["exercices_id"]] = row["representants_id"]
        inf = (row.get("montant_depense_inf") or "").strip()
        sup = (row.get("montant_depense_sup") or "").strip()
        if inf or sup:
            ex_montants[row["exercices_id"]] = (inf, sup)

    # 7 : domaines → activite_id
    dom_by_act: dict[str, set[str]] = defaultdict(set)
    for row in _csv_map("7_domaines_intervention.csv"):
        dom_by_act[row["activite_id"]].add((row.get("domaines_intervention_actions_menees") or "").strip())

    out: dict[str, dict] = {}
    for siren, rep_id in siren2rep.items():
        # domaines via les exercices du représentant ; objets d'activité déclarés
        domaines: set[str] = set()
        montants: list[tuple[str, str]] = []
        activites: set[str] = set()
        for ex_id, r_id in ex2rep.items():
            if r_id != rep_id:
                continue
            if ex_id in ex_montants:
                montants.append(ex_montants[ex_id])
            for act, doms in dom_by_act.items():
                if act2ex.get(act) == ex_id:
                    domaines |= {d for d in doms if d}
        for ex_id, objet in objs:
            if ex2rep.get(ex_id) == rep_id and objet:
                activites.add(objet[:200])
        out[siren] = {
            "rep_id": rep_id,
            "domaines": domaines,
            "activites": activites,
            "montants": montants,
        }
    return out


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
    _download(URL_JSON, CACHE_JSON)
    _download(URL_CSV, CACHE_ZIP)
    _extract_csv()
    lib.log.info("indexation des vues HATVP…")
    enrich = _enrich_index()

    data = lib.load_json(CACHE_JSON, {"publications": []})
    pubs = data.get("publications", [])
    registrations = []
    for pub in pubs:
        eid, field, conf = _match(pub)
        if not eid:
            continue
        siren = str(pub.get("identifiantNational") or "").strip()
        extra = enrich.get(siren, {})
        domaines_bruts = extra.get("domaines", set())
        tags = lib.map_eu_interests(sorted(domaines_bruts))
        if not tags:
            tags = [lib.normalize_name(d)[:24] for d in sorted(domaines_bruts)[:5]]
        montants = extra.get("montants", [])
        cost_band = None
        if montants:
            montants.sort(key=lambda m: float(m[1] or 0))
            _inf, sup = montants[-1]
            inf = montants[-1][0]
            cost_band = f"{inf}-{sup} €" if inf else f"≤ {sup} €"
        secteurs = (pub.get("activites") or {}).get("listSecteursActivites") or []
        labels = [s.get("label") for s in secteurs if s.get("label")]
        if not domaines_bruts:
            tags = lib.map_eu_interests(labels) or [lib.normalize_name(l)[:24] for l in labels[:5]]
        derniere = str(pub.get("dateDernierePublicationActivite") or "")
        year = derniere[-4:] if "/" in derniere else derniere[:4]
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
            "raw_domains": sorted(domaines_bruts)[:12],
            "cost_band": cost_band,
            "declared_activities": sorted(extra.get("activites", set()))[:12],
            "year": year or None,
            "url": f"https://www.hatvp.fr/fiche-organisation/?organisation={pub.get('identifiantNational', '')}",
        })
    lib.save_json(lib.DATA_DIR / "lobby" / "fr_hatvp.json", registrations)
    n_acts = sum(1 for r in registrations if r.get("declared_activities"))
    n_costs = sum(1 for r in registrations if r.get("cost_band"))
    return {"summary": f"{len(registrations)} org. (dont {n_costs} avec montants, {n_acts} avec activités)", "count": len(registrations)}
