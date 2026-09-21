---
name: artifacts-live-in-docs
description: Every artifact published for the data-platform repo must also be saved as a standalone file in its docs/ folder
type: feedback
status: active
agent: claude-code
---

When publishing an Artifact about the `Atomz-org/data-platform` repo, always also
save a self-contained copy into that repo's `docs/` folder. Do this without being
asked — the artifact link alone is not an acceptable delivery for this repo.

**Why:** artifacts are private to the owner's Claude account, so the claude.ai URL
does not open in a signed-out browser, on another account, or behind a network that
blocks claude.ai — the user hit exactly that on 2026-09-20 with
`Merge-Time Governance Path`. A file in `docs/` opens from disk with no login, is
reviewable in a PR, and is versioned with the code it describes.

**How to apply:**
- Author the page as usual for the Artifact tool (no `<!doctype>`/`<html>`/`<head>`
  wrapper — the service adds one), then write the `docs/` copy with that wrapper
  added: the artifact's `<title>`, `<link>` and `<style>` go inside `<head>`, and
  the content div onward inside `<body>`.
- Name it lowercase-kebab `.html` to match the existing `docs/kg-atlas.html`.
  Prose documents in `docs/` are `UPPERCASE.md` instead.
- External Google Fonts links are fine; they degrade to the fallback stack offline.
  Everything else must be inlined, since a local file has no CDN allowlist to rely on.
- After adding anything to `docs/`, run `pf check`, `pf arch check` and `pf tokens`
  — a new hand-written doc passes all three, but a generated path would not.
  Note `pf tokens` budgets only the cards, both `CLAUDE.md` levels, `ROUTING.md`
  and `VENDOR-CARD.md`, so a new `docs/` file is not budgeted.
- Leave it untracked and offer to commit; do not commit unless asked.

Existing files placed this way: `docs/AI-GOVERNANCE-ARCHITECTURE.md`,
`docs/merge-governance.html`. See [[open-pr-stacks-2026-09]].
