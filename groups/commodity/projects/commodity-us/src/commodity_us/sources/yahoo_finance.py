"""Yahoo Finance for commodity-us: daily futures candles and FX fixes.

The connector — client, parser, per-symbol cursors — is the group's
(`commodity_shared.yahoo_finance`); what is declared here is the US contract
with its own staging layer: which symbols, which columns, what they mean. The
cursors live in this resource's dlt state, so they travel with this warehouse.

    SOURCES__YAHOO_FINANCE__HISTORY_RANGE=10y uv run pf seed commodity commodity-us
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt
from commodity_shared import yahoo_finance as yf
from pf.ontology import annotate

from commodity_us.catalog import COMMODITIES, FX_CURRENCIES


def _history_range() -> str:
    return str(dlt.config.get("sources.yahoo_finance.history_range") or yf.DEFAULT_HISTORY_RANGE)


@dlt.resource(name="futures_prices", write_disposition="merge", primary_key="quote_id",
              columns=yf.FUTURES_COLUMNS)
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
    for commodity_id, meta, day, candle in yf.daily_series(
            symbols, dlt.current.resource_state(), _history_range()):
        yield yf.candle_row(commodity_id, meta, day, candle)


@dlt.resource(name="fx_rates", write_disposition="merge", primary_key="fx_rate_id",
              columns=yf.FX_COLUMNS)
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
    for ccy, _meta, day, candle in yf.daily_series(
            yf.fx_symbols(FX_CURRENCIES), dlt.current.resource_state(), _history_range()):
        yield yf.fx_row(ccy, day, candle)


@dlt.source(name="yahoo_finance")
def yahoo_finance_source():
    return [futures_prices(), fx_rates()]


ALL = [futures_prices, fx_rates]
