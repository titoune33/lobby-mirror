"""
lobby-mirror — framework commun de scraping.

Respecte la spec du hub ai-ecosystem/packages/scraper :
- rate limiting + retry exponentiel + rotation d'User-Agent ;
- sortie normalisée (schémas stables dans data/) ;
- dédoublonnage par hash de contenu ;
- cache local (data/raw/cache) pour ne pas re-télécharger à chaque run.

Dépendances : requests, rapidfuzz (voir requirements.txt).
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import requests
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_DIR = RAW_DIR / "cache"

UA_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
]

log = logging.getLogger("lobby-mirror")


# ---------------------------------------------------------------- HTTP ----

def _ua() -> str:
    return random.choice(UA_LIST)


def http_get(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 45,
    retries: int = 3,
    backoff: float = 4.0,
    cache_ttl: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> requests.Response:
    """GET avec retry exponentiel, rotation d'UA et cache optionnel (secondes)."""
    s = session or requests.Session()
    key = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    cache_file = CACHE_DIR / f"{key}.bin"
    if cache_ttl is not None and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < cache_ttl:
            with open(cache_file, "rb") as f:
                body = f.read()
            log.debug("cache hit %s", url)
            resp = requests.Response()
            resp.status_code = 200
            resp._content = body  # type: ignore[attr-defined]
            resp.headers["content-type"] = "application/json"
            return resp
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            hdrs = {"User-Agent": _ua(), "Accept": "application/json,text/plain,*/*"}
            hdrs.update(headers or {})
            resp = s.get(url, params=params, headers=hdrs, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"{resp.status_code} on {url}", response=resp)
            if cache_ttl is not None and resp.ok:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                with open(cache_file, "wb") as f:
                    f.write(resp.content)
            return resp
        except requests.RequestException as err:
            last_err = err
            sleep = backoff * (2 ** attempt) + random.uniform(0, 1)
            log.warning("HTTP %s -> %s (essai %d/%d), sleep %.1fs", url, err, attempt + 1, retries, sleep)
            time.sleep(sleep)
    raise RuntimeError(f"Échec HTTP définitif sur {url}: {last_err}")


def http_get_json(url: str, **kw: Any) -> Any:
    resp = http_get(url, **kw)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------ stockage ----

def save_json(path: Path | str, obj: Any, sort_keys: bool = True) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=sort_keys), encoding="utf-8")
    tmp.replace(path)
    return path


def load_json(path: Path | str, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def content_hash(obj: Any) -> str:
    """Hash canonique pour dédoublonnage (spec hub : dédup par hash de contenu)."""
    return hashlib.sha1(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def dedupe(items: Iterable[dict], key_fn: Callable[[dict], Any]) -> list[dict]:
    seen: dict[str, dict] = {}
    for item in items:
        try:
            h = content_hash(key_fn(item))
        except (KeyError, TypeError):
            h = content_hash(item)
        if h not in seen:
            seen[h] = item
    return list(seen.values())


# -------------------------------------------------------- normalisation ----

LEGAL_SUFFIXES = (
    r"(?<![a-z])(sa|s\.a\.|sas|s\.a\.s\.|sarl|s\.a\.r\.l\.|sca|sei|se|nv|n\.v\.|ag|gmbh|"
    r"kgaa|kg|plc|ltd|llc|inc|corp|co|bv|b\.v\.|oy|oyj|ab|sarl|spa|s\.p\.a\.|sl|slu|eu|sci)"
    r"(?![a-z])\.?"
)


def normalize_name(name: str) -> str:
    """Normalisation agressive pour le matching multi-sources.

    'TotalEnergies SE'  -> 'totalenergies'
    'Électricité de France' -> 'electricite de france'
    """
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace("&", " et ")
    s = re.sub(LEGAL_SUFFIXES, " ", s, flags=re.IGNORECASE)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------- entités ------

_ENTITIES: Optional[dict] = None


def load_entities() -> dict:
    global _ENTITIES
    if _ENTITIES is None:
        _ENTITIES = load_json(ROOT / "scrapers" / "entities.json") or {"entities": []}
    return _ENTITIES


def entities_list() -> list[dict]:
    return load_entities()["entities"]


def _alias_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for e in entities_list():
        for alias in [e["name"], *e.get("aliases", [])]:
            idx[normalize_name(alias)] = e["id"]
    return idx


def resolve_entity(name: str) -> Optional[str]:
    """Match exact (normalisé) d'un nom vers l'id d'entité, sinon None."""
    return _alias_index().get(normalize_name(name))


def match_entity(name: str, threshold: int = 92) -> Optional[tuple[str, int]]:
    """Match exact puis flou (rapidfuzz) sur les alias normalisés.

    Renvoie (entity_id, score) ou None. Ne matche jamais sur des noms
    trop courts (< 4 chars normalisés) pour éviter les faux positifs.
    """
    norm = normalize_name(name)
    idx = _alias_index()
    if norm in idx:
        return idx[norm], 100
    if len(norm) < 4:
        return None
    best_id, best_score = None, 0
    for alias_norm, eid in idx.items():
        score = fuzz.ratio(norm, alias_norm)
        if score > best_score:
            best_id, best_score = eid, score
    if best_id is not None and best_score >= threshold:
        return best_id, best_score
    return None


def entity_by_id(eid: str) -> Optional[dict]:
    for e in entities_list():
        if e["id"] == eid:
            return e
    return None


def match_entity_loose(name: str) -> Optional[tuple[str, int]]:
    """Match exact/flou, puis par sous-chaîne pour capter les filiales.

    'TotalEnergies Renouvelables France' → totalenergies (confiance 75)
    Évite les faux positifs : l'alias doit faire ≥ 8 caractères normalisés.
    """
    hit = match_entity(name)
    if hit:
        return hit
    norm = normalize_name(name)
    for e in entities_list():
        for alias in [e["name"], *e.get("aliases", [])]:
            an = normalize_name(alias)
            if len(an) >= 8 and an in norm:
                return e["id"], 75
    return None


# Domaines déclarés du registre UE (libellés EN) → vocabulaire de tags FR
EU_INTEREST_MAP: dict[str, list[str]] = {
    "agriculture": ["agriculture", "food", "farming", "rural"],
    "pesticides": ["pesticides", "chemicals", "biocides"],
    "energie": ["energy", "oil", "gas", "fuels"],
    "climat": ["climate", "carbon", "environment", "emissions", "biodiversity"],
    "nucleaire": ["nuclear"],
    "renouvelables": ["renewable", "solar", "wind", "hydro"],
    "sante": ["health", "pharmaceutical", "medical", "patients", "tobacco"],
    "tabac": ["tobacco", "nicotine"],
    "numerique": ["digital", "internet", "artificial intelligence", "ai", "data protection", "platform", "cyber"],
    "telecoms": ["telecommunication", "5g", "spectrum"],
    "finance": ["banking", "financial", "insurance", "capital", "taxation", "crypto"],
    "defense": ["defence", "defense", "security", "military", "arms"],
    "transport": ["transport", "aviation", "rail", "mobility", "maritime"],
    "automobile": ["automotive", "motor", "vehicles", "cars"],
    "environnement": ["environment", "water", "waste", "pollution", "fisheries"],
    "btp": ["construction", "housing", "real estate"],
    "social": ["employment", "labour", "social", "pensions", "workers"],
    "commerce": ["trade", "retail", "consumer", "competition", "internal market"],
    "fiscalite": ["taxation", "fiscal"],
}


def map_eu_interests(interest_names: list[str]) -> list[str]:
    """Libellés d'intérêts UE → tags normalisés (union)."""
    tags: set[str] = set()
    for name in interest_names:
        n = normalize_name(name)
        for tag, kws in EU_INTEREST_MAP.items():
            if any(kw in n for kw in kws):
                tags.add(tag)
    return sorted(tags)
