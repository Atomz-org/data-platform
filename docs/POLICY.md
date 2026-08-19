# The policy layer

Vocabulary is shared. Obligations are not.

Two sisters must mean the same thing by `Payment` or a roll-up adds two numbers
that merely share a name — so classes, roles and relations live at the platform
and group levels, and `acme-rollup` depends on exactly that. But what must
*hold* is genuinely local: acme-eu answers to GDPR and acme-us does not, and a
single platform-wide `policy.yaml` cannot say so.

So policy layers where the rest of the ontology deliberately does not.

```
platform/src/pf/ontology/policy.yaml   the floor, applying everywhere
groups/<group>/ontology/policy.yaml    the family's own obligations
<project>/governance/policy.yaml       this entity's own obligations
```

This mirrors the shape `extension.yaml` already layers over `concepts.yaml`.
The difference is what may be layered: `extension.yaml` adds vocabulary, and a
policy overlay adds *rules*, so it carries a safety property the vocabulary
layer does not need.

---

## The one rule: overlays may only tighten

A layer can do three things, and only three:

| Move | Example |
|---|---|
| **add** | declare a policy the platform does not have |
| **tighten** | raise an inherited policy's severity, `info` → `warning` → `error` |
| **enforce** | name another artifact or evidence kind for an inherited policy |

It **cannot** lower a severity, and there is no syntax for deleting an
inherited policy. A relaxation raises `PolicyRelaxation` at **load** time:

```
PolicyRelaxation: project:acme/acme-us: policy 'pii-not-in-consumption' lowers
severity 'error' -> 'warning'. A layer may tighten a policy, never relax one;
drop the override or raise it.
```

Load time, not check time, is the point. A relaxed policy that only failed when
something tripped over it would be discovered by the incident it was written to
prevent.

This is the same stance `pf.tools.spec` takes on gate sections, for the same
reason: **a governance layer that each project can weaken is not a governance
layer.**

---

## Writing an overlay

### Tighten an inherited policy

`mart-declares-grain` ships from the platform as a `warning`. To make it fatal
in one project:

```yaml
# groups/acme/projects/acme-eu/governance/policy.yaml
policies:
  - id: mart-declares-grain
    severity: error
```

Everything else about the policy is inherited — its `intent`, `constraint`,
`applies_to`, `params`, `enforced_by` and `evidence` all come from the platform
definition. You are overriding one field.

### Add a policy of your own

```yaml
policies:
  - id: gdpr-erasure-path
    intent: >
      A subject access or erasure request must have a declared path to every
      copy of the subject's data — marts and review artefacts included, not only
      the raw tables it landed in.
    applies_to: {role_glob: "pii_*"}
    constraint: erasure_declared
    severity: error
```

Note what this example does **not** do: it names no `enforced_by`. There is no
erasure checker yet, so claiming one would make `pf semantic policy` report the
rule as enforced when nothing enforces it. Left blank, it surfaces honestly:

```
1 unenforced policy(ies): gdpr-erasure-path
```

That is the finding, and it is meant to be seen. From `pf.projections.otop`:

> An unenforced policy that reports `pass` is worse than no policy at all,
> because it ends the conversation.

### Add enforcement without claiming the policy

```yaml
policies:
  - id: pii-not-in-consumption
    enforced_by: [pf.local.checks:pii_sweep]
    evidence: [pf loop run pii-audit]
```

`enforced_by` and `evidence` are unioned with what the base declared, in order,
without duplicates. Because this changes no severity, the policy's `scope` stays
`platform` — otherwise every project would appear to own every policy it merely
helps enforce.

---

## An omitted `severity:` means *inherit*

This is the subtlest rule in the layer, and it exists because of a real bug.

In a **base** document an omitted severity defaults to `error` — the strict end,
because a rule whose severity was forgotten should shout rather than whisper.

In an **overlay** it must mean *inherit*. Otherwise the example directly above —
an entry that only adds an `enforced_by` line — would silently escalate
`pii-not-in-consumption`'s severity to `error`. That is a tightening nobody
wrote, and nobody would spot it in the diff.

```yaml
# Inherits warning from the platform. Does NOT become an error.
- id: mart-declares-grain
  enforced_by: [pf.local:extra-check]
```

---

## `applies_to` and `params` are not overridable

An overlay that redefines either on an inherited policy is rejected:

```
PolicyRelaxation: project:acme/acme-us: policy 'pii-not-in-consumption'
redefines 'applies_to'. Retargeting an inherited policy can silently narrow it;
declare a new policy with its own id instead.
```

Narrowing `applies_to` reads like a refinement and is really a partial delete.
`pii-not-in-consumption` retargeted from `role_glob: "pii_*"` to
`role_glob: "pii_email"` stops covering `pii_name`, `pii_phone` and everything
else — with nothing in the diff shaped like a removal.

A project that genuinely needs different targeting declares a **new policy with
a new id**, where the addition is visible as an addition.

---

## Reading the resolved result

`pf semantic policy` takes an optional scope. With no argument it prints the
platform floor; naming a group, or a group and a project, resolves the layers
over it.

```console
$ pf semantic policy acme acme-eu
scope: acme/acme-eu
┏━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ policy      ┃ severity ┃ set by     ┃ constraint  ┃ enforced   ┃ evidence    ┃
┃             ┃          ┃            ┃             ┃ by         ┃             ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ mart-decla… │ error    │ project:a… │ meta_field… │ pf.kg.bui… │ kg/context… │
│ gdpr-erasu… │ error    │ project:a… │ erasure_de… │ NOTHING    │ —           │
└─────────────┴──────────┴────────────┴─────────────┴────────────┴─────────────┘
1 unenforced policy(ies): gdpr-erasure-path

$ pf semantic policy acme acme-us
scope: acme/acme-us
│ mart-decla… │ warning  │ platform   │ meta_field… │ pf.kg.bui… │ kg/context… │
every policy names an enforcing artifact
```

The **`set by`** column is the whole reason `Policy.scope` exists. "Why is this
an error here and a warning next door" is answerable without diffing three
files. Severities set by a local layer print highlighted; anything still at the
platform default prints plain.

---

## Where the resolved policy is used

| Consumer | What it resolves |
|---|---|
| `pf check` / `pf bootstrap` | `validate._ontology_for()` derives group **and** project from the path and resolves both layers |
| `pf semantic policy` | prints the chain at the requested scope |
| `pf.projections.otop` | `build_manifest()` exports at the scope it was asked for |

The otop projection previously assumed policies were *"platform-wide, so
identical in every project"*. That is no longer true, and exporting a project's
governance against the platform floor would understate exactly the obligations
that project was given. It now resolves per scope:

```console
$ python -c "..."
eu constraints: 11 | us constraints: 10
eu-only     : ['gdpr-erasure-path']
```

---

## How it reaches a project

The overlay is a **capability**, not a hardcoded scaffold step. One entry in
`pf.capabilities.CAPABILITIES`; adding or removing it touches no scaffolder, no
CLI and no gate.

```python
"governance": Capability(
    name="governance",
    description="Project-scoped policy overlay, layered over the platform "
                "and group floors. Tightening only.",
    files={"governance/policy.yaml": GOVERNANCE_POLICY},
    preserve=("governance/policy.yaml",),
    gate={"impact_required": ["**/governance/policy.yaml"]},
    default_enabled=True,
),
```

### New project

```console
$ pf new-project acme acme-de
  + capability governance (1 file(s))
```

`default_enabled=True`, so it arrives without being asked for. An opt-in
capability reaches only the projects whose author remembered the flag, which is
how one project ends up governed and seven do not. Opt out with
`pf new-project --without governance`.

### Existing project

```console
$ pf capability-add governance acme acme-us
  + governance (1 file(s))
```

`pf bootstrap` also backfills it into every project that lacks it, using the
existing all-or-nothing rule: a capability is applied only when **every** file
it writes is absent, never when some already exist.

### The seeded file is inert

The stub ships with `policies: []` and every example commented out. Scaffolding
a project, or backfilling this into eight existing ones, **changes no verdict
anywhere**. A capability that silently tightened the gate on adoption would be
discovered as a broken build in a project nobody had touched.

### `preserve` — seeded, not generated

`Capability.preserve` names files written *when absent* and left alone *when
present*. `apply()` otherwise rewrites every target wholesale, which is correct
for a generated artefact and destructive for one a human is expected to edit.

This matters because `pf capability-add` deliberately bypasses the backfill's
all-or-nothing guard. Without `preserve`, re-adding the capability to a project
that had written real policy into its overlay would silently destroy it.

### The overlay is impact-required, not denied

```python
gate={"impact_required": ["**/governance/policy.yaml"]},
```

A policy overlay decides whether a change is allowed to land, so it is not
something a change may quietly alter on its way past. It is deliberately *not*
denylisted — a project must be able to write its own obligations. Edits are made
visible instead, and the loosening guard lives in the loader, where it can read
what the edit actually did rather than merely that an edit happened.

---

## Implementation notes

### `load_ontology` is cached — overlays must never write through it

`load_ontology()` is `functools.lru_cache`d and shared by every caller. An
overlay that mutated it would leak one project's policy into every other, and
the test that caught it would be somewhere else entirely.

Every path that overlays returns a copy owning its own policy list. The path
most likely to leak was the early return in `load_group_ontology` for a missing
`extension.yaml`, which handed back the cached object directly:

```python
if not ext_path.exists():
    # `base` is lru_cached and shared by every caller, so an overlay must
    # never touch it — hand back a copy that owns its own policy list.
    return _overlay_policy(_copy(base), gdir / "policy.yaml", scope)
```

### `PolicyRelaxation` subclasses `ValueError`

`validate._ontology_for` catches `(OSError, ValueError)` to fall back to the
platform ontology when a group's files are unreadable. `PolicyRelaxation` must
be re-raised **before** that handler, or a project that tried to weaken a policy
would be validated against the very policy set it tried to weaken:

```python
except PolicyRelaxation:
    # A relaxation is a finding, not a fallback.
    raise
except (OSError, ValueError):
    pass
```

### Severity is ranked, not compared

```python
SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2}
```

`SEVERITY_RANK` is what makes "tightening only" a computation rather than a
convention.

---

## API

| Function | Returns |
|---|---|
| `load_ontology()` | the platform floor — cached, never mutate |
| `load_group_ontology(root, group)` | platform + group extension + group policy |
| `load_project_ontology(root, group, project)` | the above + the project's policy |
| `merge_policies(base, overlay, scope)` | tightening-only merge; raises `PolicyRelaxation` |

`Policy` gained one field:

```python
scope: str = "platform"   # "platform" | "group:<g>" | "project:<g>/<p>"
```

It records which layer set the severity — reattributed only on a real
tightening, so an overlay that merely adds evidence leaves the owner where it
was.

---

## What is deliberately *not* layered

Concepts, topology and relations stay at platform and group scope.

Project-scoped vocabulary would mean each project defining its own `Payment`,
and `acme-rollup` — which depends on `AssetKey(acme-us, fct_revenue)` and
`AssetKey(acme-eu, fct_revenue)` — would then sum two things that merely share a
name. That is the "an assumption carried across is a bug" failure moved out of
the vocabulary, where `pf check` can catch it, and into the arithmetic, where
nothing can.

Sharing a **word** is not sharing **business logic**. That a `Payment` has an
amount, a currency and an `event_time` is vocabulary. *How acme-us recognises
revenue* is business logic, and it already lives in project-confined dbt models,
where it belongs.
