"""Source : LDA (Lobbying Disclosure Act) — bulk data US.

État actuel : les bulk zips du Sénat et l'API lda.gov répondent 403 (protection
anti-bot Cloudflare) depuis notre réseau. Ce module tente les deux chemins et
se dégrade gracieusement en produisant un fichier vide + un état documenté.
"""
from __future__ import annotations

import lib

ATTEMPTS = [
    ("lda.gov API", "https://lda.gov/api/v1/filings", {"format": "json"}),
    ("Sénat bulk", "https://www.senate.gov/legislative/Public_Disclosure/LDA_2016_Q4.zip", None),
]


def run() -> dict:
    registrations: list[dict] = []
    status = "vide"
    for name, url, params in ATTEMPTS:
        try:
            resp = lib.http_get(url, params=params, timeout=30, retries=1)
            if resp.ok:
                status = f"OK via {name}"
                # le parsing des XML LDA n'est pas implémenté (accès refusé au moment du build)
                break
            lib.log.warning("LDA %s : HTTP %s", name, resp.status_code)
        except Exception as err:
            lib.log.warning("LDA %s : %s", name, err)
    lib.save_json(lib.DATA_DIR / "lobby" / "us_lda.json", registrations)
    return {"summary": f"LDA US : {status}", "count": len(registrations)}
