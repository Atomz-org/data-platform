# Commercial use

**Short version: you may use this commercially. The platform's own code is
Apache 2.0 and grants that already — no separate licence, no fee, no
permission needed. What needs attention is not this repository's licence but
three of the upstreams it pins.**

This file is not legal advice and does not add terms. [`LICENSE`](LICENSE) is
the licence; where the two ever disagree, `LICENSE` wins. This is a reading
guide for someone deciding whether they can ship something built on this.

---

## What the licence already grants

The platform is licensed under the Apache License 2.0. For a commercial
adopter that means:

- **Commercial use, modification and redistribution are permitted**, royalty-free.
- **An express patent grant** (§3) from contributors, covering their
  contributions — with the usual termination clause if you bring a patent suit.
- **No copyleft.** You may combine it with proprietary code and are not
  required to publish your changes.

Three obligations come with it, all in §4: keep the licence and copyright
notices, state significant changes you made, and carry [`NOTICE`](NOTICE) in
any redistribution.

Two things Apache 2.0 does **not** give you:

- **No warranty and no liability** (§7, §8). The software is provided "as is".
- **No trademark licence** (§6). The name, and any mark or logo associated with
  it, are not covered by the code licence.

---

## The part that actually needs care: vendored upstreams

`vendor/` pins upstream projects as **git submodules — pointers, not copies**.
Cloning without `--recurse-submodules` fetches none of that code, and each
upstream keeps its own licence, which governs its own code. The authoritative
per-path record of what was borrowed lives in
`platform/src/pf/vendor/registry.yaml`:

```bash
uv run pf vendor licences      # every upstream's licence and its review note
uv run pf vendor list -v       # what was adopted from each
uv run pf vendor why <file>    # reverse lookup for one file
```

Most upstreams are MIT or Apache-2.0 and raise nothing. **Three are different
in kind, and a commercial adopter should read them before shipping.** All
three notes below are quoted from the registry, which already records the
reasoning:

### `dlthub-ai-workbench` — dltHub License (proprietary)

Scope-of-use is limited to dltHub Services, and running dlt Core on a
third-party orchestrator reads as a "NOT permitted" example. The registry
records the mitigation: the dlt toolkits here are *independent rewrites against
dlt Core's public API*, and the submodule is pinned for reference and drift
detection rather than redistribution. The registry's own instruction stands —
**confirm with counsel before shipping this platform externally.**

### `asqav-compliance` — Elastic License 2.0

Permits use and modification, but **forbids providing the software to third
parties as a hosted or managed service.** It runs here as a GitHub Action
inside this repo's own CI on this repo's own code, which is ordinary internal
use. Two limits the registry holds explicitly: this platform **must not expose
the scanner as a compliance-scanning feature to its own tenants** — that is
precisely the managed service the licence excludes — and the action's code
stays vendored unmodified. This is a stricter licence than anything else in the
registry.

### `okf-weaver` — no licence declared

The repository carries no `LICENSE` file, so **by default all rights are
reserved by its author.** It is authored and owned by this platform's own
maintainer, which is why it is pinned at all. Confirm the terms before this
platform, or a bundle produced through it, is shipped to anyone else.

### Attribution-only, but not obligation-free

`public-sector-ai-playbook` and `ai-governance-framework` are CC BY 4.0 —
commercial use included, on condition of attribution. `wrenai` is Apache-2.0
for `core/**` and CC-BY-4.0 for `docs/**`. `evidence-bi` states no licence
upstream and is treated as reference only. The required credits are already
discharged in [`NOTICE`](NOTICE) and
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md); keep them intact when you
redistribute.

`pf vendor licences` marks these six as **licence review outstanding**. That
marker is a live signal, not decoration — read it before a release rather than
after.

---

## What is not offered

There is no commercial support contract, no warranty, no indemnity and no SLA.
Nothing here is certified against any standard. The governance machinery —
the provenance chain, `pf air coverage`, the gate — is engineering that makes
compliance work auditable; **it is not a compliance certification and must not
be represented as one.**

The security reporting process is in [`SECURITY.md`](SECURITY.md).

---

## If you want something beyond this

The Apache licence covers use. It does not cover support, a warranty, an
indemnity, or a trademark licence. If you need one of those, or want to
sponsor work, contact the maintainer:

**Suresh Swaminathan** — sureshswaminathan.96@gmail.com

Copyright 2026 Suresh Swaminathan. Licensed under the Apache License, Version 2.0.
