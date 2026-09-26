"""MCX India bhavcopy connector: daily settlement of every futures and options contract.

MCX publishes one bhavcopy per trading day — open, high, low, close, the
previous settlement, volume in lots, traded quantity, turnover in ₹ lakh and
open interest — for every listed contract. This module fetches it and hands
back rows in one shape; the dlt resources in `sources/mcx.py` land them.

Two community libraries wrap MCX: `mcxlib` (RuchiTanmay, MIT) and `mcxpy`
(Tapanhaz, MIT). Both POST to `backpage.aspx/<Method>`, which MCX retired when
it moved the site to Sitefinity: in September 2026 every one of those routes
answers MCX's own 404 page. The data did not go away, it moved to
`GET /market-data/bhavcopy/<Method>`, and Akamai in front of it admits the
browser header profile mcxlib ships and refuses a bare User-Agent. So:

* **`contract` strategy (default)** — `GetCommoditywiseBhavCopy` per contract,
  through dlt's `RESTClient` with mcxlib's header profile. One request returns
  a contract's whole life, so a five-year backfill of gold is ~30 requests.
* **`datewise` strategy** — one bhavcopy per trading day, trying `mcxlib`,
  then `mcxpy`, then the direct route, and keeping the first that answers for
  the rest of the process. This is the libraries' own API; it is kept so the
  day they follow MCX's move, they work here again without a code change.

The contract list — every contract MCX has ever listed, with a traded-today
flag — is not an endpoint: the bhavcopy page embeds it as JSON in
`div#symbol-data`, and that is where it is read from.

Rows come back as the exchange states them: ₹ per the contract's quote basis,
lots, the exchange's unit string. Nothing is converted here (price-arithmetic
skill); `bhavcopy_row` only parses MCX's string dates and splits
`"2991.000 GRMS"` into a number and a unit.

The catalogue of which MCX codes make up which commodity is this project's
`mcx_products` seed, read here so Python and SQL cannot disagree about what
`gold` means.
"""

from __future__ import annotations

import csv
import json
import logging
import re
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

BASE_URL = "https://www.mcxindia.com"
BHAVCOPY_PAGE = "market-data/bhavcopy"
SEEDS = Path(__file__).resolve().parents[2] / "transform" / "seeds"

FUTURES = "FUTCOM"
OPTIONS = "OPTFUT"

#: mcxlib's browser profile (libutil.get_headers), minus the POST-only headers.
#: Used only if mcxlib is not importable — the library's copy is preferred so a
#: profile it refreshes for Akamai is picked up here too.
_FALLBACK_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/{BHAVCOPY_PAGE}",
    "Sec-GPC": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Chromium";v="118", "Brave";v="118", "Not=A?Brand";v="99"',
    "sec-ch-ua-platform": '"Windows"',
}

_SYMBOL_DATA = re.compile(r'<div id="symbol-data"[^>]*>(.*?)</div>', re.S)


class MCXUnavailable(RuntimeError):
    """MCX answered, but not with data: a moved route, an Akamai block, or IsSuccess=false."""


# --------------------------------------------------------------- catalogue --
@dataclass(frozen=True)
class Product:
    """One MCX contract code, e.g. GOLDM, and the commodity it trades."""

    contract_code: str
    mcx_commodity: str          # the job key: gold, crude_oil, ...
    contract_name: str
    is_flagship: bool


@cache
def products() -> tuple[Product, ...]:
    with (SEEDS / "mcx_products.csv").open(newline="", encoding="utf-8") as fh:
        return tuple(
            Product(contract_code=r["contract_code"], mcx_commodity=r["mcx_commodity"],
                    contract_name=r["contract_name"], is_flagship=r["is_flagship"] == "true")
            for r in csv.DictReader(fh))


def commodities() -> tuple[str, ...]:
    """Every MCX commodity the seed catalogues, in seed order. One job each."""
    return tuple(dict.fromkeys(p.mcx_commodity for p in products()))


def codes_for(commodity: str) -> tuple[str, ...]:
    """The MCX contract codes of one commodity. An unknown name is a typo, not a no-op."""
    codes = tuple(p.contract_code for p in products() if p.mcx_commodity == commodity)
    if not codes:
        raise KeyError(f"{commodity!r} is not an mcx_commodity in mcx_products.csv")
    return codes


# ---------------------------------------------------------------- contracts --
@dataclass(frozen=True)
class Contract:
    instrument: str             # FUTCOM | OPTFUT
    code: str                   # GOLD, GOLDM, ...
    expiry: date
    traded_today: bool

    @property
    def contract_id(self) -> str:
        """Exchange-scoped id. An options id names the expiry's chain, not one strike."""
        return f"MCX:{self.instrument}:{self.code}:{self.expiry.isoformat()}"


def parse_expiry(value: str) -> date:
    return datetime.strptime(value.strip(), "%d%b%Y").date()  # noqa: DTZ007 — a calendar date


def parse_symbol_data(page_html: str) -> list[Contract]:
    """Contracts listed in the bhavcopy page's embedded `div#symbol-data`."""
    m = _SYMBOL_DATA.search(page_html)
    if not m:
        raise MCXUnavailable("bhavcopy page has no #symbol-data — MCX changed the page")
    out: list[Contract] = []
    for item in json.loads(m.group(1)):
        try:
            out.append(Contract(instrument=item["InstrumentName"].strip(),
                                code=(item.get("SymbolValue") or item["Symbol"]).strip(),
                                expiry=parse_expiry(item["ExpiryDate"]),
                                traded_today=bool(item.get("TodaysTraded"))))
        except (KeyError, ValueError) as exc:  # one malformed listing is not a failed feed
            log.warning("mcx: skipping symbol-data item %s: %s", item, exc)
    return out


# ------------------------------------------------------------------- client --
def headers() -> dict[str, str]:
    try:
        from mcxlib.libutil import get_headers
        h = dict(get_headers(use_for="bhavcopy"))
    except Exception:  # noqa: BLE001 — optional dependency, profile has a fallback
        h = dict(_FALLBACK_HEADERS)
    # GETs: a Content-Length: 0 / JSON content type on a GET is what trips Akamai.
    for k in ("Content-Length", "Content-Type", "Cookie"):
        h.pop(k, None)
    return h


def _ddmmyyyy(d: date) -> str:
    return d.strftime("%d/%m/%Y")


class MCXClient:
    """The two bhavcopy routes and the contract list, through dlt's RESTClient.

    `pause_s` spaces requests out. MCX is a public site, not an API with a rate
    card; a backfill that hammers it is how a desk's IP ends up on Akamai's list.
    """

    def __init__(self, pause_s: float = 0.25, rest: Any = None) -> None:
        if rest is None:
            from dlt.sources.helpers.rest_client import RESTClient
            rest = RESTClient(base_url=BASE_URL, headers=headers())
        self.rest = rest
        self.pause_s = pause_s

    def _data(self, method: str, params: dict[str, str]) -> list[dict[str, Any]]:
        resp = self.rest.get(f"{BHAVCOPY_PAGE}/{method}", params=params, timeout=60)
        resp.raise_for_status()
        if "json" not in resp.headers.get("content-type", ""):
            raise MCXUnavailable(f"{method}: MCX answered {resp.headers.get('content-type')} "
                                 "instead of JSON — route moved or request blocked")
        body = resp.json()
        if isinstance(body, dict) and body.get("IsSuccess") is False:
            raise MCXUnavailable(f"{method}: {body.get('Message')}")
        time.sleep(self.pause_s)
        return (body.get("Data") if isinstance(body, dict) else body) or []

    def contracts(self) -> list[Contract]:
        resp = self.rest.get(BHAVCOPY_PAGE, headers={"Accept": "text/html"}, timeout=120)
        resp.raise_for_status()
        return parse_symbol_data(resp.text)

    def contract_history(self, contract: Contract, start: date, end: date) -> list[dict[str, Any]]:
        return self._data("GetCommoditywiseBhavCopy", {
            "InstrumentName": contract.instrument, "Symbol": contract.code,
            "Expiry": contract.expiry.strftime("%d%b%Y").upper(),
            "fromDate": _ddmmyyyy(start), "toDate": _ddmmyyyy(end)})

    def datewise(self, day: date, instrument: str) -> list[dict[str, Any]]:
        return self._data("GetDateWiseBhavCopy",
                          {"InstrumentName": instrument, "fromDate": _ddmmyyyy(day)})


# ------------------------------------------------- date-wise backend chain --
def _native_date(value: Any) -> str:
    """MCX's own `MM/DD/YYYY`, from whatever a library turned it into."""
    if isinstance(value, str):
        return value
    return value.strftime("%m/%d/%Y")


def _native_expiry(value: Any) -> str:
    if isinstance(value, str):
        return value
    return value.strftime("%d%b%Y").upper()


def from_mcxlib(rec: dict[str, Any]) -> dict[str, Any]:
    """mcxlib returns MCX's record less `__type`; nothing to undo."""
    return dict(rec)


#: mcxpy renames columns for display; these put MCX's names back.
_MCXPY_NAMES = {
    "Instrument Name": "InstrumentName", "Expiry Date": "ExpiryDate",
    "Option Type": "OptionType", "Strike Price": "StrikePrice",
    "Previous Close": "PreviousClose", "Volume(Lots)": "Volume",
    "Value(Lacs)": "Value", "Open Interest(Lots)": "OpenInterest",
}


def from_mcxpy(rec: dict[str, Any]) -> dict[str, Any]:
    out = {_MCXPY_NAMES.get(k, k): v for k, v in rec.items()}
    out["Date"] = _native_date(out["Date"])
    out["ExpiryDate"] = _native_expiry(out["ExpiryDate"])
    return out


def _via_mcxlib(day: date, instrument: str, _client: MCXClient) -> list[dict[str, Any]]:
    import mcxlib
    df = mcxlib.get_bhav_copy(trade_date=day.strftime("%Y%m%d"), instrument=instrument)
    return [from_mcxlib(r) for r in df.to_dict("records")]


def _via_mcxpy(day: date, instrument: str, _client: MCXClient) -> list[dict[str, Any]]:
    from mcxpy import mcx
    df = mcx.mcx_bhavcopy(day)
    if df is None:  # mcxpy prints its errors and returns None
        raise MCXUnavailable("mcxpy.mcx_bhavcopy returned nothing")
    rows = [from_mcxpy(r) for r in df.to_dict("records")]
    return [r for r in rows if str(r.get("InstrumentName", "")).strip() == instrument]


def _via_direct(day: date, instrument: str, client: MCXClient) -> list[dict[str, Any]]:
    return client.datewise(day, instrument)


BACKENDS: dict[str, Callable[[date, str, MCXClient], list[dict[str, Any]]]] = {
    "mcxlib": _via_mcxlib,
    "mcxpy": _via_mcxpy,
    "direct": _via_direct,
}


class DatewiseFeed:
    """One bhavcopy per day, from the first backend that answers.

    A backend that fails is dropped for the life of this object, not retried
    per day: a library pointed at a retired route fails identically every time,
    and paying that timeout on every day of a backfill is the cost of not
    remembering. The winner is recorded on every row as `extracted_via`.
    """

    def __init__(self, client: MCXClient, order: Iterable[str] = ("mcxlib", "mcxpy", "direct")) -> None:
        self.client = client
        self.order = [b for b in order if b in BACKENDS]
        self.chosen: str | None = None

    def bhavcopy(self, day: date, instrument: str) -> tuple[str, list[dict[str, Any]]]:
        candidates = [self.chosen] if self.chosen else list(self.order)
        errors: list[str] = []
        for name in candidates:
            try:
                rows = BACKENDS[name](day, instrument, self.client)
            except Exception as exc:  # noqa: BLE001 — try the next backend
                errors.append(f"{name}: {type(exc).__name__}: {str(exc)[:160]}")
                if name in self.order and name != self.chosen:
                    self.order.remove(name)
                continue
            if self.chosen != name:
                log.info("mcx: date-wise bhavcopy via %s", name)
            self.chosen = name
            return name, rows
        raise MCXUnavailable(f"every date-wise backend failed for {day}: " + "; ".join(errors))


# -------------------------------------------------------------------- rows --
def parse_quantity(value: Any) -> tuple[float | None, str | None]:
    """`"2991.000 GRMS "` → (2991000.0, "GRMS"). MCX states it in thousands."""
    parts = str(value or "").split()
    if len(parts) < 2:
        return None, None
    try:
        return round(float(parts[0]) * 1000, 3), parts[1]
    except ValueError:
        return None, parts[-1]


def bhavcopy_row(rec: dict[str, Any], mcx_commodity: str, extracted_via: str) -> dict[str, Any]:
    """One bhavcopy record, keyed. Futures and options share the shape; an option
    row adds strike and type to its key, and its `contract_id` is the chain's."""
    instrument = str(rec["InstrumentName"]).strip()
    code = str(rec["Symbol"]).strip()
    expiry = parse_expiry(rec["ExpiryDate"])
    day = datetime.strptime(str(rec["Date"]).strip(), "%m/%d/%Y").date()  # noqa: DTZ007 — a calendar date
    contract = Contract(instrument, code, expiry, traded_today=False)
    quantity, unit = parse_quantity(rec.get("VolumeInThousands"))
    row: dict[str, Any] = {
        "contract_id": contract.contract_id,
        "mcx_commodity": mcx_commodity,
        "contract_code": code,
        "instrument_type": instrument,
        "trade_date": day,
        "expiry_date": expiry,
        "open": rec.get("Open"),
        "high": rec.get("High"),
        "low": rec.get("Low"),
        "close": rec.get("Close"),
        "previous_close": rec.get("PreviousClose"),
        "volume_lots": rec.get("Volume"),
        "traded_quantity": quantity,
        "quantity_unit": unit,
        "turnover_lakhs": rec.get("Value"),
        "open_interest_lots": rec.get("OpenInterest"),
        "extracted_via": extracted_via,
    }
    if instrument.startswith("OPT"):
        option_type = str(rec.get("OptionType") or "").strip()
        strike = rec.get("StrikePrice")
        row["option_type"] = option_type
        row["strike_price"] = strike
        row["bhavcopy_id"] = f"{contract.contract_id}:{option_type}:{strike:g}:{day.isoformat()}"
    else:
        row["bhavcopy_id"] = f"{contract.contract_id}:{day.isoformat()}"
    return row


def contract_row(c: Contract, mcx_commodity: str) -> dict[str, Any]:
    return {"contract_id": c.contract_id, "mcx_commodity": mcx_commodity,
            "contract_code": c.code, "instrument_type": c.instrument,
            "expiry_date": c.expiry, "is_traded_today": c.traded_today}


# -------------------------------------------------------------- planning --
@dataclass(frozen=True)
class Window:
    contract: Contract
    start: date
    end: date


def plan(contracts: Iterable[Contract], cursors: dict[str, str], completed: Iterable[str],
         history_start: date, today: date, refetch_days: int) -> list[Window]:
    """Which contracts to (re)fetch, and over which days.

    A contract is fetched from `history_start` the first time, then from its
    last stored day minus `refetch_days` (a late settlement revision lands, a
    missed day heals). Once a fetch has reached its expiry after the expiry has
    passed, it is `completed` and never requested again — which is what keeps
    a daily run at a handful of requests however deep the history.
    """
    from datetime import timedelta

    done = set(completed)
    out: list[Window] = []
    for c in sorted(contracts, key=lambda c: (c.expiry, c.code)):
        if c.contract_id in done or c.expiry < history_start:
            continue
        last = cursors.get(c.contract_id)
        start = max(history_start, date.fromisoformat(last) - timedelta(days=refetch_days)) \
            if last else history_start
        end = min(today, c.expiry)
        if start > end:
            continue
        out.append(Window(c, start, end))
    return out


def fetch_windows(client: MCXClient, windows: Iterable[Window], mcx_commodity: str,
                  state: dict[str, Any], today: date) -> Iterator[dict[str, Any]]:
    """Rows for every window, advancing each contract's cursor after its rows.

    Per-contract isolation, as in the Yahoo connector: one contract MCX will not
    serve must not stop thirty others. Every contract failing is the feed being
    down, and raises, so a job never reports green over an empty load.
    """
    cursors: dict[str, str] = state.setdefault("cursors", {})
    completed: list[str] = state.setdefault("completed", [])
    ok, failed = 0, []
    windows = list(windows)
    for w in windows:
        try:
            records = client.contract_history(w.contract, w.start, w.end)
        except Exception as exc:  # noqa: BLE001 — isolation is the point
            log.warning("mcx: %s failed: %s", w.contract.contract_id, exc)
            failed.append(w.contract.contract_id)
            continue
        ok += 1
        days: list[date] = []
        for rec in records:
            row = bhavcopy_row(rec, mcx_commodity, extracted_via="direct:contract")
            days.append(row["trade_date"])
            yield row
        if days:
            cursors[w.contract.contract_id] = max(days).isoformat()
        if w.end == w.contract.expiry and w.contract.expiry < today:
            completed.append(w.contract.contract_id)
    if windows and not ok:
        raise MCXUnavailable(f"mcx {mcx_commodity}: every contract failed ({len(failed)})")
