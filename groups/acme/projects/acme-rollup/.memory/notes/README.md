# Session memory

One lesson per file, one line in the frontmatter `description`, the why and
the how-to-apply in the body. Written mid-task by whichever agent learned it —
Claude Code, Copilot, a person — so the next session, whichever tool runs it,
does not pay for the same lesson twice.

    uv run pf memory show            # what applies here, one line each
    uv run pf memory show --full     # with bodies
    uv run pf memory add <module> <name> "<one line>" --body-file notes.md

`add` writes the file into the right module and regenerates `.memory/MEMORY.md`,
the index CI checks (`pf memory check`). Never hand-edit the index; edit the
note and run `pf memory index`.

Put a lesson here only if it is about *this* module. A lesson that is true of
every project belongs in `platform/.memory/notes/`; one about git, CI or the
session layer belongs at the repo root. A sister project's lessons are not
readable from here, by design.

Write it dense. The `description` is one keyword-rich line, not a sentence
with a preamble; the body is why and how-to-apply, and nothing else. A new
dependency or constraint you introduced is exactly what belongs here — say
what it rules out. What is *in progress* does not belong here: that is the
branch and its pull request.

Promotion into a `CLAUDE.md` (always loaded, budgeted) is a reviewed, human
step — that promotion is what makes the platform compound instead of
accumulating notes nobody reads.
