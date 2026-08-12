"""lobby-mirror — orchestrateur du pipeline de données.

Usage :
  pipeline.py --all                     # toutes les sources + croisement + alertes
  pipeline.py --source eu_registry      # une source précise
  pipeline.py --match --alerts          # recalcul croisement/alertes sans re-scraper
  pipeline.py --list                    # liste des sources disponibles
"""
from __future__ import annotations

import argparse
import importlib
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib  # noqa: E402

SOURCES = [
    "eu_procedures",
    "eu_registry",
    "fr_dossiers",
    "fr_hatvp",
    "us_congress",
    "us_fec",
    "us_lda",
    "yahoo_finance",
    "gdelt_news",
]


def run_source(name: str) -> None:
    mod = importlib.import_module(f"sources.{name}")
    result = mod.run()
    out = lib.DATA_DIR / f"raw/{name}.result.json"
    lib.save_json(out, result)
    print(f"[ok] {name}: {result.get('summary', '')}")


def merge_lobby() -> None:
    """Fusionne les registres par entité → lobby/registrations.json (pour le web)."""
    from glob import glob

    merged: dict[str, dict] = {}
    for f in glob(str(lib.DATA_DIR / "lobby" / "*.json")):
        name = f.rsplit("/", 1)[-1]
        if name in ("registrations.json", "donations.json"):
            continue
        for r in lib.load_json(f, []) or []:
            merged.setdefault(r["id"], r)
    lib.save_json(lib.DATA_DIR / "lobby" / "registrations.json", list(merged.values()))
    print(f"[merge] {len(merged)} enregistrement(s) de lobbying")


def main() -> None:
    ap = argparse.ArgumentParser(description="Pipeline de données lobby-mirror")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--source", action="append", default=[])
    ap.add_argument("--match", action="store_true", help="recalculer influence.json")
    ap.add_argument("--alerts", action="store_true", help="recalculer alerts.json")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--copy", action="store_true", help="copier les sorties vers web/public/data")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.list:
        for s in SOURCES:
            print(s)
        return

    sources = args.source if args.source else (SOURCES if args.all else [])
    for name in sources:
        try:
            run_source(name)
        except Exception as err:  # une source en échec ne bloque pas le reste
            logging.error("source %s en échec : %s", name, err)

    if args.all or args.match or args.alerts:
        if args.all or args.match:
            from match import build_influence

            build_influence()
        if args.all or args.alerts:
            from alerts import build_alerts

            build_alerts()

    if args.all:
        merge_lobby()

    if args.all or args.copy:
        merge_lobby()
        from meta import write_meta, copy_to_web

        write_meta()
        copy_to_web()
        print("[ok] sorties copiées vers web/public/data")

    if not (sources or args.match or args.alerts or args.list):
        ap.print_help()


if __name__ == "__main__":
    main()
