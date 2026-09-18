"""Yahoo Finance source for commodity-india: daily futures candles and FX fixes.

The same public chart endpoint MrChartist/commodity-price-tracker polls from the
browser. Server-side it needs no CORS proxy, but it does need a browser
User-Agent — without one Yahoo answers 429.

Prices land exactly as quoted: the exchange's currency (USX for cents) and the
contract's unit. Conversion is a dbt concern, done once, in the group macros.

Why `RESTClient` and a parser rather than a declarative `rest_api` config: a
chart payload is parallel arrays (`timestamp[]`, `quote[0].close[]`) that no
selector turns into rows, and every symbol needs its own request window. That
is the case dlt's REST guidance reserves for the client, so the client owns the
session and retries and Python owns the shape.

Incremental, per symbol, in dlt's own state: `dlt.current.resource_state()`
keeps the newest stored day for each symbol. A symbol with nothing stored
fetches `history_range`; otherwise the load refetches from its last day minus a
`REFETCH_DAYS` overlap, so late revisions land and a missed week self-heals.
`dlt.sources.incremental` was not used because it keeps one cursor per resource:
a metal added to the catalog would start at the others' cursor and get no
history. The state travels with the destination — dlt writes it to
`_dlt_pipeline_state` and drops the local copy when the dataset is gone — so
deleting data/*.duckdb rebackfills instead of loading ten days into nothing.
Changing `history_range` re-backfills every symbol.

    SOURCES__YAHOO_FINANCE__HISTORY_RANGE=10y uv run pf seed commodity commodity-india
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import dlt
from dlt.sources.helpers.rest_client import RESTClient
from pf.ontology import annotate

from commodity_india.catalog import COMMODITIES, FX_CURRENCIES

log = logging.getLogger(__name__)

BASE_URL = "https://query1.finance.yahoo.com"
CHART_PATH = "v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (commodity-india data pipeline)"}
DEFAULT_HISTORY_RANGE = "5y"
REFETCH_DAYS = 10


def _history_range() -> str:
    return str(dlt.config.get("sources.yahoo_finance.history_range") or DEFAULT_HISTORY_RANGE)


def _client() -> RESTClient:
    return RESTClient(base_url=BASE_URL, headers=HEADERS)


def fetch_chart(client: RESTClient, symbol: str, params: dict[str, Any]) -> dict[str, Any]:
    resp = client.get(CHART_PATH.format(symbol=symbol), params=params, timeout=20)
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


def _daily_series(symbols: dict[str, str], state: dict[str, Any]
                  ) -> Iterator[tuple[str, dict[str, Any], date, dict[str, Any]]]:
    """(key, meta, day, candle) for every symbol, tolerating individual failures.

    One delisted contract must not stop thirty others. Every symbol failing is a
    different thing — the feed is down — and raises, so a seed never builds
    marts over an empty load and calls it green. Each symbol's cursor advances
    only after its candles were yielded, so a failed symbol retries its whole
    window next run.
    """
    history_range = _history_range()
    backfilled = state.get("history_range")
    cursors: dict[str, str] = state.setdefault("cursors", {})
    client = _client()
    ok, failed = 0, []
    for key, symbol in symbols.items():
        last = date.fromisoformat(cursors[key]) if key in cursors else None
        params = window(last, backfilled, history_range)
        try:
            meta, candles = parse_candles(fetch_chart(client, symbol, params))
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


@dlt.resource(
    name="futures_prices",
    write_disposition="merge",
    primary_key="quote_id",
    columns={
        "trade_date": {"data_type": "date"},
        "open": {"data_type": "double"},
        "high": {"data_type": "double"},
        "low": {"data_type": "double"},
        "close": {"data_type": "double"},
        "volume": {"data_type": "bigint"},
    },
)
@annotate(
    source="yahoo_finance",
    concept="PriceObservation",
    grain="one commodity per trading day",
    description="Daily front-month futures candles from Yahoo Finance, in the "
                "exchange's quote currency and contract unit (unconverted)",
    roles={
        "quote_id": "natural_key",
        "open": "unit_price",
        "high": "unit_price",
        "low": "unit_price",
        "close": "unit_price",
        "currency": "currency_code",
        "trade_date": "event_time",
        "volume": "quantity",
    },
    rename={"open": "open_price", "high": "high_price", "low": "low_price",
            "close": "close_price", "currency": "currency_code", "trade_date": "traded_at"},
    links={"commodity_id": "Commodity"},
)
def futures_prices() -> Iterator[dict[str, Any]]:
    symbols = {c.commodity_id: c.yahoo_symbol for c in COMMODITIES if c.yahoo_symbol}
    for commodity_id, meta, day, candle in _daily_series(symbols, dlt.current.resource_state()):
        yield {
            "quote_id": f"{commodity_id}:{day.isoformat()}",
            "commodity_id": commodity_id,
            "symbol": meta.get("symbol"),
            "trade_date": day,
            "currency": meta.get("currency"),
            **candle,
        }


@dlt.resource(
    name="fx_rates",
    write_disposition="merge",
    primary_key="fx_rate_id",
    columns={"rate_date": {"data_type": "date"}, "rate": {"data_type": "double"}},
)
@annotate(
    source="yahoo_finance",
    concept="FxRate",
    grain="one currency pair per day",
    description="Daily USD fixes from Yahoo Finance; rate = quote currency per 1 USD",
    roles={
        "fx_rate_id": "natural_key",
        "base_currency": "currency_code",
        "quote_currency": "currency_code",
        "rate": "exchange_rate",
        "rate_date": "event_time",
    },
    rename={"base_currency": "base_currency_code",
            "quote_currency": "quote_currency_code", "rate_date": "rate_at"},
)
def fx_rates() -> Iterator[dict[str, Any]]:
    # Yahoo's `INR=X` is USD/INR: rupees per one dollar.
    symbols = {ccy: f"{ccy}=X" for ccy in FX_CURRENCIES}
    for ccy, _meta, day, candle in _daily_series(symbols, dlt.current.resource_state()):
        yield {
            "fx_rate_id": f"USD{ccy}:{day.isoformat()}",
            "base_currency": "USD",
            "quote_currency": ccy,
            "rate_date": day,
            "rate": candle["close"],
        }


@dlt.source(name="yahoo_finance")
def yahoo_finance_source():
    return [futures_prices(), fx_rates()]


ALL = [futures_prices, fx_rates]
