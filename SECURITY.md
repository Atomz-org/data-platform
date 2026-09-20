# Security Policy

## Supported versions

This project is pre-1.0; only the latest commit on `main` is supported with
security fixes.

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Report vulnerabilities privately by email to
**sureshswaminathan.96@gmail.com** with a description of the issue, steps to
reproduce, and any relevant logs or proof of concept. You should receive an
acknowledgement within 7 days.

Please give us a reasonable window to investigate and release a fix before any
public disclosure.

## Scope notes

- The platform records every agent action in a hash-chained provenance log
  (`provenance/`, see `docs/GOVERNANCE.md`). Findings that allow tampering
  with or bypassing that record are in scope and treated as high severity.
- Credentials are expected to live only in the environment (`.env`, dlt
  `secrets.toml`) — never in the repository. If you find a committed secret,
  report it privately as above.
