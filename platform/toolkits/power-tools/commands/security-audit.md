---
name: security-audit
description: Audit the active project for exposed secrets, gate holes and PII leaking into committed review artefacts.
disable-model-invocation: "yes"
---

# Security audit

Scope: `$ARGUMENTS` if given (e.g. `secrets`, `gate`, `pii`, a path), otherwise
the whole active project. Never leave the active project — a sister's exposure
is a finding for a session opened there.

## 1. Secrets at rest

```bash
uv run pf check                     # flags any denied path git is tracking
git ls-files | grep -E '\.env|secrets\.toml|credentials|_key|_secret' || echo "clean"
```

Then call `secrets_view_redacted` (MCP) rather than reading `.dlt/secrets.toml`
yourself — it returns the shape without the values, which is all an audit needs.

A finding here is: a value committed, **or** a key present in `.dlt/secrets.toml`
that has no counterpart in `.env.example`, which means a fresh clone silently
runs without it.

## 2. Gate coverage — the holes, not the rules

`gate.yaml` plus the generated `gate.capabilities.yaml` are the policy. The
question is not "what does it deny" but "what does it fail to deny".

```bash
uv run pf gate --paths "$(git diff --cached --name-only | tr '\n' ',')"
```

Check each in turn, and report the ones that fail:
- every artefact a generator writes is on the `denylist` (drift otherwise
  re-appears as a hand edit that the next regeneration discards silently),
- every entry in `denylist_except` is a deliberate, still-true exception,
- `platform_denylist` still covers shared infra a project session must not touch.

## 3. PII in committed review artefacts

This repo deliberately commits `transform/recce_state.json` — and `value_diff`
checks write **compared rows** into it. That is only safe while PII columns stay
excluded from those checks (`pf.tools.recce`). Verify it, every time:

```bash
uv run python - <<'PY'
import json, pathlib
for p in pathlib.Path('.').rglob('transform/recce_state.json'):
    d = json.loads(p.read_text())
    print(p, '→ checks:', len(d.get('checks', [])))
PY
```

For any `value_diff` check, confirm its column list contains no name matching
email / phone / name / address / dob / ssn / iban / card. One that does is a
**critical** finding: the data is already in git history.

Same question for `mdl/mdl.json` and `catalog/openmetadata.json` — both are
committed contracts. They should carry column *names and types*, never values,
and never a credential (the ingestion workflow holds an env-var reference only).

## 4. Query surface

- `execute_sql_query` and `dbt_build` reach the warehouse. Confirm the project's
  `.claude/settings.json` `permissions.deny` blocks reads of `.env*`,
  `**/secrets.toml` and `**/credentials/**`.
- Confirm no model or Evidence page interpolates a value that arrived from an
  untrusted source into raw SQL.
- Confirm logging never writes a row value — `pf.obs` records counts and
  verdicts, not data.

## 5. Report

Prioritised list. For each finding: **severity** (Critical / High / Medium /
Low), what is exposed, the blast radius (who can already see it — is it in git
history?), and the concrete remediation. Lead with anything already committed:
rotation, not deletion, is the fix for that class.

---

## Generic checklist (retained from the source guide)

Where the sections above do not apply, fall back to these:

**Authentication & authorization** — JWT handling, session management, RBAC.
**Input validation** — SQL injection, XSS, API input sanitisation.
**Data protection** — hardcoded secrets and API keys, PII handling, encryption
at rest, secure logging (no sensitive data in logs), environment variable usage,
CORS and CSP headers.

**Output format** — a prioritised list of findings, each with severity level,
description of the vulnerability, potential impact, recommended remediation, and
a code example where applicable.
