"""A local model — Qwen on mlx_lm.server or Ollama — driven by a harness that has hooks.

A model has no hooks; the harness driving it does. So a local model is not a
harness here, it is a *provider* for one, and it is gated exactly as that
harness is:

    OpenCode   `bin/agent-here opencode --local` — mlx_lm.server on :8080 (or
               Ollama on :11434 with PF_LOCAL_PROVIDER=ollama). This module
               contributes both providers to `.opencode/opencode.json`; listing
               them selects nothing, so the default model stays the person's.
    Codex      `bin/agent-here codex --local` — Ollama through `codex --oss`.
               Codex speaks only the Responses API, which mlx_lm.server does
               not serve, so mlx is OpenCode's route and Ollama is Codex's.

Qwen produces text and tool-call requests; the harness executes them, and its
hook — `agent_hook.py opencode|codex pre` — runs before each one. The verdict
does not depend on the model.
"""

from __future__ import annotations

from pf.harness import Harness
from pf.harnesses.base import Ctx, Spec

MLX_URL = "http://127.0.0.1:8080/v1"
MLX_MODEL = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
OLLAMA_URL = "http://127.0.0.1:11434/v1"
OLLAMA_MODEL = "qwen3-coder:30b"

PROVIDERS = {
    "mlx": {
        "npm": "@ai-sdk/openai-compatible",
        "name": "MLX (local)",
        "options": {"baseURL": MLX_URL},
        "models": {MLX_MODEL: {"name": "Qwen3 Coder 30B (MLX)"}},
    },
    "ollama": {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Ollama (local)",
        "options": {"baseURL": OLLAMA_URL},
        "models": {OLLAMA_MODEL: {"name": "Qwen3 Coder 30B (Ollama)"}},
    },
}


def _render(ctx: Ctx) -> dict[str, str]:
    return {}  # its configuration is the providers block OpenCode renders


SPEC = Spec(
    key="local",
    label="Local model",
    order=70,
    rows=(
        Harness(
            "Local model — Qwen on mlx or Ollama",
            "`bin/agent-here opencode --local` (mlx) · `bin/agent-here codex --local` (Ollama)",
            "as its harness",
            "as its harness",
            "pre-commit",
            "as its harness",
            "as its harness",
            "as its harness",
            "as its harness",
            "as its harness",
        ),
    ),
    render=_render,
    owner="Local model",
    providers=PROVIDERS,
    caveats=(
        "- **A local model** is gated by the harness driving it. mlx_lm.server speaks",
        "  Chat Completions only, so it goes through OpenCode; Codex speaks the Responses",
        "  API only, so its local route is Ollama. Another model id means editing",
        "  `pf.harnesses.local` and `pf context refresh` — OpenCode rejects a model its",
        "  config does not list.",
    ),
    sessions=(
        "bin/agent-here opencode --local      # Qwen on mlx_lm.server, :8080",
        "PF_LOCAL_PROVIDER=ollama bin/agent-here opencode --local   # Qwen on Ollama",
        "bin/agent-here codex --local         # Qwen on Ollama, via codex --oss",
    ),
)
