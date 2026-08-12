"""Source : Yahoo Finance chart API — séries boursières 1 an.

API non officielle : rythme très prudent (8 s entre symboles, 2 essais) car les
rafales déclenchent des blocs IP temporaires (429). Sauvegarde incrémentale :
chaque symbole réussi est écrit immédiatement, un re-run ne refait que les trous.
"""
from __future__ import annotations

import datetime
import time

import lib

BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}
SLEEP = 8.0


def _series(symbol: str) -> dict | None:
    try:
        data = lib.http_get_json(
            f"{BASE}/{symbol}",
            params={"range": "1y", "interval": "1d"},
            headers=HEADERS,
            cache_ttl=12 * 3600,
            retries=2,
            backoff=15.0,
            timeout=20,
        )
    except Exception as err:
        lib.log.warning("yahoo %s : %s", symbol, err)
        return None
    try:
        result = data["chart"]["result"][0]
    except (KeyError, IndexError, TypeError):
        return None
    ts = result.get("timestamp") or []
    quotes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    series = []
    for t, c in zip(ts, quotes):
        if c is None:
            continue
        d = datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
        series.append({"date": d.strftime("%Y-%m-%d"), "close": round(float(c), 4)})
    if len(series) < 5:
        return None
    return {"symbol": symbol, "series": series}


def _pct(series: list[dict], days: int) -> float | None:
    if len(series) <= days:
        return None
    start = float(series[-days - 1]["close"])
    end = float(series[-1]["close"])
    if not start:
        return None
    return round(100 * (end - start) / start, 2)


def _anomaly(series: list[dict]) -> float | None:
    """Plus grand |retour| sur fenêtre de 5 jours, sur les 90 derniers points."""
    closes = [float(p["close"]) for p in series][-90:]
    best = 0.0
    for i in range(len(closes) - 5):
        r = (closes[i + 5] - closes[i]) / closes[i]
        if abs(r) > abs(best):
            best = r
    return round(100 * best, 2) if best else None


def run() -> dict:
    stocks = lib.load_json(lib.DATA_DIR / "finance" / "stocks.json", {}) or {}
    ok = len(stocks)
    for e in lib.entities_list():
        if e["id"] in stocks:  # déjà acquis (sauvegarde incrémentale)
            continue
        tickers = e.get("tickers")
        if not tickers:
            continue
        for sym in tickers:
            s = _series(sym)
            if s:
                s["change_1w_pct"] = _pct(s["series"], 7)
                s["change_1m_pct"] = _pct(s["series"], 30)
                s["anomaly_pct"] = _anomaly(s["series"])
                stocks[e["id"]] = s
                ok += 1
                lib.save_json(lib.DATA_DIR / "finance" / "stocks.json", stocks)
                break
        time.sleep(SLEEP)
    lib.save_json(lib.DATA_DIR / "finance" / "stocks.json", stocks)
    return {"summary": f"{ok} séries boursières", "count": ok}
