"""Stripe source for acme-us.

Synthetic generator so the project runs offline. Swap `_charges()` etc. for
`dlt.sources.rest_api` against the live API — the annotations do not change,
which is the point: meaning is declared once and survives the implementation.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

import dlt

from pf.ontology import annotate

ENTITY = "US"
SEED = 20260812
PLANS = ["starter", "growth", "enterprise"]
SEGMENTS = ["smb", "mid_market", "enterprise"]
STATUSES = ["succeeded", "succeeded", "succeeded", "refunded", "failed"]


def _rng() -> random.Random:
    return random.Random(SEED)


@dlt.resource(name="customers", write_disposition="merge", primary_key="id")
@annotate(
    source="stripe",
    concept="Customer",
    grain="one customer account",
    description="Stripe customers for the US entity",
    roles={
        "id": "natural_key",
        "email": "pii_email",
        "name": "pii_name",
        "country": "geo_country",
        "segment": "status_enum",
        "created": "event_time",
    },
    rename={"id": "customer_id", "email": "customer_email", "name": "customer_name",
            "country": "country_code", "segment": "customer_segment", "created": "created_at"},
    links={"organization_id": "Organization"},
)
def customers() -> Iterator[dict[str, Any]]:
    r = _rng()
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(1, 121):
        yield {
            "id": f"cus_us_{i:04d}",
            "organization_id": f"org_us_{r.randint(1, 40):03d}",
            "email": f"  User{i}@Example.COM " if i % 3 == 0 else f"user{i}@example.com",
            "name": f"Customer  {i} " if i % 4 == 0 else f"Customer {i}",
            "country": " us " if i % 5 == 0 else "US",
            "segment": r.choice(SEGMENTS),
            "created": (base + timedelta(days=r.randint(0, 400))).isoformat(),
        }


@dlt.resource(name="subscriptions", write_disposition="merge", primary_key="id")
@annotate(
    source="stripe",
    concept="Subscription",
    grain="one subscription",
    description="Active and churned subscriptions",
    roles={
        "id": "natural_key",
        "plan": "status_enum",
        "status": "status_enum",
        "mrr_amount": "money_amount",
        "currency": "currency_code",
        "started_at": "event_time",
        "canceled_at": "valid_to",
    },
    rename={"id": "subscription_id", "plan": "plan_tier",
            "status": "subscription_status", "currency": "currency_code"},
    links={"customer_id": "Customer"},
)
def subscriptions() -> Iterator[dict[str, Any]]:
    r = _rng()
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(1, 141):
        started = base + timedelta(days=r.randint(0, 380))
        churned = r.random() < 0.18
        yield {
            "id": f"sub_us_{i:04d}",
            "customer_id": f"cus_us_{r.randint(1, 120):04d}",
            "plan": r.choice(PLANS),
            "status": "canceled" if churned else "active",
            "mrr_amount": round(r.choice([49, 149, 499, 1499]) * r.uniform(0.9, 1.1), 2),
            "currency": "USD",
            "started_at": started.isoformat(),
            "canceled_at": (started + timedelta(days=r.randint(30, 300))).isoformat()
            if churned else None,
        }


@dlt.resource(name="charges", write_disposition="merge", primary_key="id")
@annotate(
    source="stripe",
    concept="Payment",
    grain="one payment attempt",
    description="Stripe charge events — the revenue source of record",
    roles={
        "id": "natural_key",
        "amount": "money_amount",
        "currency": "currency_code",
        "status": "status_enum",
        "created": "event_time",
        "receipt_email": "pii_email",
    },
    rename={"id": "payment_id", "currency": "currency_code",
            "status": "payment_status", "created": "paid_at"},
    links={"customer_id": "Customer", "subscription_id": "Subscription"},
)
def charges() -> Iterator[dict[str, Any]]:
    r = _rng()
    base = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for i in range(1, 1801):
        created = base + timedelta(days=r.randint(0, 420), hours=r.randint(0, 23))
        yield {
            "id": f"ch_us_{i:05d}",
            "customer_id": f"cus_us_{r.randint(1, 120):04d}",
            "subscription_id": f"sub_us_{r.randint(1, 140):04d}",
            "amount": round(r.choice([49, 149, 499, 1499]) * r.uniform(0.85, 1.15), 2),
            "currency": "usd" if i % 7 == 0 else "USD",
            "status": " " + r.choice(STATUSES).upper() if i % 11 == 0 else r.choice(STATUSES),
            "created": created.isoformat(),
            "receipt_email": f"USER{r.randint(1, 120)}@example.com",
        }


@dlt.source(name="stripe")
def stripe_source():
    return [customers(), subscriptions(), charges()]


ALL = [customers, subscriptions, charges]
