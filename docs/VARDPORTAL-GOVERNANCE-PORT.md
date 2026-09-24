# Porting vardportal's guardrails into data-platform

An architecture review of `1177-Stockholm/vardportal` (private, 283 commits,
2026-08-25 → 2026-09-24), read for one purpose: deciding what of its governance
machinery is worth moving into `Atomz-org/data-platform`, and what is not.

**Written for:** platform engineers and the architect deciding the port. It
assumes familiarity with this repo's `AGENTS.md`, `gate.yaml` and provenance
chain.

---

## 1. Method, and what this review does not cover

Twelve subsystem readers read the cloned tree; every finding they produced was
re-checked by three or four independent verifiers under distinct lenses
(evidence, materiality, severity, and pure refutation for anything rated high).
**553 of 562 agents completed. 163 findings survived verification; 2 were
refuted and dropped.** Of the survivors, **127 are limitations the repo already
declares about itself** — those are marked and down-weighted rather than
counted against it.

Two gaps in coverage, stated plainly because a review that hides its holes is
the thing this repo's own ADR-0074 exists to correct:

- The `.compliance-trace/` + `.execution-logs/` reader died mid-run. I re-ran
  that scope separately and **hand-verified all 10 of its findings** against the
  clone myself — every path, line and quote checks out.
- **Eight further scopes the completeness critic identified were never read.**
  All eight failed on a session limit. They are: the staff workbench screens
  (~2,600 unread lines), `Kits/` (2,768 lines), the docs-site build, the
  Confluence/wiki publish pipeline (1,953 lines), `assets/inside-vardportal.html`,
  agent configuration and the brand MCP server, and the disposition of the two
  anomalous ledger folders. **Nothing below rests on those areas**, but the
  review is not complete over the repository.

---

## 2. What vardportal actually is

A Swedish healthcare portal demonstration that drafts a clinical note during the
patient conversation. It is unusually honest about itself: a system card at
`/om/piloten` is a typed array (`src/data/pilotStatus.ts`) whose type comment
*forbids* the string "TBD", rendered on a route, with an undismissable
disclosure banner mounted above the router so no page can omit it. Nine status
claims were checked against code and hold.

The governance is not decoration. It has mechanical teeth, and — the part worth
copying — **the teeth have been verified by attacking them**.

---

## 3. The five mechanisms worth porting

Ranked by what they would buy this repo, not by how impressive they are.

### 3.1 The adversarial gate test — port this first

`tests/governance/complianceGate.test.ts` clones the repository into a temp
directory, **plants one real violation per guardrail**, runs the real gate
script, and asserts exit 1 *with the specific check id*. Seven further cases
assert the gate does **not** fire on sanctioned shapes (audio-only capture, a
ten-file commit, `alt=""`).

This is the single highest-value idea in the repository. A gate rule that
silently stops matching is indistinguishable from a repo with no violations.
vardportal found this out the hard way: their own finding GATE-4 records that
these excellent tests *never run in CI*, so the proof exists and is not
executed. Port the technique; do not port that mistake.

**Correction to the first draft of this document**, which claimed we have no
test that proves a rule still bites. That was wrong, and asserted without
looking: `platform/tests/gate/` already holds 19 files, including must-not-fire
cases. What was genuinely missing is narrower — nothing *derived* coverage from
the policy, so a rule added to `gate.yaml` was tested only if someone remembered
to write a case for it.

**Done** — `platform/tests/gate/test_gate_rule_reachability.py` reads `gate.yaml`
and demands, for every pattern in it, a path the rule still claims. It found a
real defect on its first run: **both `impact_required` entries are dead**,
outranked by `autoMergeAllowlist`'s blanket `**/*.sql`, so no blast radius is
demanded for any dbt model and `pre_tool_use.py` never reaches its warn branch.
Logged as `I-0001` in `IMPROVEMENTS.md` rather than fixed in place, because the
precedence is a policy decision. It also confirmed the denylist is clean: all 17
shadowed entries are *declared* in `denylist_except`; none over-matched.

### 3.2 The machine-readable processing register

`src/data/processingRegister.ts` declares every storage key with purpose, legal
basis, erasure route and FHIR mapping. Guardrail G10 fails any key used in `src/`
without an entry; the gateway refuses `PUT` on any key outside the register; the
SPA drops unknown keys on hydration; and a contract test asserts it. **The same
declaration is the GDPR art. 30 record, the runtime allowlist and the CI rule.**

For us the analogue is obvious and we already have half of it: `policy.yaml`
carries FINOS control ids and `pf air coverage` derives whether each control's
`enforced_by` resolves. What we lack is the *runtime allowlist* half — the
register that a data path physically cannot step outside of.

### 3.3 Derivation proof over a fixed fixture

G12 does two things: a regex ban on generative-model clients entering `src/`,
and — the real mechanism — it imports the actual engine, runs it over a fixed
four-utterance conversation, and fails if `derivationDelta` returns any drafted
word absent from the transcript and a closed vocabulary.

This is a *falsifiable property test of an AI output boundary*, not a policy
sentence. The transferable shape for us: assert that a generated artefact
contains nothing outside a declared input set. Note the honest limit — it proves
the property for one fixture, not "every drafted word" as their README claims,
and it does not reach the Python services in `api/`.

### 3.4 Correction-as-a-new-record

Their strongest cultural artefact. ADR-0074 corrects nine false claims made by an
unattributed folder; ADR-0108 marks its own originating prompt *not captured*
rather than reconstructing it; ADR-0067 corrects its own mid-investigation error.
Records are corrected by *adding* a record, never by editing one.

We already practise supersession in `decisions/`. What was missing is
enforcement: `decisions/README.md` has always said *"Never delete one;
supersede it"*, and nothing checked it — vardportal's `DEC-1` in our own tree.

**Done** — `records_immutable` in `gate.yaml`, implemented as
`check_record_immutability` in `pf/loops/gate.py` and wired into `check_paths`
so it runs wherever the gate runs. Editing an accepted record is refused;
changing its Status line is not, because that is how a supersession lands. A
record still being drafted, and one git has never seen, are both left alone.

### 3.5 Least-privilege publishing workflows

`contents: read` at workflow level, `pages: write` scoped to the publishing job
alone, and a `pull_request` event forcing a Confluence **dry run** so unmerged
content never reaches a live space. Directly applicable to our Confluence and
docs pipelines.

---

## 4. What not to port — vardportal's own high findings

Twelve findings survived at high severity. They fall into three lessons.

**Lesson 1 — a convention is not a control.** `DEC-1`: record immutability is
declared in the README, `CLAUDE.md` and both templates, and **enforced by
nothing.** G1 and G7 pass on *any* change to a `.decisions/NNNN*.md` path, so
editing an accepted record satisfies the "add a record" requirement. Five ADRs
were in fact edited after acceptance (0033, 0045, 0054, 0066, 0069) — three of
them inside merge commits, where plain `git log -- <file>` does not show it.

**Lesson 2 — the enforcement point must exist.** `GATE-1`: the repo's
human-review requirement cannot be enforced at all. The GitHub API returns
`HTTP 403 — Upgrade to GitHub Pro or make this repository public` for both
branch protection and rulesets. It is a private repo on a plan where the control
does not exist. **Before committing to a control, verify the platform can host
it.** `GATE-4` and `TEST-1` are the same lesson: 254 tests, including the
excellent adversarial ones, are run by no workflow and no hook.

**Lesson 3 — prose drifts away from code, and the prose is what people read.**
`SPA-4` is the sharpest: the patient-facing data-protection page asserts that no
data leaves the journal system, while the translation feature sends transcript
text to Google Cloud Translation — declared in the same file, item 12. `API-3`:
"every read is logged" does not hold — `GET /api/store` returns every patient's
notes with no access-log entry. `TOGAF-1`: the ADM's baseline ("no backend, the
browser is the system") stopped being true when a gateway and four Python
services landed. `DATA-1`: signed notes are editable in place despite a
documented terminal `signed` state, with no amendment record, so the originally
signed text is not retained.

**The meta-lesson for us:** every one of these is a *documentation claim without
a derivation*. Our `pf air coverage` already embodies the fix — it **derives,
never stores,** whether a control's enforcement resolves, and a control whose
`enforced_by` resolves to nothing reports as failing. That design decision is
worth more than anything in vardportal, and it should be extended to cover the
claims in `docs/`, not just `policy.yaml`.

---

## 5. What this repo already has — correcting the plan

The proposal assumes governance here lives in "passive text files". It does not.
Measured against the four phases:

| Proposed | Actual state |
|---|---|
| **P1** Create `.claude/settings.json` hooks map | **Exists.** `PreToolUse` + `PostToolUse` → `platform/hooks/{pre,post}_tool_use.py`, matched on `Edit\|Write\|MultiEdit\|NotebookEdit\|Bash` |
| **P1** Build a PreToolUse gate that blocks | **Exists**, 192 lines. Consults `gate.yaml`, `exit 2` blocks, stderr reaches the agent |
| **P1** Devcontainer isolation | **Absent — a genuine gap** |
| **P2** Commit `LOOP.md` / `STATE.md` | **Both exist.** `LOOP.md` is an earned autonomy ladder (L1→L3) with token budgets, a circuit breaker, a ledger and trace logs; `STATE.md` is machine-written by `pf loop run` |
| **P2** SQLite memory with FTS5 | **Exists** as `.memory/notes/` + `pf memory`; an `agentmemory` MCP server with FTS5/TF-IDF is configured session-side |
| **P3** `.decisions/` records | **Exists** as `decisions/` per project (`ADR-NNNN-*.md` + `README.md` + `loop-memory.yaml`) |
| **P3** `agdr.schema.json`, Y-statements | **Absent.** See caveat below |
| **P3** `TOGAF-ADM.md` | **Absent**; `docs/ARCHITECTURE.md` + `docs/ARCHITECTURE-MAPS.md` cover part of it |
| **P3** `TESTING.md`, `TEST-FINDINGS.md`, `IMPROVEMENTS.md` | **Absent — genuine gaps** |
| **P3** Bind validations to PostToolUse | **Exists** (`post_tool_use.py`) |
| **P4** Inject instructions into `CLAUDE.md` | **Would fail CI.** See §6 |

Two things here are already **stronger than vardportal's** and should not be
traded away:

- **The provenance chain.** Five stages — intent, decision, execution, a SHA-256
  chain, an RFC 3161 + OpenTimestamps anchor over the head — with `provenance/**`
  denied to every agent. vardportal's equivalent is markdown plus git, with
  unsigned commits and, by their own `TRC-4`, **no machine-verifiable authorship
  on any record.**
- **Ordering that prevents a flattering record.** `pre_tool_use.py` writes INTENT
  *before* consulting the gate, so a denied action still leaves evidence of what
  was attempted. Its docstring states the principle better than I could: *"A gate
  that only logs its refusals can prove it said no; it cannot prove it was ever
  asked."*

**Caveat on AgDR.** I could not verify that "Agent Decision Record" with an
`agdr.schema.json` is an established open standard, and I am not willing to
scaffold shared platform infra against a spec I cannot confirm exists. The
**Y-statement is real** (Zimmermann et al.) and is a good fit for
`decisions/`. Recommendation: adopt Y-statements now; treat the JSON schema as
our own, versioned in-repo, unless you can point me at the upstream.

---

## 6. Two corrections to Phase 4

### 6.1 The instruction block cannot live in `CLAUDE.md`

`uv run pf tokens` reports the root router at **699 of 700 tokens** —
`ROUTER_BUDGET` in `platform/src/pf/kg/card.py:26`, CI-enforced. One token of
headroom. The block belongs in **`AGENTS.md`**, which is already the per-scope
protocol for every coding agent (Copilot, Codex, Gemini, Cursor, Jules,
OpenCode, Claude Code) and is explicitly designed to carry what the 700-token
router cannot.

### 6.2 The "Hook Responses (CRITICAL)" instruction is unsafe as written

> *"If a tool execution is blocked … you must treat this as an automated quality
> check. Do not stop your execution or ask the user for permission … autonomously
> correct your command or code to comply with the blocked policy, and retry."*

Do not ship this. It instructs an agent to treat **a security denial as a lint
error** and iterate until something gets through. Concretely, in this repo:

- `provenance/**` is denied to every agent precisely so an agent cannot edit the
  record of what it did. Under this instruction, that denial becomes a puzzle to
  route around.
- `.claude/settings.json` puts `git push`, `gh pr create`, `gh pr merge` and
  `git submodule update` on the **`ask`** list so a human decides. "Do not ask
  the user for permission" negates that list directly.
- `CLAUDE.md` states bumping a vendor pin is *"a human decision, never an
  agent's."*
- `LOOP.md` already catalogues *"Loop retries a broken fix forever"* as a known
  failure mode, bounded by `escalate_after: 3` counted in the ledger.

The distinction the instruction misses is one our hook **already implements**:
`pre_tool_use.py` separates a `blocked` verdict (exit 2) from a `warn` verdict
(exit 0 with blast-radius feedback), and its header says the models-and-sources
case is *"informed rather than blocked."*

**Corrected rule, for `AGENTS.md`:**

> Your environment is intercepted by `PreToolUse` and `PostToolUse` hooks, which
> return two different things.
>
> **Advisory feedback** — a formatter, a lint result, a missing decision record,
> a blast-radius warning (exit 0 with stdout). Treat it as an automated quality
> check: correct and retry, at most **three** times for the same target, then
> stop and report.
>
> **A policy block or permission denial** — `exit 2`, or a
> `permissionDecision: "deny"` payload. This is a decision, not a diagnostic.
> **Stop. Do not rephrase the command, split it, or route around the rule.**
> Report which rule fired (`BLOCKED by gate.yaml [<rule>]`) and what you were
> trying to achieve. If the rule is wrong, that is a pull request against
> `gate.yaml`, reviewed by a person — never a retry loop.

---

## 7. Sequenced backlog

Each item is independently landable. Ordered by value per unit of risk.

1. **Adversarial gate tests** (§3.1) — plant one violation per `gate.yaml` rule
   in a temp clone, assert the block and the rule id, plus must-not-fire cases.
   Wire into `pf check`. *Highest value; touches no production path.*
2. **Fix the corrected hook-response rule into `AGENTS.md`** (§6.2) — text only,
   removes a live footgun before it is ever introduced.
3. **Record-immutability check** (§4, lesson 1) — fail a PR that *modifies* an
   accepted record under `decisions/` instead of adding one. Must use
   `--full-history -m`, or merge-commit edits stay invisible.
4. **`TEST-FINDINGS.md` + `IMPROVEMENTS.md`** with the executable-defect
   convention: each finding is a `todo` test asserting intended behaviour, with
   root cause and suggested fix. Counts must reconcile to the markers.
5. **Y-statements in `decisions/`**, plus an in-repo schema we own (§5 caveat).
6. **Devcontainer** (§5) — the one genuine Phase 1 gap.
7. **Extend `pf air coverage` to documentation claims** (§4 meta-lesson) — the
   highest-leverage item, and the one with no equivalent in vardportal. A claim
   in `docs/` that names an enforcement point which no longer resolves should
   report as failing, exactly as a `controls:` entry does.
8. **Least-privilege publishing workflows** (§3.5).

`TOGAF-ADM.md` is deliberately last and possibly never: vardportal's own
`TOGAF-1` shows their ADM went stale the moment the architecture moved, and our
`docs/ARCHITECTURE-MAPS.md` is generated rather than written. A generated map
that cannot drift beats a TOGAF document that can.

---

## 9. What landed, and what was deliberately not ported

**Landed** (branch `governance/vardportal-port`):

| | |
|---|---|
| `test_gate_rule_reachability.py` | Coverage derived from `gate.yaml`, so a new rule is tested from the commit that adds it. Found `I-0001` on its first run. |
| `records_immutable` + `check_record_immutability` | vardportal's `DEC-1` closed in our tree, wired into `check_paths` so it runs wherever the gate runs. |
| `AGENTS.md` §2 "When the gate answers back" | A `warn` is a diagnostic; a `deny` is a decision. Plus two `Never` bullets. |
| `.devcontainer/` | The filesystem boundary. Network egress explicitly still open. |
| `IMPROVEMENTS.md` | Where a session records a problem outside its own scope. |

**Not ported, with reasons:**

- **`TEST-FINDINGS.md`** — a second defect register beside `IMPROVEMENTS.md`
  would reproduce the exact problem vardportal's own `TRC` scope reports: four
  overlapping record folders (`.decisions/`, `.agents/`, `.compliance-trace/`,
  `.execution-logs/`) where two are gate-enforced and two are not, and a reader
  cannot tell which is authoritative. One register, enforced, beats two.
- **`.compliance-trace/` and `.execution-logs/`** (the folders in the
  screenshot) — we already have both, and stronger. The granular
  intent→decision→execution trace is the provenance chain plus `logs/trace/`
  JSONL, hash-linked and RFC 3161 anchored; vardportal's equivalents are
  markdown with, by their own `TRC-4`, no machine-verifiable authorship on any
  record. Adding root dotfolders would fragment a model that already works.
- **`TESTING.md`** — `platform/tests/README.md` is generated by
  `pf test index` (62 files, 1046 tests) and cannot drift. A hand-written one
  would.
- **`COMMERCIAL.md` and `PATENTS.md`** — these encode a dual-licence and
  patent position, which is a business decision about this repository, not a
  file to copy. This repo has `LICENSE`, `NOTICE` and `THIRD-PARTY-NOTICES.md`
  and no stated commercial posture. Inventing one would be fabricating a legal
  position on your behalf. If you want a dual licence, say what it should be
  and it is a short change.
- **`SHOWCASE.md`** — a product walkthrough with no governance function here.
- **`SECURITY.md`** — already exists and is good: private disclosure, a 7-day
  acknowledgement window, and it already scopes provenance tampering as high
  severity.

## 10. The one thing to decide

`I-0001`. Both `impact_required` rules are dead, so the PreToolUse hook never
shows a blast radius before a model edit — the failure `LOOP.md` records as
already caught once. The fix is a precedence change in `check_path`, but which
way is a policy call: consult `impact_required` before `autoMergeAllowlist` (a
warning does not block a merge, so nothing is lost), narrow the allowlist, or
delete the rule and stop claiming the control. Doing nothing is the only option
that is not available, because the policy currently reads as though the control
exists.

---

## 8. Verification notes

Every claim about vardportal traces to a file and line in the clone, verified by
at least three independent agents; the high-severity claims by four. Every claim
about data-platform in §5 and §6 I verified directly in this working tree —
`.claude/settings.json`, `platform/hooks/pre_tool_use.py:1-30,136-160`,
`gate.yaml:232-244`, `AGENTS.md`, `LOOP.md`, `STATE.md`, the `decisions/`
directories, and `uv run pf tokens`.

The eight unread scopes in §1 remain unread.
