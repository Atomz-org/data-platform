"""Yahoo Finance chart connector: daily futures candles and FX fixes.

The same public chart endpoint MrChartist/commodity-price-tracker polls from the
browser. Server-side it needs no CORS proxy, but it does need a browser
User-Agent — without one Yahoo answers 429.

Why `RESTClient` and a parser rather than a declarative `rest_api` config: a
chart payload is parallel arrays (`timestamp[]`, `quote[0].close[]`) that no
selector turns into rows, and every symbol needs its own request window. That
is the case dlt's REST guidance reserves for the client, so the client owns the
session and retries and Python owns the shape.

Incremental, per symbol, in the caller's dlt resource state: `daily_series`
keeps the newest stored day for each symbol under `state["cursors"]`. A symbol
with nothing stored fetches `history_range`; otherwise the load refetches from
its last day minus a `REFETCH_DAYS` overlap, so late revisions land and a
missed week self-heals. `dlt.sources.incremental` was not used because it keeps
one cursor per resource: a metal added to the catalog would start at the
others' cursor and get no history. Changing `history_range` re-backfills every
symbol.

Prices come back exactly as quoted — the exchange's currency (USX for cents)
and the contract's unit. Conversion is dbt's job, once, in the group macros.
This module holds no `@dlt.resource` and no annotation: each sister declares
its own resources over `daily_series`, because the annotation is the sister's
contract with its own staging layer.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from dlt.sources.helpers.rest_client import RESTClient

log = logging.getLogger(__name__)

BASE_URL = "https://query1.finance.yahoo.com"
CHART_PATH = "v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (commodity data pipeline)"}
DEFAULT_HISTORY_RANGE = "5y"
REFETCH_DAYS = 10


def client() -> RESTClient:
    return RESTClient(base_url=BASE_URL, headers=HEADERS)


def fetch_chart(rest: RESTClient, symbol: str, params: dict[str, Any]) -> dict[str, Any]:
    resp = rest.get(CHART_PATH.format(symbol=symbol), params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def parse_candles(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[date, dict[str, Any]]]:
    """(meta, {trading day: candle}) from a chart payload.

    Days are taken in the exchange's own timezone: a CME session stamped
    04:00 UTC is that calendar day in Chicago/New York, not the day before.
    Candles with no close are dropped. When Yahoo appends a live intraday point
    for a day it already has a candle for, the later point wins.
    """
    results = (payload.get("chart") or {}).get("result") or []
    if not results:
        return {}, {}
    result = results[0]
    meta = result.get("meta") or {}
    try:
        tz = ZoneInfo(meta.get("exchangeTimezoneName") or "UTC")
    except (KeyError, ValueError):
        tz = UTC
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]

    def at(field: str, i: int) -> Any:
        values = quote.get(field) or []
        return values[i] if i < len(values) else None

    candles: dict[date, dict[str, Any]] = {}
    for i, ts in enumerate(result.get("timestamp") or []):
        close = at("close", i)
        if close is None:
            continue
        day = datetime.fromtimestamp(ts, tz).date()
        candles[day] = {"open": at("open", i), "high": at("high", i),
                        "low": at("low", i), "close": close, "volume": at("volume", i)}
    return meta, candles


def _epoch(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp())


def window(last: date | None, backfilled_range: str | None, history_range: str) -> dict[str, Any]:
    """Chart query parameters: a full backfill, or a short overlapping refetch."""
    if last and backfilled_range == history_range:
        return {"interval": "1d", "period1": _epoch(last - timedelta(days=REFETCH_DAYS)),
                "period2": int(time.time()) + 86400}
    return {"interval": "1d", "range": history_range}


def daily_series(symbols: dict[str, str], state: dict[str, Any], history_range: str,
                 ) -> Iterator[tuple[str, dict[str, Any], date, dict[str, Any]]]:
    """(key, meta, day, candle) for every symbol, tolerating individual failures.

    One delisted contract must not stop thirty others. Every symbol failing is a
    different thing — the feed is down — and raises, so a seed never builds
    marts over an empty load and calls it green. Each symbol's cursor advances
    only after its candles were yielded, so a failed symbol retries its whole
    window next run.
    """
    backfilled = state.get("history_range")
    cursors: dict[str, str] = state.setdefault("cursors", {})
    rest = client()
    ok, failed = 0, []
    for key, symbol in symbols.items():
        last = date.fromisoformat(cursors[key]) if key in cursors else None
        params = window(last, backfilled, history_range)
        try:
            meta, candles = parse_candles(fetch_chart(rest, symbol, params))
        except Exception as exc:  # noqa: BLE001 — per-symbol isolation is the point
            log.warning("yahoo_finance: %s (%s) failed: %s", key, symbol, exc)
            failed.append(symbol)
            continue
        ok += 1
        for day, candle in sorted(candles.items()):
            yield key, meta, day, candle
        if candles:
            cursors[key] = max(candles).isoformat()
    if symbols and not ok:
        raise RuntimeError(f"yahoo_finance: every symbol failed ({', '.join(failed)})")
    state["history_range"] = history_range


def candle_row(commodity_id: str, meta: dict[str, Any], day: date, candle: dict[str, Any]) -> dict[str, Any]:
    """One futures row, keyed the way every sister's `futures_prices` is."""
    return {
        "quote_id": f"{commodity_id}:{day.isoformat()}",
        "commodity_id": commodity_id,
        "symbol": meta.get("symbol"),
        "trade_date": day,
        "currency": meta.get("currency"),
        **candle,
    }


def fx_symbols(currencies: Iterable[str]) -> dict[str, str]:
    """Yahoo's `INR=X` is USD/INR: units of the currency per one dollar."""
    return {ccy: f"{ccy}=X" for ccy in currencies}


def fx_row(currency: str, day: date, candle: dict[str, Any]) -> dict[str, Any]:
    return {
        "fx_rate_id": f"USD{currency}:{day.isoformat()}",
        "base_currency": "USD",
        "quote_currency": currency,
        "rate_date": day,
        "rate": candle["close"],
    }


# Column hints every sister applies to the rows above, so the raw types are
# frozen identically in each warehouse and the roll-up unions them without casts.
FUTURES_COLUMNS = {
    "trade_date": {"data_type": "date"},
    "open": {"data_type": "double"},
    "high": {"data_type": "double"},
    "low": {"data_type": "double"},
    "close": {"data_type": "double"},
    "volume": {"data_type": "bigint"},
}
FX_COLUMNS = {"rate_date": {"data_type": "date"}, "rate": {"data_type": "double"}}
