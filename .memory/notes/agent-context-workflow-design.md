---
name: agent-context-workflow-design
description: 'agent-context.yml checks every PR (no path filter): pf context/memory/test/arch hard, pf tokens advisory until the jaffle-shop card is decided; auto-refresh needs AGENT_CONTEXT_TOKEN since GITHUB_TOKEN pushes never re-trigger checks'
type: project
status: active
agent: claude-code
---

**Why:** `platform-tests.yml` only runs on platform paths, so a PR that adds a
model and a note under `groups/` never had its memory index, test index or
repo map checked; and nothing at all checked the hand-written layer — that
`GEMINI.md` still imports `AGENTS.md`, that a `§5` pointer survives a
renumbering, that every module has the README that makes `.memory/notes/`
exist in git. `pf tokens` is advisory there (`continue-on-error`) because the
jaffle-shop card is 1585/1500 on main and fixing that is a person's decision;
a hard step would redden every PR until it is made.

**How to apply:** stale → `uv run pf context refresh` (memory index, READMEs,
test index, repo map) and commit; disagreeing entry points → read the
`pf context check` line, it names the file and the missing mention or the
dangling section. The `refresh` job pushes that commit itself only with an
`AGENT_CONTEXT_TOKEN` fine-grained PAT (`contents: write`): a push made with
`GITHUB_TOKEN` never starts another workflow run, so the fixed commit would
sit on the PR with no checks and a required check would wait forever. It
never touches a fork's branch or `main`. Once the card decision is made,
delete `continue-on-error` on the tokens step. A local session pushing to
the same branch right after the bot commits gets a non-fast-forward: pull
first.
