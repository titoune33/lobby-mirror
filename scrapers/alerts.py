"""
générateur d'alertes — alerts.json

Types :
  pression_forte   score entité↔loi ≥ 60                        → critical
  vote_proche      loi avec date d'étape sous 7 jours + entités  → warning
  nouvelle_loi     texte déposé sous 7 jours + thématique chaude → info
  anomalie_bourse  mouvement |≥5%| en 1 mois                     → warning
  registre         nouvelle inscription détectée                 → info

Les ids sont des hashes de contenu : rejouer le même run ne duplique pas.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from glob import glob
from pathlib import Path

from lib import DATA_DIR, entities_list, load_json, save_json


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


def _days_until(iso: str) -> int | None:
    try:
        d = datetime.fromisoformat(iso[:10]).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return (d - datetime.now(timezone.utc)).days


def build_alerts() -> list[dict]:
    entities = {e["id"]: e for e in entities_list()}
    laws = load_json(DATA_DIR / "laws" / "laws.json", [])
    influence = load_json(DATA_DIR / "influence.json", {})
    stocks = load_json(DATA_DIR / "finance" / "stocks.json", {})
    regs: list[dict] = []
    for f in glob(str(DATA_DIR / "lobby" / "*.json")):
        if Path(f).name in ("registrations.json", "donations.json"):
            continue
        regs.extend(load_json(f, []) or [])
    alerts: list[dict] = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 1. pression forte
    for eid, edges in influence.items():
        for edge in edges:
            if edge["score"] >= 60:
                law = next((l for l in laws if l["id"] == edge["law_id"]), None)
                if not law:
                    continue
                name = entities[eid]["name"]
                alerts.append({
                    "id": _id("pression", eid, edge["law_id"]),
                    "date": now,
                    "severity": "critical",
                    "kind": "pression_forte",
                    "title": f"{name} pousse le texte {law['id']}",
                    "body": f"Score de pression {edge['score']:.0f}/100 — {law['title']}. "
                            f"Signaux : {edge['signals']['news']:.0f} articles, registre, dons, marché.",
                    "entity_id": eid,
                    "law_id": law["id"],
                })

    # 2. vote / étape proche
    for law in laws:
        nxt = law.get("dates", {}).get("next_step")
        if not nxt:
            continue
        d = _days_until(nxt)
        if d is not None and 0 <= d <= 7 and law.get("entities"):
            names = ", ".join(entities[eid]["name"] for eid in law["entities"][:3])
            alerts.append({
                "id": _id("vote", law["id"], nxt),
                "date": now,
                "severity": "warning",
                "kind": "vote_proche",
                "title": f"Échéance sous {max(d, 1)} j : {law['id']}",
                "body": f"{law['title']} — étape prévue le {nxt[:10]}. "
                        f"Entreprises impliquées : {names}.",
                "law_id": law["id"],
            })

    # 3. textes récents à thématique sensible
    for law in laws:
        intro = law.get("dates", {}).get("introduced")
        if not intro:
            continue
        d = _days_until(intro)
        if d is not None and -7 <= d <= 0 and law.get("tags"):
            alerts.append({
                "id": _id("nouvelle_loi", law["id"], intro),
                "date": now,
                "severity": "info",
                "kind": "nouvelle_loi",
                "title": f"Nouveau texte déposé : {law['id']} ({law['jurisdiction']})",
                "body": f"{law['title']} — thématiques : {', '.join(law['tags'])}.",
                "law_id": law["id"],
            })

    # 4. anomalies boursières
    for eid, stock in stocks.items():
        chg = stock.get("change_1m_pct")
        if chg is not None and abs(chg) >= 5:
            alerts.append({
                "id": _id("bourse", eid, str(round(chg, 1))),
                "date": now,
                "severity": "warning",
                "kind": "anomalie_bourse",
                "title": f"{entities[eid]['name']} : {chg:+.1f}% sur un mois",
                "body": f"Variation boursière inhabituelle sur 1 mois ({stock['symbol']}). "
                        f"À croiser avec l'agenda législatif de l'entreprise.",
                "entity_id": eid,
            })

    # 5. nouvelles inscriptions au registre
    for r in regs:
        try:
            yr = int(str(r.get("year") or "")[:4])
        except (ValueError, TypeError):
            continue
        if datetime.now().year - yr <= 1:
            alerts.append({
                "id": _id("registre", r["id"]),
                "date": now,
                "severity": "info",
                "kind": "registre",
                "title": f"{entities[r['entity_id']]['name']} inscrit au registre {r['registry']}",
                "body": f"Déclaration d'intérêts ({r.get('registrant_type', '')}). "
                        f"Domaines : {', '.join(r.get('domains', []))}.",
                "entity_id": r["entity_id"],
            })

    alerts.sort(key=lambda a: (a["severity"] != "critical", a["severity"] != "warning", a["date"]), reverse=False)
    save_json(DATA_DIR / "alerts.json", alerts)
    print(f"[alerts] {len(alerts)} alerte(s) générée(s)")
    return alerts
