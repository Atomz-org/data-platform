"""The conformed catalog: which commodities the family prices, and in which markets.

Both lists are the group's dbt seeds (`shared/transform/seeds`), read here so the
symbols a source fetches are exactly the rows `dim_commodities` will hold in every
sister. A benchmark cannot be fetched without being modelled, or modelled without
being fetched, and two sisters cannot mean different things by `gold`.

A sister narrows the catalog to what it tracks with `commodities(tracked=...)`
and names its market once with `market("IN")`. Adding a market is a row in
`markets.csv` plus a project; adding a commodity is a row in `commodities.csv`.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

SEEDS = Path(__file__).resolve().parents[3] / "transform" / "seeds"


@dataclass(frozen=True)
class Commodity:
    commodity_id: str
    commodity_name: str
    category: str               # precious | industrial | energy | agri
    segment: str
    #: Unit the international benchmark is quoted per; a code in `units_of_measure`.
    quote_unit: str
    exchange: str | None = None
    #: None means no free live feed; the commodity is priced from `indicative_prices`.
    yahoo_symbol: str | None = None
    #: gold-api.com spot symbol, precious metals only.
    spot_symbol: str | None = None

    @property
    def price_basis(self) -> str:
        return "futures" if self.yahoo_symbol else "indicative"


@dataclass(frozen=True)
class Market:
    market_code: str            # ISO 3166 alpha-2, which is also the tenant key
    market_name: str
    country_code: str
    currency_code: str          # the currency a landed price is expressed in
    home_exchange: str | None
    timezone: str
    project: str                # the sister project that owns this market


def _rows(name: str) -> list[dict[str, str]]:
    with (SEEDS / f"{name}.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@cache
def all_commodities() -> tuple[Commodity, ...]:
    return tuple(
        Commodity(
            commodity_id=r["commodity_id"],
            commodity_name=r["commodity_name"],
            category=r["category"],
            segment=r["segment"],
            quote_unit=r["quote_unit"],
            exchange=r["exchange"] or None,
            yahoo_symbol=r["yahoo_symbol"] or None,
            spot_symbol=r["spot_symbol"] or None,
        )
        for r in _rows("commodities")
    )


def commodities(tracked: Iterable[str] | None = None) -> tuple[Commodity, ...]:
    """The catalog, or the subset a sister tracks. An unknown id is a typo, not a
    silent no-op: it raises."""
    if tracked is None:
        return all_commodities()
    wanted = set(tracked)
    known = {c.commodity_id for c in all_commodities()}
    if unknown := sorted(wanted - known):
        raise KeyError(f"not in commodities.csv: {', '.join(unknown)}")
    return tuple(c for c in all_commodities() if c.commodity_id in wanted)


@cache
def markets() -> tuple[Market, ...]:
    return tuple(
        Market(
            market_code=r["market_code"],
            market_name=r["market_name"],
            country_code=r["country_code"],
            currency_code=r["currency_code"],
            home_exchange=r["home_exchange"] or None,
            timezone=r["timezone"],
            project=r["project"],
        )
        for r in _rows("markets")
    )


def market(code: str) -> Market:
    for m in markets():
        if m.market_code == code:
            return m
    raise KeyError(f"market {code!r} is not in markets.csv — add the row before the project")
