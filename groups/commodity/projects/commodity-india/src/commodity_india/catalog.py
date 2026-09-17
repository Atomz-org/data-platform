"""The commodities commodity-india tracks, and where each one is priced.

One list drives both what the sources fetch and what `dim_commodities` contains,
so a benchmark cannot be fetched without being modelled or modelled without
being fetched. Adapted from the COMMODITIES table in
MrChartist/commodity-price-tracker (app.js).

`quote_unit` is the unit the benchmark is quoted per; codes are the group's
conformed units (`units_of_measure`). Market units, duty and purity are
India-specific and live in this project's dbt seeds, not here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Commodity:
    commodity_id: str
    commodity_name: str
    category: str               # precious | industrial | energy | agri
    segment: str
    quote_unit: str
    exchange: str | None = None
    #: None means no free live feed exists; the commodity is priced from the
    #: `indicative_prices` seed instead.
    yahoo_symbol: str | None = None
    #: gold-api.com spot symbol, for the precious metals only.
    spot_symbol: str | None = None

    @property
    def price_basis(self) -> str:
        return "futures" if self.yahoo_symbol else "indicative"


COMMODITIES: tuple[Commodity, ...] = (
    # -- precious metals ----------------------------------------------------
    Commodity("gold", "Gold", "precious", "precious_metal", "troy_oz", "COMEX", "GC=F", "XAU"),
    Commodity("silver", "Silver", "precious", "precious_metal", "troy_oz", "COMEX", "SI=F", "XAG"),
    Commodity("platinum", "Platinum", "precious", "precious_metal", "troy_oz", "NYMEX", "PL=F", "XPT"),
    Commodity("palladium", "Palladium", "precious", "precious_metal", "troy_oz", "NYMEX", "PA=F", "XPD"),
    # -- energy -------------------------------------------------------------
    Commodity("crude_oil_wti", "Crude Oil (WTI)", "energy", "crude_oil", "barrel", "NYMEX", "CL=F"),
    Commodity("crude_oil_brent", "Brent Crude", "energy", "crude_oil", "barrel", "ICE", "BZ=F"),
    Commodity("natural_gas", "Natural Gas", "energy", "natural_gas", "mmbtu", "NYMEX", "NG=F"),
    # -- industrial and battery metals --------------------------------------
    Commodity("copper", "Copper", "industrial", "base_metal", "lb", "COMEX", "HG=F"),
    Commodity("aluminium", "Aluminium", "industrial", "base_metal", "metric_ton", "COMEX", "ALI=F"),
    Commodity("zinc", "Zinc", "industrial", "base_metal", "metric_ton", "LME"),
    Commodity("nickel", "Nickel", "industrial", "base_metal", "metric_ton", "LME"),
    Commodity("lead", "Lead", "industrial", "base_metal", "metric_ton", "LME"),
    Commodity("tin", "Tin", "industrial", "base_metal", "metric_ton", "LME"),
    # HRC=F is US Midwest hot-rolled coil, quoted per US short ton.
    Commodity("steel_hrc", "Steel (HRC)", "industrial", "ferrous", "short_ton", "COMEX", "HRC=F"),
    Commodity("iron_ore", "Iron Ore (62% Fe)", "industrial", "ferrous", "dry_metric_ton", "SGX"),
    Commodity("lithium_carbonate", "Lithium (Carbonate)", "industrial", "battery_metal", "metric_ton"),
    Commodity("cobalt", "Cobalt", "industrial", "battery_metal", "metric_ton", "LME"),
    # -- agriculture --------------------------------------------------------
    Commodity("wheat", "Wheat", "agri", "grain", "bushel_60lb", "CBOT", "ZW=F"),
    Commodity("corn", "Corn (Maize)", "agri", "grain", "bushel_56lb", "CBOT", "ZC=F"),
    Commodity("rice", "Rice (Rough)", "agri", "grain", "cwt", "CBOT", "ZR=F"),
    Commodity("soybean", "Soybean", "agri", "oilseed", "bushel_60lb", "CBOT", "ZS=F"),
    Commodity("soybean_meal", "Soybean Meal", "agri", "oilseed", "short_ton", "CBOT", "ZM=F"),
    Commodity("soybean_oil", "Soybean Oil", "agri", "vegetable_oil", "lb", "CBOT", "ZL=F"),
    Commodity("canola_oil", "Canola Oil", "agri", "vegetable_oil", "metric_ton"),
    Commodity("palm_oil", "Palm Oil (CPO)", "agri", "vegetable_oil", "metric_ton", "BMD"),
    Commodity("sugar", "Sugar", "agri", "soft", "lb", "ICE", "SB=F"),
    Commodity("cotton", "Cotton", "agri", "soft", "lb", "ICE", "CT=F"),
    Commodity("coffee", "Coffee", "agri", "soft", "lb", "ICE", "KC=F"),
    Commodity("cocoa", "Cocoa", "agri", "soft", "metric_ton", "ICE", "CC=F"),
    Commodity("orange_juice", "Orange Juice", "agri", "soft", "lb", "ICE", "OJ=F"),
    Commodity("lumber", "Lumber", "agri", "forest_product", "mbf", "CME", "LBR=F"),
    Commodity("lean_hogs", "Lean Hogs", "agri", "livestock", "lb", "CME", "HE=F"),
    Commodity("live_cattle", "Live Cattle", "agri", "livestock", "lb", "CME", "LE=F"),
)

#: Currencies fixed against USD every day. INR drives the landed price; the rest
#: are the reference rates the tracker shows beside it.
FX_CURRENCIES: tuple[str, ...] = ("INR", "EUR", "GBP", "JPY", "CNY", "AED", "CAD")
