# LLM backends — Nativ, FreeLLMAPI and Claude Pro

Status: research, 2026-09-07. Nothing here is built. The question is where each
of three backends could plug into this platform, and what each costs in money,
quality, terms and governance compared with the others. Every non-obvious
claim carries a source in §9; anything the sources could not confirm is marked
*unconfirmed*.

## 1. The four places this platform calls a model

Before comparing backends, be precise about what would consume them. There are
four call sites, and they differ in who pays, what data they see, and how
tightly they are governed.

| # | call site | today | auth | what the prompt contains | governed by |
|---|---|---|---|---|---|
| A | `pf commit` / `pf git-doctor` (`platform/src/pf/committer.py`, `gitdoctor.py`) | local OpenAI-compatible endpoint, `http://127.0.0.1:8080/v1/chat/completions`, MLX Qwen 3.5 (9B configured, 4B actually cached); fallback headless `claude -p --model haiku` | none locally; the user's own login for the fallback | file list + ≤400 chars of diff per file, ≤12,000 chars total; the commit style file | `llm-commits-are-recorded-and-attributed`, `commit-plans-are-validated-not-trusted`, provenance action per apply |
| B | `pf.agents.base` loops (`freshness_triage` Haiku 4.5, `test_failure_triage` Opus 5, `metric_gap_proposer` Sonnet 5) | Anthropic SDK direct | `ANTHROPIC_API_KEY` or `~/.config/anthropic/credentials` | monitor rows, dbt lineage, MetricFlow grammar. **Can contain warehouse-derived values** | `model-routing-is-declared` (AIR-PREV-10), 200k tokens/day cap in `LOOP.md`, circuit breaker |
| C | CI review: `claude-review.yml` today, `pr-agent.yml` planned (`docs/PR-AGENT.md`) | `anthropics/claude-code-action` on the API key; pr-agent via litellm | repository secret `ANTHROPIC_API_KEY` | the PR diff, `pf gate` / `pf check` output, router rules | `high-impact-actions-need-a-human`, `review-artifacts-exclude-pii` (AIR-DET-1) |
| D | the interactive Claude Code session (this one) | Claude Code under the user's subscription | OAuth login | everything the session reads | hooks (`pre_tool_use.py`), `gate.yaml`, power-tools |

Two seams already exist and matter for what follows:

- **A is provider-agnostic by construction.** `PF_COMMIT_LLM_URL` and
  `PF_COMMIT_LLM_MODEL` point at any OpenAI-compatible chat endpoint; the client
  is raw `urllib`, no SDK. Anything that speaks `/v1/chat/completions` is a
  drop-in with no code change.
- **B and D are Anthropic-shaped.** The SDK honours `ANTHROPIC_BASE_URL`, so a
  server exposing the Anthropic Messages API can stand in, but `pf.agents.models`
  only knows the models in its registry and `spec()` raises for anything else.
  A substitute model needs a `ModelSpec` row before B will route to it.

## 2. Nativ

### 2.1 What it is

A native macOS app (Swift/SwiftUI) wrapping an embedded Python `mlx-vlm` server.
Chat UI, model manager, metrics dashboard, and a local API server on
`127.0.0.1:8080`. Author Prince Canuma (Blaizzy), author of mlx-vlm and
mlx-audio. MIT, free, no accounts. First release 2026-07-20; v0.3.7 shipped
today (2026-09-07), thirteen tags in seven weeks, about 1,400 stars.

| fact | value |
|---|---|
| platform | Apple silicon and **macOS 26 or newer** only. No Sequoia, no Intel, no Linux |
| install | `brew install --cask nativ` or DMG; Sparkle auto-update |
| engine | mlx-vlm ≥ 0.6.10, mlx ≥ 0.32; mlx-lm was removed from the bundle in 0.3.7 |
| API | OpenAI `/v1/chat/completions`, `/v1/responses`, `/v1/models`, embeddings, images, audio; **Anthropic `/v1/messages` plus token counting**; `/health`, `/metrics`; bearer key, default `nativ` |
| features | streaming, tool calling, JSON-schema structured output (llguidance), per-model thinking toggle and budget, KV-cache quantisation, speculative decoding with a draft model, prefix caching |
| models | whatever the pinned mlx-vlm loads from the HF cache; curated list includes GLM-5.3-Flash, Gemma 4 E2B, Cohere North Mini Code, LFM2.5-VL. Qwen variants have open load-failure issues (#338, #423) |
| Claude Code | official recipe: `ANTHROPIC_BASE_URL=http://127.0.0.1:8080`, `ANTHROPIC_AUTH_TOKEN=nativ`, `ANTHROPIC_MODEL=<id>`, `ANTHROPIC_SMALL_FAST_MODEL=<id>` |
| MCP | Nativ is an MCP *host* for its own chat; MCP tools are not exposed to API clients |

### 2.2 Measured performance

There is no Nativ-vs-Ollama-vs-LM Studio benchmark; the author lists one as
"not started". The only third-party numbers found:

| setup | decode | prefill | note |
|---|---|---|---|
| M4 Max 128 GB, Qwen3.6-27B-NVFP4 | 15.1 tok/s | 210 tok/s | a ~16K-token agent turn took 108 s, 75 s of it prefill |
| issue #354, prefix cache **on**, `prefixCacheBlocks=9600` | | | a 100k-token Claude Code turn fell from 233 s to 1.7 s |
| issue #354, defaults | | | six requests averaged 682 s |

The second and third rows are the whole story for agent use: **prefix caching
is off by default, not in the UI, and the default pool is 32,768 tokens.** It
has to be enabled through the model-config environment for any agent-shaped
workload to be usable.

### 2.3 Where it fits here

| call site | fit | what changes | what does not work |
|---|---|---|---|
| A `pf commit` | **drop-in.** Same host, same port, same route as `DEFAULT_URL`. Set `PF_COMMIT_LLM_MODEL` to the Nativ model id and, if a key is set, add the bearer header (one line in `committer.py`, the client sends none today) | Nothing else. Thinking is disabled per model in Nativ's config instead of the `--chat-template-args` flag the memory note records for `mlx_lm.server` |
| Pre-PR `pf review` (planned) | **good.** pr-agent via litellm `openai/<model>` with `api_base=http://127.0.0.1:8080/v1` | Needs a model with tool calling and enough context for a diff; the 16K-turn-in-108s number says small PRs only |
| D offline session | **possible.** The Anthropic shim lets Claude Code run against Nativ when offline or when the Pro limit is hit | Quality is the local model's, not Claude's. `/v1/models` does not report context length; the session's hooks and MCP servers still work because they are Claude Code's, not Nativ's |
| B loops | **dev and eval only.** Point `ANTHROPIC_BASE_URL` at Nativ, add a `ModelSpec` row; `models.py` already strips unsupported parameters (effort, cache_control) per model, which is exactly the seam a shim needs | The loops' value is Opus-grade root-causing over lineage; a local model changes the answer, not just the bill. Run it to build evals, not to replace the routing table |
| C CI | **no.** CI runners are Linux | |

### 2.4 Risks

- Seven weeks old, one developer, macOS 26 only. The `mlx_lm.server` path in
  the committer is the fallback if Nativ regresses; keep both documented.
- Port 8080 is also llama.cpp's default and is hard-coded as the committer's
  default. That is convenient today and a collision tomorrow; the env var
  resolves it.
- Model support is whatever mlx-vlm supports at the pinned version; Qwen, the
  family the committer was tuned on, has open load failures.

## 3. FreeLLMAPI

### 3.1 What it is

A self-hosted TypeScript router that puts 34 free-tier LLM providers behind one
OpenAI-compatible endpoint on `localhost:3001`, with a dashboard, a CLI, and
desktop builds. Bring-your-own keys, AES-encrypted in SQLite; clients use one
`freellmapi-…` bearer token. Thompson-sampling routing across providers with
quota tracking (RPM/RPD/TPM/TPD per key), cooldown ladders on 429, sticky
sessions, optional response cache and prompt compression. MIT router; the live
model catalogue is a paid feed ($19/yr) and free installs see models **30 days
late**. Created 2026-04-21, v0.9.8 today, about 24,800 stars, one dominant
maintainer.

| fact | value |
|---|---|
| endpoints | `/v1/chat/completions`, `/v1/embeddings`, `/v1/models`, **Anthropic `/v1/messages`**, `/v1/responses`, Gemini-native, Ollama emulation, `/mcp` |
| model names | `auto`, `auto:fast`, `auto:smart`, `auto:reliable`, `auto:balanced`, `auto:<chain>`, or an explicit catalogue id. No `model@provider` pin syntax |
| attribution | response headers `X-Routed-Via: <platform>/<model>`, `X-Fallback-Trail` |
| Claude Code | `ANTHROPIC_BASE_URL=http://localhost:3001`, key `freellmapi-…`; `npx freellmapi setup-claude` |
| providers of note | Groq, Google AI Studio, OpenRouter, Cerebras (trial only now), Mistral, Cloudflare, NVIDIA NIM, HF Router, Ollama Cloud, plus ~25 smaller gateways. GitHub Models removed (retired 2026-07-30); SambaNova retired |
| stated purpose | "personal experimentation and learning, not production… swap in a paid API before you ship" |

### 3.2 The terms problem, in the project's own words

FreeLLMAPI ships a per-provider ToS review (May 2026). Cohere: **avoid**.
Google Gemini, NVIDIA NIM, GitHub Models, Z.ai: **caution**. Cloudflare:
ambiguous. Groq, Cerebras, Mistral, OpenRouter, Zhipu, Ollama Cloud, OVH, AI
Horde: likely OK. The project's principles are one account per provider, no
resale, no sharing with other humans, no paid-production backend. It does not
address whether providers train on prompts; an independent review notes that
Google's unpaid Gemini API uses content to improve products with possible human
review, while Groq contractually prohibits training.

Open issue #1170 is directly relevant to any Anthropic-shaped client: the
`/v1/messages` route ignores `auto:<chain>` and routes over the whole active
pool while **echoing the requested model id back**. A caller cannot trust the
`model` field in the response; only the `X-Routed-Via` header says where the
prompt went.

### 3.3 Where it fits here

| call site | fit | why |
|---|---|---|
| A `pf commit` | **technically trivial, do not.** `PF_COMMIT_LLM_URL=http://localhost:3001/v1/chat/completions` works unchanged | The prompt carries diff text from every project. Business logic leaving the machine to a rotating set of free tiers, some of which train on it, is the opposite of the isolation rule. And a commit plan from `auto` cannot be attributed to a pinned model, which `llm-commits-are-recorded-and-attributed` requires |
| B loops | **no.** | Warehouse-derived values in prompts, `secrets-never-in-context` (AIR-PREV-23), `review-artifacts-exclude-pii` (AIR-DET-1), and `model-routing-is-declared` (AIR-PREV-10) all fail on a router whose defining feature is not telling you the model in advance |
| C CI | **no.** | Same, plus "personal use only, don't expose publicly" and per-IP limits on a shared runner |
| D session | **no.** | Routing a Claude Code session through it is exactly the "third-party harness intermediating credentials" pattern, and the quality is not Claude's |
| **evals** | **yes, narrowly.** As a source of candidate open models when choosing the local tier's model, or for the `pf models` bench, on synthetic prompts from `evals/`, never on real diffs or warehouse data | The value of 300+ free endpoints is breadth for comparison, not a production path |

If it is used for evals, record `X-Routed-Via` in the eval row so the result is
attributable, and run it with `CATALOG_SYNC_DISABLED=1` if the phone-home
matters.

## 4. Claude Pro

All figures from Anthropic pages fetched 2026-09-07 unless marked.

### 4.1 What $20 buys

| item | Pro | note |
|---|---|---|
| price | $20/mo, $17/mo annual | Max 5x $100, Max 20x $200, Team Standard $25/seat |
| Claude Code | included; one shared limit with chat, IDE, Cowork | default model **Sonnet 5**; Opus 5 available at 200K; Opus 1M and Sonnet 4.6 1M need usage credits |
| Fable 5 / 5.1 | **not included** on Pro; pay-as-you-go usage credits | the free 50% promotion ended 2026-07-19 |
| limits | 5-hour session window, "at least 5x free"; a weekly cap across all models, plus per-family Opus and Sonnet caps | no token or message numbers are published anywhere official |
| upcoming | +25% to standard weekly limits from 2026-09-14, replacing the temporary +50% boost since May: **net −17% versus today** | *unconfirmed on official pages*; announced on X, reported by BleepingComputer |
| usage credits | prepaid, billed at standard API rates, kick in after the session limit, $2,000/day redemption cap | cache TTL drops from 1h to 5min once on credits |
| API credit | **none.** "The Pro plan does not include API usage through the Claude Console" | |

### 4.2 What the terms allow for automation

This is the part that decides whether Pro can back call sites A–C.

- **Permitted, and drawing from the subscription:** `claude -p`, the Agent SDK,
  and the Claude Code GitHub Actions integration, authenticated through the
  subscriber's own login. Anthropic's 2026-06-15 update says "nothing has
  changed" and that the planned split into a separate monthly Agent SDK credit
  ($20 for Pro, at API rates) is **paused**, not cancelled, with notice promised
  before any change.
- **Bounded by:** "advertised usage limits… assume ordinary, individual usage of
  Claude Code and the Agent SDK", and Anthropic "may limit your usage in other
  ways… at our discretion".
- **Not permitted:** routing requests through Pro credentials on behalf of other
  users, intermediating OAuth tokens outside Anthropic's own sign-in flow (the
  opencode / claude-code-router pattern), sharing the account. Consumer terms
  bar "automated or non-human means… except… via an Anthropic API Key or where
  we otherwise explicitly permit it", and the Agent SDK article is that
  explicit permission.
- **Data:** consumer plans have a training opt-in toggle that covers Claude
  Code; retention 30 days with it off, up to five years de-identified with it
  on. API and Team/Enterprise are under commercial terms: no training, 30-day
  deletion, ZDR for qualified orgs (Fable excluded).

So for this repo, with one human: the `claude -p haiku` fallback in the
committer (A) and this session (D) are squarely "ordinary, individual usage".
A GitHub Action authenticated with the user's own OAuth token is covered by the
June 15 article, but it is the user's personal token in a repository secret, the
cap is discretionary, and the paused credit split would turn it into a $20/month
API budget the day it resumes. CI belongs on an API key.

### 4.3 API prices, for the cost model

| model | in $/MTok | cache read | out $/MTok | batch in / out |
|---|---|---|---|---|
| Fable 5.1 | 10 | 0.25 | 50 | 5 / 25 |
| Opus 5 | 5 | 0.50 | 25 | 2.50 / 12.50 |
| Sonnet 5 | 2 | 0.20 | 10 | 1 / 5 |
| Haiku 4.5 | 1 | 0.10 | 5 | 0.50 / 2.50 |

Sonnet 5's $2/$10 introductory price is now permanent. Opus 4.7+ and Fable
tokenise about 30% heavier than Sonnet 4.6 and earlier.

## 5. Cost model against this platform's own budgets

The platform already states its budgets, so the comparison can be concrete.

**Loops (B), at the `LOOP.md` cap of 200,000 tokens/day, assuming 80% input.**

| routed entirely to | per day | per month |
|---|---|---|
| Haiku 4.5 | $0.36 | $11 |
| Sonnet 5 | $0.72 | $22 |
| Opus 5 | $1.80 | $54 |
| the declared mix (Haiku triage at high cadence, Sonnet daily, Opus on failure) | ≈ $0.50–0.90 | ≈ $15–27 |

The full loop budget on the API costs about one Pro subscription. Pro cannot
back it anyway (§4.2: not ordinary individual usage, and no API credit), so the
comparison is Pro-for-the-human plus API-for-the-loops, versus API for both.

**CI review (C), label-gated.** A review with the diff plus `pf gate` context
runs roughly 30–60K input and 3–5K output tokens.

| model | per run | 40 runs/month |
|---|---|---|
| Sonnet 5 | $0.09–0.17 | $4–7 |
| Opus 5 | $0.23–0.43 | $9–17 |
| pr-agent small-PR routing to Haiku | $0.04–0.08 | $2–3 |

**Committer (A).** About 3–4K tokens in, 1–2K out per plan. Twenty commits a
day is ≈100K tokens/day: $0.10/day on Haiku via the API, or $0 and no network
on the local tier. The local tier's cost is wall-clock: the memory note records
prefill at ~7 tok/s under memory pressure, which is why `PF_COMMIT_LLM_TIMEOUT`
is 1800.

**FreeLLMAPI.** $0 in money. The cost is the ToS exposure in §3.2, the data
exposure, and the 30-day catalogue lag; none of those appear on an invoice.

## 6. Comparison

| dimension | Nativ (local MLX) | FreeLLMAPI (free tiers) | Claude Pro (subscription) | Anthropic API (reference) |
|---|---|---|---|---|
| money | $0 after hardware | $0; $19/yr for a current catalogue | $20/mo flat | per token, §4.3 |
| model quality | open 4–30B models; good enough for closed-menu tasks (commit plans, git repair), not for lineage reasoning | same open models, sometimes larger, routed unpredictably | Sonnet 5 default, Opus 5 available, Fable on credits | any, pinned |
| latency | seconds to minutes; prefill-bound; prefix cache is the lever | provider-dependent; capacity drops late UTC | interactive | interactive |
| offline | yes | no | no | no |
| data leaves the machine | never | to whichever provider won the route | to Anthropic under consumer terms (training opt-in) | to Anthropic under commercial terms (no training) |
| model pinning (AIR-PREV-10) | yes, one local id | **no**: `auto` by design, and `/v1/messages` echoes the wrong id (#1170) | yes | yes |
| attribution in provenance | model id + local | only via `X-Routed-Via` header | model id | model id |
| PII / secrets policy (AIR-DET-1, AIR-PREV-23) | satisfied trivially | violated for any real prompt | acceptable with training off | acceptable |
| automation allowed | yes | "personal experimentation", per-provider caution/avoid | `claude -p` / SDK / GH Action under own login; discretionary caps; credit split paused not cancelled | yes, that is what it is for |
| CI | no (Linux runners) | no | own OAuth token only; not recommended | yes |
| reliability | one developer, seven weeks, macOS 26 only | one maintainer, providers retire (GitHub Models, SambaNova, Cerebras free tier) | Anthropic; limits changing 2026-09-14 | Anthropic |
| rate ceiling | hardware | per-provider RPM/RPD, cooldown ladders | 5-hour window + weekly cap, unpublished | org rate limits |

## 7. Recommendation: three tiers, one seam each

**Tier 0, local, for anything that sees repository or warehouse content and
does not need frontier reasoning.** Call site A today; the pre-PR `pf review`
when it exists; evals. Nativ is the better server than `mlx_lm.server` for
this once prefix caching is turned on, because of the metrics, the model
manager, the draft-model speculative decoding, and the Anthropic shim that
makes Claude Code itself usable offline. It is also a drop-in on the exact
default URL the committer already uses. Adopt it as *the* local server but keep
`mlx_lm.server` documented as the fallback, because the app is seven weeks old
and requires macOS 26. Concretely:

1. Enable prefix caching and a pool sized for the committer's 12K-char prompt
   plus the style file; record the config in `docs/COMMITTER.md`.
2. Add optional bearer auth to the committer's client (one header, read from
   `PF_COMMIT_LLM_KEY`).
3. Pin the model id in `PF_COMMIT_LLM_MODEL` and keep `enable_thinking` off; a
   thinking model burns the plan budget, as the memory note records.
4. Add a `pf models bench` row so the local model's plan quality is measured
   against `evals/`, not assumed.

**Tier 1, Claude Pro, for the human.** Call site D, and the `claude -p`
fallback in A. This is what the subscription is for and what its terms cover.
Do not put the OAuth token in CI; do not route it through a third-party
harness. Watch two dates: the 2026-09-14 limit change, and whatever resumes the
paused Agent SDK credit split. If the session keeps hitting the Opus family
cap, Max 5x at $100 is the sanctioned upgrade, not a free-tier router.

**Tier 2, the API, for everything automated and governed.** Call sites B and
C. Pinned model ids, commercial data terms, provenance attribution by model, an
invoice that `output_run_cost` and `pf.agents.base` can reconcile. At this
repo's declared budgets that is roughly $15–30/month for loops and under $10
for label-gated review: about the price of the subscription, for the half of
the work the subscription is not allowed to do.

**FreeLLMAPI: not on any governed path.** Its honest use here is as an eval
harness for choosing Tier 0's model, on synthetic prompts, with the routing
header recorded. The features that make it attractive (automatic failover
across anonymous free tiers) are the features that make it incompatible with
`model-routing-is-declared`, `secrets-never-in-context`, and the sister
isolation rule.

## 8. Open questions

- Nativ's `/v1/messages` shim: does it accept and ignore `cache_control`,
  `output_config.effort` and adaptive `thinking`, or reject them? `models.py`
  strips per model, so a `ModelSpec` row with everything off is the safe start.
  Test before pointing `pf.agents` at it even for evals.
- Whether Nativ exposes context length anywhere an agent can read it;
  `/v1/models` does not, and DevoxxGenie falls back to 8,000.
- The Pro weekly numbers after 2026-09-14, once a support page states them.
- Whether usage credits cover Agent SDK traffic; the official page does not
  say. Matters only if CI were ever put on the subscription, which §7 advises
  against.

## 9. Sources

Nativ: https://blaizzy.github.io/nativ/ · https://github.com/Blaizzy/nativ ·
`Docs/features/{developer,integrations,models,chat}.md` in that repo ·
https://github.com/Blaizzy/nativ/issues/354 · issues/123 (roadmap) ·
https://simonwillison.net/2026/Jul/21/nativ/ ·
https://genie.devoxx.com/blog/nativ-local-mlx-apple-silicon

FreeLLMAPI: https://github.com/tashfeenahmed/freellmapi (README, `docs/en/`
providers, api, fallback, clients, architecture) · https://freellmapi.co ·
https://freellmapi.co/privacy · https://freellmapi.co/terms ·
https://github.com/tashfeenahmed/freellmapi/issues/1170 · issues/549 ·
https://artificiallyintimidating.com/p/freellmapi ·
https://betterstack.com/community/guides/ai/freellmapi/

Claude Pro and API: https://claude.com/pricing ·
https://support.claude.com/en/articles/8325606 (Pro) · 11049741 (Max) ·
9266767 (Team) · 15424964 (Fable on your plan) · 11647753 (usage limits) ·
11145838 (Claude Code with Pro/Max) · 15036540 (Agent SDK with your plan,
2026-06-15) · 12429409 (usage credits) ·
https://code.claude.com/docs/en/legal-and-compliance ·
https://code.claude.com/docs/en/model-config · /costs · /data-usage ·
https://platform.claude.com/docs/en/about-claude/pricing ·
https://www.anthropic.com/legal/consumer-terms ·
https://privacy.claude.com/en/articles/10023548 · 10023580 · 7996866 ·
https://www.bleepingcomputer.com/news/artificial-intelligence/anthropic-is-cutting-claude-codes-current-weekly-limits-by-17-percent/
(secondary, 2026-08-29) · https://zed.dev/blog/anthropic-subscription-changes
(secondary)

Repository: `platform/src/pf/committer.py`, `platform/src/pf/agents/base.py`,
`platform/src/pf/agents/models.py`, `.github/workflows/claude-review.yml`,
`LOOP.md`, `docs/COMMITTER.md`, `docs/PR-AGENT.md`.
