# CI workflows, one diagram each

Every GitHub workflow in this repository, drawn. [`CI.md`](CI.md) is the prose;
this is the board version — one diagram per workflow, each with a worked example
underneath it, all of them pasteable into Miro without editing.

## Pasting into Miro

Copy a fenced block's contents (not the fence) and use **Miro → Diagram →
Mermaid**. The syntax here is deliberately plain so it survives that importer:

| rule | why |
|---|---|
| `flowchart TD` only | Miro's importer is flowchart-centric; sequence and state diagrams do not come through |
| no `<br/>`, no HTML tags | dropped silently, taking half the label with them |
| every label double-quoted | a label with a slash, dot or space parses as syntax otherwise |
| no `style`, `classDef` or `linkStyle` | ignored on import, and they make the source harder to edit on the board |
| ASCII only, no parentheses inside labels | the importer is stricter than GitHub's renderer |

Shapes carry meaning: `([ ])` is a trigger, `[ ]` is a job or a step, `{ }` is a
decision, and edge labels are the condition under which that path is taken.

---

## 0. The fleet — what wakes on what

Twenty-three workflows. Nothing here runs "the build"; each answers one question,
and most sleep through any given change.

```mermaid
flowchart TD
  PR(["Pull request opened or updated"])
  PUSH(["Push to main"])
  CRON(["Schedule - daily"])
  ASK(["A person asks"])

  PR --> AC["agent-context - is generated context current, is every commit within the cap"]
  PR --> GOV["ai-governance - provenance chain, control coverage, code scan"]
  PR --> REP["pr-report - blast radius, as one comment"]
  PR --> PATHS{"Which paths changed?"}

  PATHS -->|"groups/GROUP/projects/PROJECT/**"| PROJ["one project workflow - 11 of them"]
  PATHS -->|"platform/** pyproject.toml uv.lock gate.yaml"| PLAT["platform - tests, gates, converged"]
  PATHS -->|"platform/** or any .memory/**"| PTEST["platform-tests - suite"]
  PATHS -->|".gitmodules"| PINS["vendor-pins - every pin still resolves"]
  PATHS -->|"nothing matched"| SLEEP["those workflows never start"]

  PUSH --> AC
  PUSH --> GOV
  PUSH --> PINS
  PUSH --> LOOP["loop-observations - run the loops, file findings"]

  CRON --> GOV
  CRON --> PINS
  CRON --> LOOP
  CRON --> VSYNC["vendor-sync - fetch upstreams, open a PR"]
  CRON --> BOTS["bot-findings - review findings become issues"]

  ASK -->|"add the label claude-review"| CREV["claude-review - judgement, read only"]
  ASK -->|"mention claude in a comment"| CIMP["claude - implements on a branch"]
  ASK -->|"Copilot agent starts work"| COP["copilot-setup-steps - build its sandbox"]
```

**Example.** You change one dbt model in `jaffle-shop`. `agent-context`,
`ai-governance` and `pr-report` run because they have no path filter;
`jaffle-shop.yml` runs because the path matched; the other ten project
workflows, `platform`, `platform-tests` and `vendor-pins` never start. About
nine checks, not thirty.

---

## 1. A project workflow — `jaffle-shop.yml` and its ten siblings

Generated per project by `pf bootstrap`, all eleven the same shape:
`acme-eu` `acme-rollup` `acme-us` `commodity-india` `commodity-rollup`
`commodity-us` `globex-core` `globex-eu` `jaffle-shop` `zenith-de` `zenith-uk`.

One job diffs the pull request once and publishes a boolean per area; the other
five each declare which boolean they need. This is the most important diagram
here — it is why a README change does not wait on a warehouse build.

```mermaid
flowchart TD
  T(["PR touches groups/jaffle/projects/jaffle-shop/**"])
  T --> C["changes - diff once against the merge base, fetch-depth 0"]
  C --> O{"Which areas moved?"}

  O -->|"any"| AIR["air-baseline - pf air gate jaffle jaffle-shop"]
  O -->|"any"| ARCH["architecture - pf kg build then pf arch --check"]
  O -->|"any"| KG["kg-current - pf kg check --strict"]
  O -->|"models or sources"| IMP["impact-gate - pf impact-gate over the changed models"]
  O -->|"transform"| REC["recce - pf tool recce ci, diff against the base build"]
  O -->|"none"| SKIP["every job skips - shown as skipping, not as a pass"]

  AIR --> V{"all green?"}
  ARCH --> V
  KG --> V
  IMP --> V
  REC --> V
  V -->|"yes"| OK["check passes"]
  V -->|"no"| BAD["check fails - the job name is the pf command to run locally"]
```

**Example.** Editing `marts/customers.sql` sets `models`, `transform` and `any`,
so all five run. Editing only that project's `README.md` sets `any` alone —
`impact-gate` and `recce` skip, and the review is not held up by a build.

---

## 2. `platform.yml` — the shared engines

```mermaid
flowchart TD
  T(["PR touches platform/** pyproject.toml uv.lock gate.yaml groups/GROUP/group.yaml"])
  T --> TESTS["tests - pytest platform/tests then ruff check platform"]
  T --> GATES["gates - pf tokens, pf check, pf group verify, pf loop audit"]
  T --> CONV["converged - run pf bootstrap --all on a clean checkout"]

  CONV --> D{"Did bootstrap change a tracked file?"}
  D -->|"yes"| F["FAIL - the committed tree is behind the scaffold"]
  D -->|"no"| P["PASS - the scaffold and the repository agree"]
  F --> FIX["run pf bootstrap --all locally and commit what it writes"]
```

**Example.** You add a capability that writes a new file into every project.
`converged` fails on your PR because the eleven projects do not have it yet —
run `pf bootstrap --all`, commit the files, and the job goes green. This is the
job that catches a project silently drifting behind the scaffold.

---

## 3. `platform-tests.yml` — the suite, on a narrower trigger

```mermaid
flowchart TD
  T(["PR touches platform/** the lockfiles or any .memory/**"])
  T --> CO["checkout, then fetch each vendored pin one by one"]
  CO --> SY["uv sync"]
  SY --> L["Lint - ruff check platform/"]
  L --> TI["Test index is current - pf test check"]
  TI --> MI["Memory index is current - pf memory check"]
  MI --> AM["Architecture map is current - pf arch check"]
  AM --> SU["Suite - pytest platform/tests -q"]
  SU --> R{"all green?"}
  R -->|"yes"| OK["suite passes"]
  R -->|"no"| BAD["suite fails - the step name says which command to run"]
```

**Example.** You add `platform/tests/gate/test_new_thing.py` and forget
`pf test index`. The suite itself passes; **Test index is current** fails, because
a fresh clone would not list your test. One `pf test index` and a commit fixes it.

---

## 4. `agent-context.yml` — every pull request, no path filter

The one that can repair itself. It is also where the per-commit file cap is
re-applied, which is the layer no developer machine can skip.

```mermaid
flowchart TD
  T(["Every pull request, pushes to main, manual dispatch"])
  T --> CAP["pf gate --commits - every commit in the PR within maxFiles"]
  CAP --> CTX["pf context check - CLAUDE.md AGENTS.md GEMINI.md Copilot agree"]
  CTX --> MEM["pf memory check"]
  MEM --> TST["pf test check"]
  TST --> ARC["pf arch check"]
  ARC --> GUI["pf guide check"]
  GUI --> HAR["pf harness check"]
  HAR --> MDL["pf semantic mdl --check --all"]
  MDL --> OKF["pf tool okf check --all and pf tool okf graph --all"]
  OKF --> TOK["pf tokens - advisory, never fails the job"]
  TOK --> Q{"Did any step fail?"}

  Q -->|"no"| OK["check passes"]
  Q -->|"yes"| SUM["write what is stale into the run summary"]
  SUM --> G{"Same-repo PR and AGENT_CONTEXT_TOKEN present?"}
  G -->|"yes"| RF["refresh - pf context refresh, commit, push to the PR branch"]
  G -->|"no"| RED["check fails - the log names the one command to run"]
```

**Example.** You add a memory note with `pf memory add` but do not commit the
regenerated index. **Memory index is current** fails, the summary says so, and
the `refresh` job pushes the regenerated index onto your branch — so the next
agent reads context that matches the code.

---

## 5. `ai-governance.yml` — four checks that fail in different directions

Run together because each is blind to what the others see.

```mermaid
flowchart TD
  T(["Every pull request, pushes to main, daily at 07:23"])
  T --> P["Provenance chain - pf provenance verify over the ledger"]
  T --> S["ASQAV compliance scan - vendored scanner over the agent code"]
  T --> A["AI control baseline - pf air coverage and pf air verify"]
  T --> K{"Is this a pull request?"}
  K -->|"no, a push or the schedule"| TS["Timestamp anchor coverage - is the newest anchor recent"]
  K -->|"yes"| SK["anchor skips - a PR cannot have anchored yet"]

  P --> V{"all green?"}
  S --> V
  A --> V
  V -->|"yes"| OK["governance passes"]
  V -->|"no"| BAD["a named control failed - docs/AIR.md says what it covers"]
```

**Example.** An agent edits a file under `provenance/`. The hash chain no longer
verifies, **Provenance chain** goes red, and the PR cannot be merged on a green
board — which is the point: the record of what an agent did is not the agent's
to edit.

---

## 6. `pr-report.yml` — one comment, edited in place

```mermaid
flowchart TD
  T(["PR opened, synchronised, reopened or marked ready"])
  T --> B["Build the report - pf pr report over the diff"]
  B --> C{"Does a marker comment already exist?"}
  C -->|"yes"| E["edit that comment in place"]
  C -->|"no"| N["post one new comment"]
  E --> U["upload the same JSON as an artifact"]
  N --> U
  U --> V{"What is the verdict?"}
  V -->|"block"| F["FAIL the check"]
  V -->|"warn or allow"| OK["report passes"]
```

**Example.** You rename a column eleven dashboards read. The comment names the
downstream exposures, the verdict is `block`, and the check goes red — before a
reviewer has read a line of SQL. Eleven pushes later there is still one comment,
not eleven stale ones.

---

## 7. `vendor-pins.yml` — two questions per submodule

```mermaid
flowchart TD
  T(["PR touching .gitmodules, pushes to main, daily at 07:00"])
  T --> L["read every submodule path and url from .gitmodules"]
  L --> Q1{"Does the remote still exist? git ls-remote"}
  Q1 -->|"no"| F1["FAIL - the upstream was deleted or made private"]
  Q1 -->|"yes"| Q2{"Is the pinned commit still fetchable?"}
  Q2 -->|"no"| F2["FAIL - the pin was force-pushed away"]
  Q2 -->|"yes"| OK["Pins resolve passes"]
```

**Example.** An upstream deletes its repository. Nothing in this repo changed,
so no PR is open — the daily run is what notices, and it notices the same day
rather than the next time somebody clones with `--recursive`.

---

## 8. `vendor-sync.yml` — fetches, reports, never approves

```mermaid
flowchart TD
  T(["Daily at 01:00, or manual dispatch"])
  T --> FK["forks - sync each fork from its source"]
  FK --> SY["sync - fetch every upstream and compare against the lock"]
  SY --> REC["record the comparison, whatever the outcome"]
  REC --> M{"Did any upstream move?"}
  M -->|"no"| Q["nothing to do"]
  M -->|"yes"| PR["open or update one sync pull request"]
  PR --> H["a human runs pf vendor approve after reading the diff"]
  H --> DONE["the pin moves only then"]
```

**Example.** `wrenai` publishes a fix. The job opens a PR showing exactly what
moved. It never runs `pf vendor approve`, because approval means *a person read
the diff*, and a workflow cannot mean that.

---

## 9. `loop-observations.yml` — findings go where people already look

```mermaid
flowchart TD
  T(["Daily at 06:17, pushes to main touching groups platform or vendor"])
  T --> BG["build every project graph and run each deterministic loop"]
  BG --> O{"Did a loop observe anything?"}
  O -->|"yes, and no issue exists"| NEW["open an issue, label loop-observation"]
  O -->|"yes, and an issue exists"| UPD["update that issue in place"]
  O -->|"no, and an issue is open"| CLOSE["close it - the run came back clean"]
  NEW --> TR["keep the trace as an artifact"]
  UPD --> TR
  CLOSE --> TR
```

**Example.** A model gains a test that never fails. The loop notices, files one
issue per loop per project, and closes it the day the model changes — so
`loop-ledger.json` is not a file somebody has to remember to open.

---

## 10. `claude-review.yml` — opt in, read only

```mermaid
flowchart TD
  T(["Someone adds the label claude-review"])
  T --> G{"Is ANTHROPIC_API_KEY set?"}
  G -->|"no"| X["exit green with an explanation - an unconfigured fork is not broken"]
  G -->|"yes"| CO["checkout with full history, uv sync"]
  CO --> CTX["collect platform context - pf gate per commit, pf gate per path, pf check"]
  CTX --> RV["review what a rule cannot decide - SQL semantics, grain, blast radius, isolation"]
  RV --> CM["post one comment carrying a marker, updated in place next run"]
```

**Example.** A mart pre-aggregates what a metric aggregates. No gate can see
that; the review names the file, the line, and the wrong number it produces.
The gate verdicts go in as *evidence* so the reviewer does not re-derive them.

---

## 11. `claude.yml` — mention it by name, and it writes

```mermaid
flowchart TD
  T(["Mention claude in an issue, an issue comment or a PR review comment"])
  T --> G{"Is ANTHROPIC_API_KEY set?"}
  G -->|"no"| X["exit green with an explanation"]
  G -->|"yes"| CO["checkout, fetch vendored pins, uv sync"]
  CO --> HK["pf install-hook - the same commit gate a person gets"]
  HK --> IM["implement, reading CLAUDE.md, the memory notes and the gates"]
  IM --> BR["push a branch - never main, never a fork"]
```

**Example.** An issue says "the safe-divide macro brackets the wrong operand".
It fixes the macro, adds the test, and pushes a branch under the same twelve-file
cap a person commits under — `pf install-hook` is what makes that true.

---

## 12. `copilot-setup-steps.yml` — the sandbox, before the agent starts

```mermaid
flowchart TD
  T(["GitHub Copilot's coding agent starts on this repository"])
  T --> CO["checkout, fetch each vendored pin, uv sync --frozen"]
  CO --> HK["pf install-hook - so the gate exists in its sandbox too"]
  HK --> V["prove the first commands work - pf, the memory index, the suite"]
  V --> R{"Did they run?"}
  R -->|"yes"| OK["the agent starts in a working checkout"]
  R -->|"no"| F["FAIL here, not silently inside the agent's first task"]
```

**Example.** Copilot reads `AGENTS.md`, which tells it to run `pf test check`.
This workflow is why that command exists in its sandbox. The file must sit at
exactly this path and the job must carry exactly this name — GitHub looks it up
by both.
