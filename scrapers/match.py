"""
moteur de croisement — influence.json

Pour chaque couple (entité, loi), 4 signaux sont agrégés :
  presse   : articles co-mentionnant l'entité + la thématique de la loi
  registre : inscription au registre de lobbying de la juridiction
             + chevauchement domaines déclarés ↔ tags de la loi
  dons     : contributions politiques de l'entité (lois US uniquement)
  marché   : anomalie de cours autour des dates clés de la loi

Score = 45·presse + 25·registre + 15·dons + 15·marché, borné 0–100.
Estimation heuristique : pression probable, jamais une accusation.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path

from lib import DATA_DIR, entities_list, load_json, save_json, normalize_name

W_NEWS = 0.45
W_REGISTER = 0.20
W_DONATIONS = 0.15
W_STOCK = 0.15

JUR_REGISTRY = {"EU": "EU_TR", "FR": "HATVP", "US": "LDA"}

# Vocabulaire de tags commun lois ↔ domaines entités (FR + EN)
TAG_MAP: dict[str, list[str]] = {
    "agriculture": ["agricultur", "farm", "semence", "seed", "alimentation", "food"],
    "pesticides": ["pesticid", "glyphosate", "neonicotinoid", "biocide", "herbicide"],
    "energie": ["energy", "energ", "fuel", "carburant", "oil", "petrole", "gaz", "gas"],
    "climat": ["climat", "carbon", "carbone", "emission", "greenhouse", "ges", "deforestation"],
    "nucleaire": ["nuclear", "nucleaire", "epr"],
    "renouvelables": ["renewable", "renouvelable", "solar", "eolien", "wind", "photovoltaic"],
    "sante": ["health", "sante", "medical", "medicament", "drug", "pharma", "vaccin", "vaccine"],
    "tabac": ["tobacco", "tabac", "nicotine", "vaping", "vape", "cigarette"],
    "numerique": ["digital", "numerique", "platform", "plateforme", "internet", "ai act", "intelligence artificielle"],
    "telecoms": ["telecom", "5g", "fiber", "fibre", "spectrum", "frequence"],
    "finance": ["bank", "banque", "financ", "taxonomie", "capital", "crypto"],
    "defense": ["defence", "defense", "military", "militaire", "armement", "weapon"],
    "transport": ["transport", "mobility", "mobilite", "rail", "ferroviaire", "aviation"],
    "automobile": ["automotive", "automobile", "vehicle", "vehicule", "car", "co2"],
    "environnement": ["environment", "environnement", "pollution", "waste", "dechet", "eau", "water"],
    "btp": ["construction", "building", "buildings", "logement", "housing"],
    "fiscalite": ["tax", "fiscal", "taxation", "impot"],
    "social": ["social", "labour", "travail", "wage", "salaire", "pension"],
}


def tag_law(title: str) -> list[str]:
    """Tague un texte par mots-clés (titre normalisé).

    Les mots-clés courts (< 5 chars, ex. « car ») exigent une frontière de mot
    pour éviter les faux positifs (« cardio » → automobile).
    """
    t = normalize_name(title)
    tags = []
    for tag, kws in TAG_MAP.items():
        for kw in kws:
            if len(kw) < 5:
                if re.search(rf"\b{re.escape(kw)}\b", t):
                    tags.append(tag)
                    break
            elif kw in t:
                tags.append(tag)
                break
    return tags


def tags_for_entity(entity: dict) -> set[str]:
    """Domaines d'une entité traduits en vocabulaire de tags."""
    out: set[str] = set()
    for d in entity.get("domains", []):
        dn = normalize_name(d)
        for tag, kws in TAG_MAP.items():
            if any(kw in dn for kw in kws):
                out.add(tag)
                break
        else:
            out.add(dn)
    return out


def build_influence() -> dict:
    entities = entities_list()
    laws: list[dict] = []
    for f in glob(str(DATA_DIR / "laws" / "*.json")):
        if f.endswith("laws.json"):
            continue
        laws.extend(load_json(f, []) or [])
    laws = dedupe_by_id(laws)
    regs: list[dict] = []
    for f in glob(str(DATA_DIR / "lobby" / "*.json")):
        if Path(f).name == "registrations.json" or Path(f).name == "donations.json":
            continue
        regs.extend(load_json(f, []) or [])
    dons = load_json(DATA_DIR / "lobby" / "donations.json", [])
    stocks = load_json(DATA_DIR / "finance" / "stocks.json", {})
    news = load_json(DATA_DIR / "news" / "news.json", [])

    # pré-index
    regs_by_entity: dict[str, list[dict]] = defaultdict(list)
    for r in regs:
        regs_by_entity[r["entity_id"]].append(r)
    dons_by_entity: dict[str, list[dict]] = defaultdict(list)
    for d in dons:
        dons_by_entity[d["entity_id"]].append(d)
    news_by_entity: dict[str, list[dict]] = defaultdict(list)
    for n in news:
        for eid in n.get("entity_ids", []):
            news_by_entity[eid].append(n)

    influence: dict[str, list[dict]] = {e["id"]: [] for e in entities}
    entity_tags = {e["id"]: tags_for_entity(e) for e in entities}

    for law in laws:
        law["tags"] = tag_law(law.get("title", ""))  # recalcul propre à chaque run
        law_tags = set(law["tags"])
        law_jur = law.get("jurisdiction", "")
        law_title_norm = normalize_name(law.get("title", ""))
        law_keywords = law_tags | {t for t in law_title_norm.split() if len(t) > 4}
        introduced = law.get("dates", {}).get("introduced") or law.get("dates", {}).get("updated")

        for e in entities:
            eid = e["id"]
            signals = {"news": 0.0, "register": 0.0, "donations": 0.0, "stock": 0.0}
            reasons: list[str] = []

            # 1. presse : articles de l'entité dont le titre touche la thématique de la loi
            ent_news = news_by_entity.get(eid, [])
            matching_news = []
            for n in ent_news:
                title_norm = normalize_name(n.get("title", ""))
                if any(t in title_norm for t in law_keywords):
                    matching_news.append(n)
            n_matches = len(matching_news)
            signals["news"] = min(n_matches / 3.0, 1.0)
            if n_matches:
                reasons.append(f"{n_matches} article(s) de presse lient {e['name']} à cette thématique")

            # 2. registre : entité inscrite AU REGISTRE DE LA JURIDICTION de la loi,
            #    avec chevauchement thématique (ou citation explicite du texte).
            #    2 tags communs → signal plein ; 1 tag seul → signal partiel
            #    (ne suffit pas à créer un lien à lui seul).
            ent_regs = regs_by_entity.get(eid, [])
            jur_regs = [r for r in ent_regs if r.get("registry") == JUR_REGISTRY.get(law_jur)]
            if jur_regs:
                overlap = entity_tags[eid] & law_tags
                cited = any(
                    (r.get("eu_proposals_text") or "")
                    and any(k in normalize_name(r["eu_proposals_text"]) for k in law_keywords)
                    for r in jur_regs
                )
                if cited or len(overlap) >= 2:
                    signals["register"] = 1.0
                    if cited:
                        reasons.append("registre de lobbying (juridiction), texte explicitement suivi (déclaration UE)")
                    else:
                        reasons.append(f"registre de lobbying (juridiction), thématiques communes : {', '.join(sorted(overlap))}")
                elif len(overlap) == 1:
                    signals["register"] = 0.8
                    reasons.append(f"registre de lobbying (juridiction), thématique commune : {next(iter(overlap))}")

            # 3. dons : uniquement pour les lois US
            ent_dons = dons_by_entity.get(eid, [])
            if law_jur == "US" and ent_dons:
                total = sum(d.get("amount_usd", 0) for d in ent_dons)
                signals["donations"] = min(total / 500_000.0, 1.0)
                reasons.append(f"{total:,.0f} $ de dons politiques aux élus du cycle")

            # 4. marché : anomalie de cours autour de la date du texte
            stock = stocks.get(eid)
            anomaly = 0.0
            if stock and introduced:
                try:
                    d_intro = datetime.fromisoformat(introduced[:10])
                except ValueError:
                    d_intro = None
                if d_intro and stock.get("series"):
                    anomaly = window_anomaly(stock["series"], d_intro, days=10)
            if abs(anomaly) >= 0.03:
                signals["stock"] = min(abs(anomaly) / 0.10, 1.0)
                reasons.append(f"mouvement de bourse de {anomaly*100:+.1f}% autour de la date clé")

            score = 100 * (
                W_NEWS * signals["news"]
                + W_REGISTER * signals["register"]
                + W_DONATIONS * signals["donations"]
                + W_STOCK * signals["stock"]
            )
            if score >= 20:  # seuil : évite les liens trivials (registre seul, etc.)
                influence[eid].append(
                    {
                        "law_id": law["id"],
                        "score": round(score, 1),
                        "signals": {k: round(v, 3) for k, v in signals.items()},
                        "reasons": reasons,
                    }
                )

    # annoter les lois : entités liées + score max
    entity_by_id = {e["id"]: e for e in entities}
    linked: dict[str, set[str]] = defaultdict(set)
    max_score: dict[str, float] = {}
    for eid, edges in influence.items():
        for edge in edges:
            linked[edge["law_id"]].add(eid)
            max_score[edge["law_id"]] = max(max_score.get(edge["law_id"], 0), edge["score"])
    for law in laws:
        law["entities"] = sorted(linked.get(law["id"], set()), key=lambda x: entity_by_id[x]["name"])
        law["score"] = round(max_score.get(law["id"], 0), 1)

    save_json(DATA_DIR / "laws" / "laws.json", laws)
    save_json(DATA_DIR / "influence.json", influence)
    n_edges = sum(len(v) for v in influence.values())
    print(f"[match] {n_edges} liens entité ↔ loi, {sum(1 for l in laws if (l.get('score') or 0) > 0)} lois avec pression")
    return influence


def window_anomaly(series: list[dict], ref_date: datetime, days: int = 10) -> float:
    """Écart de cours entre J-`days` et J+3 autour d'une date de référence."""
    lo, hi = ref_date - timedelta(days=days), ref_date + timedelta(days=3)
    pts = []
    for p in series:
        try:
            d = datetime.fromisoformat(p["date"][:10])
        except (ValueError, TypeError):
            continue
        if lo <= d <= hi:
            pts.append((d, float(p["close"])))
    pts.sort(key=lambda x: x[0])
    if len(pts) < 4:
        return 0.0
    return (pts[-1][1] - pts[0][1]) / pts[0][1]


def dedupe_by_id(items: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for it in items:
        seen.setdefault(it["id"], it)
    return list(seen.values())
