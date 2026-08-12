#!/bin/bash
# Mise à jour complète locale : scrape + croisement + alertes + copie vers le web.
set -euo pipefail
cd "$(dirname "$0")/../scrapers"
env -u PYTHONPATH .venv/bin/python pipeline.py --all "$@"
