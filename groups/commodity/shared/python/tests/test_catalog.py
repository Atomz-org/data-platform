"""The conformed catalog Python reads is the one dbt seeds — and it is well-formed."""

import csv

import pytest
from commodity_shared import catalog


def test_every_row_of_the_seed_becomes_a_commodity():
    with (catalog.SEEDS / "commodities.csv").open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert [c.commodity_id for c in catalog.commodities()] == [r["commodity_id"] for r in rows]
    assert len(rows) == 33


def test_a_commodity_is_priced_by_a_feed_or_by_an_indicative_level():
    with (catalog.SEEDS / "indicative_prices.csv").open(newline="") as fh:
        indicative = {r["commodity_id"] for r in csv.DictReader(fh)}
    for c in catalog.commodities():
        assert c.price_basis == ("futures" if c.yahoo_symbol else "indicative")
        if c.price_basis == "indicative":
            assert c.commodity_id in indicative, f"{c.commodity_id} has no feed and no level"


def test_quote_units_are_conformed_units():
    with (catalog.SEEDS / "units_of_measure.csv").open(newline="") as fh:
        units = {r["unit_code"] for r in csv.DictReader(fh)}
    assert {c.quote_unit for c in catalog.commodities()} <= units


def test_tracking_a_subset_keeps_catalog_order_and_rejects_typos():
    subset = catalog.commodities(tracked=["silver", "gold"])
    assert [c.commodity_id for c in subset] == ["gold", "silver"]
    with pytest.raises(KeyError, match="platnum"):
        catalog.commodities(tracked=["platnum"])


def test_every_market_names_a_sister_project_and_a_currency():
    for m in catalog.markets():
        assert m.project.startswith("commodity-"), m
        assert len(m.currency_code) == 3 and m.currency_code.isupper(), m
        assert catalog.market(m.market_code) is m
    with pytest.raises(KeyError, match=r"markets\.csv"):
        catalog.market("ZZ")
