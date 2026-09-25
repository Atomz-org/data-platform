# Control: session containment

**Written for:** whoever has to attest that this repository's agent activity is
auditable — and for the engineer who has to keep the control working.

**Objective.** Every file a Claude Code session writes on behalf of this
repository lands inside this checkout.

**Why it is a control and not a preference.** An agent's working files are
evidence of what the agent did. Evidence that lives in a system temp directory
is not findable by the operator, not covered by any backup, not covered by any
retention period anyone here chose, and is removed by the OS on a schedule
nobody here sets. `docs/GOVERNANCE.md` records *decisions*; this control is what
keeps the *working material* behind those decisions reachable. A chain of
custody that ends at `/private/tmp` is not a chain of custody.

---

## 1. Scope

| In scope | Out of scope |
|---|---|
| session scratchpad, background task output, pasted images | the user's own shell, run outside Claude Code |
| workflow runs and run scripts | temp files written by `dbt`, `duckdb`, `uv` (see §6) |
| session transcript, subagent transcripts, tool results | anything under `vendor/` |

**Containment** here means the bytes are inside the checkout. **Direct
containment** additionally means the path the harness uses is inside it. The
difference matters and §3 keeps them apart, because a redirection can break in
ways a direct write cannot.

## 2. Threat model — how the objective gets violated

| # | Path to violation | Realised? |
|---|---|---|
| T1 | Harness places its temp root outside the repo and nothing redirects it | **yes — the default on macOS** |
| T2 | Redirection happens after the harness has already written | yes — every `resume` and `compact` |
| T3 | Redirection is refused and the refusal is not noticed | yes — went unnoticed for several sessions |
| T4 | Redirection itself breaks the session | **yes — see §5** |
| T5 | Retention sweep deletes redirected history | not realised; designed against |
| T6 | `git clean -xdf` removes `.tmp/` with a live session's state | not realised; accepted (§6) |

## 3. Controls

| id | Control | Type | Status |
|---|---|---|---|
| **SC-1** | `CLAUDE_CODE_TMPDIR=<repo>/.tmp` exported before the harness starts — `.envrc`, `just claude`, `bin/claude-here` | preventive | **UNVERIFIED** |
| **SC-2** | `platform/hooks/session_start.py` symlinks the harness's directories into the checkout | corrective | verified in use |
| **SC-3** | `pf workflow capture` copies what cannot safely be linked | corrective | verified by test |
| **SC-4** | The hook states the verdict on every session — `direct`, `linked`, or `OUTSIDE` | **detective** | new, untested |
| **SC-5** | `PF_SCRATCH_ENFORCE=1` refuses to start a session that would write outside | preventive | new, untested, **off by default** |
| **SC-6** | `workflows.ADOPT_NOT_WHILE_LIVE` — never link `tasks/` under a running session, empty or not | safety | test added (`test_workflows_live_tasks.py`) |

**SC-1 is the only preventive control that removes the problem rather than
repairing it.** Everything else is compensating. It is also the one that has
never been observed working — see §4.

**SC-4 is the control that was missing.** T3 is the instructive failure here:
the redirection was refused, the refusal was reported once at session start, and
nothing said anything afterwards. The repository's position was "contained"
while the actual state was "outside", and nobody could tell the difference
without running a command they had no reason to run. A control that is silent
when it is working is indistinguishable from a control that is silent because it
is broken.

### Why a setting cannot implement SC-1

Claude Code resolves its temp root once, at process start, from the environment
it inherits. An `env` block in `.claude/settings.json` is applied to the tool and
hook subprocesses the harness spawns *afterwards*. Tested: the variable was
added to project settings, the session was restarted, and the temp root did not
move. The variable must be exported by whatever launches `claude`.

`CLAUDE_CODE_TMPDIR` is still declared in `.claude/settings.json` so tools and
hooks agree with the harness when it *is* set. `workflows._literal()` discards a
value still containing `$`, so an unexpanded `${CLAUDE_PROJECT_DIR}` is treated
as a misconfiguration rather than resolved into a directory named after the
variable.

## 4. Evidence, and what it does not cover

| Claim | Evidence | Strength |
|---|---|---|
| Redirected files are inside the repo | the same file read through both paths returns identical bytes | **direct** |
| A new session is redirected at start | session `16804381…`: all five kinds reported `created` / `linked` | **direct** |
| A resumed session is refused | session `3f4a4bbb…`: three kinds `refused: holds N item(s)` | **direct** |
| Settings `env` does not move the temp root | restarted with it set; temp root unchanged | **direct** |
| SC-1 moves the temp root | **none** | **absent** |

**SC-1 has never been exercised.** The basis for it is that Claude Code names
`CLAUDE_CODE_TMPDIR` in its own recovery message — a program does not tell you
to set a variable it does not read. That is a reasonable basis and it is not
evidence. Until a session starts through `bin/claude-here` and reports its
scratchpad inside the checkout, this control is **designed, not in force**, and
the repository's actual posture is SC-2: contained by redirection.

Stating that plainly is the point. The provenance chain has the same shape of
gap at stage 05 and `docs/cicd/provenance.md` says so; a control catalogue that
marks its untested controls as working is worth less than no catalogue.

## 5. Incident — the control broke the thing it protected

On 2026-09-24 a session adopted its own `tasks/` directory mid-flight while
testing SC-2. Claude Code records that directory at session start and checks it
on every tool call; finding it replaced by a symlink it refused to write any
further tool output. **The session could not run a single command for the rest
of its life** — including the command that would have undone the change.

Three things came out of it, and they are the reason SC-6 exists:

1. A corrective control that runs inside the thing it corrects can remove its
   own ability to correct. SC-2 now refuses `tasks/` whenever the session owning
   it is live, and only `pf workflow link --adopt` — run by a person, between
   sessions — may move it.
2. Recovery required a command from outside the harness. Any control of this
   kind needs an out-of-band recovery path, written down before it is needed.
3. It is an argument for SC-1 over SC-2 on its own merits: a directory created
   in the right place is never moved, so it can never be moved at the wrong
   moment.

On 2026-09-25 it recurred in a *new* session. SC-6 as first written held back
only a populated `tasks/`, on the premise that linking an empty one "before the
harness first looks" was safe. There is no such moment: the harness has noted
the directory before SessionStart fires, so the hook's link of an empty
`tasks/` cost the session every command from its first. SC-6 now leaves
`tasks/` alone under a live session whether it is empty or not; only SC-1
(`just claude`) keeps it in the checkout.

## 6. Residual risk — accepted

- **`git clean -xdf` removes `.tmp/`**, including a live session's state. Accepted:
  the alternative is a directory outside the repo, which is the thing this
  control exists to prevent.
- **The Claude Code folder is copied, not linked.** The transcript, subagent
  transcripts and tool results stay at `~/.claude/projects/<slug>/<session>/`
  and a copy is taken. Deliberate: the retention sweep recurses with `readdir`,
  which follows a symlinked directory, so linking those would put repo history
  behind a 30-day delete. The copy is the containment; the original is the
  harness's own.
- **Non-harness temp files** — `dbt`, `duckdb`, `uv` and anything else honouring
  `TMPDIR` — are out of scope. Redirecting `TMPDIR` repo-wide would bring them
  in, and would break a fresh clone where `.tmp/` does not yet exist. Not taken.
- **SC-5 is off.** A SessionStart hook that refuses to start is the only true
  hard stop available, and an untested one can make every session in the
  repository unstartable. Turning it on is a policy decision, taken once SC-1
  is verified.

## 7. What the owner has to decide

1. **Verify SC-1** — start one session through `just claude` and read the
   scratchpad path in its environment preamble. Until then §4 stands.
2. **Then decide on SC-5.** With SC-1 verified, fail-closed costs nothing in
   normal operation. Without it, fail-closed would refuse every session.
3. **Register the control.** This page is prose. The repository's own mechanism
   for a named control is a `controls:` entry in `policy.yaml` with an
   `enforced_by` that `pf air coverage` can resolve — an entry that resolves to
   nothing reports as failing, which is the point. This control is not
   registered; doing so is the step that makes it auditable by machine rather
   than by reading.

---

*Operational detail: [`docs/CLAUDE-CODE.md`](CLAUDE-CODE.md) · decision record:
[`docs/GOVERNANCE.md`](GOVERNANCE.md) · control catalogue:
[`docs/AIR.md`](AIR.md)*
