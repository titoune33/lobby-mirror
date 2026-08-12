"""méta-données du run + copie des sorties vers web/public/data."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from lib import DATA_DIR, ROOT, load_json, save_json

WEB_DATA = ROOT / "web" / "public" / "data"

FILES = [
    "laws/laws.json",
    "lobby/registrations.json",
    "lobby/donations.json",
    "finance/stocks.json",
    "news/news.json",
    "influence.json",
    "alerts.json",
]


def write_meta() -> dict:
    counts = {}
    for f in FILES:
        obj = load_json(DATA_DIR / f, [])
        key = "lobby" if "lobby" in f else "laws" if "laws" in f else Path(f).stem
        if isinstance(obj, dict):
            counts[key] = sum(len(v) for v in obj.values()) if key == "influence" else len(obj)
        else:
            counts[key] = len(obj)
    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": counts,
        "sources": [
            "Parlement européen (procédure feed)",
            "Transparency Register UE",
            "Assemblée nationale (open data)",
            "HATVP",
            "Congress.gov",
            "LDA (US)",
            "FEC (dons)",
            "Yahoo Finance",
            "GDELT / NewsAPI",
        ],
    }
    save_json(DATA_DIR / "meta.json", meta)
    return meta


def copy_to_web() -> None:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    # défauts vides : le front fetch chaque fichier, aucun ne doit manquer
    defaults = {
        "laws.json": [],
        "registrations.json": [],
        "donations.json": [],
        "stocks.json": {},
        "news.json": [],
        "influence.json": {},
        "alerts.json": [],
    }
    for f in FILES:
        src = DATA_DIR / f
        name = Path(f).name
        if src.exists():
            shutil.copy2(src, WEB_DATA / name)
        else:
            save_json(WEB_DATA / name, defaults[name])
    shutil.copy2(DATA_DIR / "meta.json", WEB_DATA / "meta.json")
    shutil.copy2(ROOT / "scrapers" / "entities.json", WEB_DATA / "entities.json")
    print(f"[meta] sorties copiées vers {WEB_DATA}")


if __name__ == "__main__":
    m = write_meta()
    copy_to_web()
    print(m)
