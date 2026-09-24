# Devcontainer — the boundary the policy files cannot be

`gate.yaml`, `platform/hooks/pre_tool_use.py` and the permission lists in
`.claude/settings.json` bound what an agent may write **inside this
repository**. Until this container existed, nothing bounded what the agent
*process* could reach outside it — the host home directory, `~/.ssh`,
`~/.aws`, every other checkout on the machine.

That is a real difference in kind. Everything in the policy layer is a rule an
agent is asked to respect and that a hook tries to enforce; a container is a
boundary that does not depend on the agent's cooperation at all.

## What it does give you

- **Filesystem.** Only this repository is mounted, at `/workspace`. No host
  home, no credential files, no sibling repositories.
- **A non-root user** (`platform`), `--cap-drop ALL` and `no-new-privileges`,
  so an escape is not automatically a root escape.
- **A reproducible toolchain.** Python 3.12, `uv sync --frozen`, and
  `pf install-hook` run on create — git does not clone `.git/hooks`, and the
  commit gate is where most of this repo's rules actually run.

## What it does not give you

**Network egress is not restricted.** A process in this container can still
reach the internet. Constraining that needs an egress proxy or a firewall on
the container network, and neither is set up here. If you are running an
untrusted agent, this container is not sufficient on its own — say so rather
than assuming the name implies it.

It also does not protect against anything you mount into it. Do not add a
mount for host credentials. Pass a secret as an environment variable to the
one command that needs it.
