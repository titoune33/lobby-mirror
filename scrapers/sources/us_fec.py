"""Source : FEC API — dons politiques (US).

1. /v1/names/committees/?q=<nom>  → PACs liés à l'entreprise
2. /v1/committee/{id}/schedules/schedule_a/ → contributions aux candidats

Clé : env FEC_API_KEY (gratuite, api.data.gov/signup) sinon DEMO_KEY (40 req/h).
Le rate-limit est géré avec dégradation gracieuse : résultats partiels conservés.
"""
from __future__ import annotations

import os
import time

import lib

BASE = "https://api.open.fec.gov/v1"
KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")
CYCLE = "2026"


def _find_pacs(name: str) -> list[dict]:
    data = lib.http_get_json(
        f"{BASE}/names/committees/",
        params={"api_key": KEY, "q": name},
        cache_ttl=7 * 86400,
    )
    results = data.get("results", [])
    # comités "de type PAC" : P/N/O/Q/V/W (sans les comités de candidats H/S)
    return [r for r in results if r.get("committee_type") not in ("H", "S", "C", "D", "E", "X", "Y", "Z", "I", "J", "K", "U")]


def _contributions(committee_id: str) -> list[dict]:
    data = lib.http_get_json(
        f"{BASE}/committee/{committee_id}/schedules/schedule_a/",
        params={
            "api_key": KEY,
            "two_year_transaction_period": CYCLE,
            "per_page": 100,
            "sort": "-contribution_receipt_amount",
        },
        cache_ttl=7 * 86400,
    )
    return data.get("results", [])


def run() -> dict:
    donations: list[dict] = []
    seen_candidates: set[tuple[str, str]] = set()
    rate_limited = False
    for e in lib.entities_list():
        # seules les entités ayant une présence US plausible font l'objet d'une recherche
        name = e["name"].split("/")[0]
        try:
            pacs = _find_pacs(name)
        except Exception as err:
            if "429" in str(err) or "RATE" in str(err).upper():
                rate_limited = True
                lib.log.warning("FEC rate-limité sur %s — arrêt gracieux", name)
                break
            continue
        for pac in pacs[:2]:
            cid = pac.get("committee_id")
            if not cid:
                continue
            try:
                contribs = _contributions(cid)
            except Exception as err:
                if "429" in str(err) or "RATE" in str(err).upper():
                    rate_limited = True
                    break
                continue
            for c in contribs:
                last = c.get("candidate_last_name")
                first = c.get("candidate_first_name")
                if not last:
                    continue
                key = (str(last), str(first or ""))
                if key in seen_candidates:
                    continue
                seen_candidates.add(key)
                donations.append({
                    "id": f"FEC-{c.get('sub_id') or cid}",
                    "entity_id": e["id"],
                    "recipient": f"{first} {last}".strip(),
                    "office": f"{c.get('candidate_office') or ''} {c.get('candidate_state') or ''}".strip(),
                    "amount_usd": float(c.get("contribution_receipt_amount") or 0),
                    "cycle": CYCLE,
                    "source": "FEC",
                })
            if rate_limited:
                break
            time.sleep(1.0)
        if rate_limited:
            break
        time.sleep(1.0)
    lib.save_json(lib.DATA_DIR / "lobby" / "donations.json", donations)
    note = " (rate-limité, partiel)" if rate_limited else ""
    return {"summary": f"{len(donations)} dons FEC{note}", "count": len(donations)}
