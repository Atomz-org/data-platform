---
type: Vendor Upstream
title: Floci
description: a local AWS, so the artefact store can be exercised without an account
resource: https://github.com/floci-io/floci
tags:
- vendor
- engine
- MIT
status: stable
sources:
- id: floci:docker-compose.yml
  resource: https://github.com/floci-io/floci
  title: docker-compose.yml
- id: floci:README.md
  resource: https://github.com/floci-io/floci
  title: README.md
---

# Floci

`pf.artifacts` is the one subsystem with no local mode. Every other engine this platform runs degrades to a file on disk — dbt to DuckDB, recce to a local state file, the catalogue to a JSON export — but the bucket is a bucket, so `pf artifacts push`, `pull`, `ls` and the recce baseline path through CI could only ever be tested against real object storage with real credentials and real spend. They therefore mostly were not.
Floci is an S3 on localhost:4566 that needs no account and no auth token, which turns that whole path into something a laptop and a CI runner can exercise for free. It replaces LocalStack Community, whose sunset in March 2026 is why this is a new pin rather than an old one.
It is an emulator and it is scoped like one: it proves the AWS *shape* of the artefact store, and nothing about AWS itself. A green floci run is not evidence that a real bucket is reachable — `pf artifacts status` against the real endpoint is the only thing that says that.

## Adopted

- **docker-compose.yml** (shape) -> platform/deploy/compose.floci.yaml
  The service definition: image, the single published port, and `FLOCI_HOSTNAME`, which is what makes container-to-container calls resolve when a caller reaches the emulator by service name rather than through localhost. Ours adds a healthcheck — a JVM reports "started" well before it serves — and binds the port to loopback, because an object store that accepts any credential pair must not be reachable from the network. It is a separate file rather than a service in `compose.yaml`, so bringing up the control plane never starts an emulator nobody asked for.
- **README.md** (shape) -> platform/src/pf/artifacts.py, docs/ARTIFACTS.md
  The configuration contract we encode: port 4566, `FLOCI_DEFAULT_REGION` defaulting to us-east-1, and the fact that any non-empty credential pair signs. If upstream renames a `FLOCI_*` variable or moves the default port, our compose file and the documented env block are what stop working — which is precisely what `pf vendor drift` should surface on this pin.

## Declined

- **the other sixty-odd emulated services**
  We use S3 and only S3. Floci also emulates Lambda, ECS, RDS, Redshift, Glue and more, and each one is a standing invitation to move a piece of this platform onto an AWS service because it happens to be emulable locally. The platform's portability comes from *not* depending on those — the warehouse is a dbt target, the orchestrator is Dagster, the catalogue is OpenMetadata — and adopting them here would trade that for convenience in a test harness.
- **backing the control plane's Postgres with floci's RDS emulation**
  `platform/deploy/compose.yaml` runs a real Postgres holding real catalogued tables and Dagster's run history. An emulator is the wrong fidelity for a stateful store we upgrade with a dump and restore, and the failure mode — a subtly different Postgres under OpenMetadata's migrations — is one nobody would attribute to the emulator.
- **floci's Redshift emulation as a test for the `redshift` target**
  `pf.runtime.targets` declares Redshift for dbt, and what needs proving about it is dialect behaviour: identifier folding, `merge` support, type coercion. An emulator that answers the wire protocol does not answer those, and a green build against it would be exactly the false assurance `pf align validate --stage dialect` exists to refuse.
- **running it anywhere but a laptop or a CI job**
  It has no durability guarantees worth the name — the default storage mode is in-memory — and it is not a place to put an artefact anyone will need later. `PF_ARTIFACTS_ENDPOINT` pointing at 4566 outside development is a misconfiguration, not a deployment.
