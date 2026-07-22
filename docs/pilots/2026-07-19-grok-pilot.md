# Grok Build CLI pilot (Phase 0) — 2026-07-19

Task: fg-c0104 (bm-grok-pilot-test). Spec: `.forge/specs/2026-07-19-provider-profiles.md`
§"Provider-specific enablement gates" (Grok clause) + §"Risks" (Grok/Antigravity gate).

Goal: primary-source evidence on (a) Grok Build CLI's non-interactive auth path and
(b) subscription rate-cap shape, so a human can review before any Grok enablement. This
task does **not** enable Grok — the picker stays closed regardless of findings below.

## Live probe result — CLI absent, LIVE half blocked on human install

Checked on this machine (Windows, this worktree's host):

- `shutil.which('grok')` (kernel's prior check): empty — confirmed again below.
- `where grok` (PowerShell/cmd PATH search): no match.
- `which grok` (Git Bash PATH search): `which: no grok in (...)` — full PATH dumped, no hit.
- `npm ls -g --depth=0`: lists `@codexstar/bug-hunter`, `@openai/codex`, `@shopify/cli`,
  `pnpm`, `skillui`, `vercel` — **no grok package**.
- No `.grok/` directory found under the user profile during this pass (not exhaustively
  searched beyond PATH + npm global list, per task scope — a full filesystem sweep was
  not run).

**Conclusion: Grok Build CLI is not installed on this machine.** Per the task brief, Forge
does not install provider CLIs (spec non-goal) — the LIVE half of this pilot (running
`grok --version`, an actual auth probe, observing real rate-limit headers/behavior) is
**blocked on a human installing the CLI**. Everything below is desk research against
primary sources only; none of it was verified by actually running the tool.

## Findings table

| # | Claim | Source | Status |
|---|---|---|---|
| 1 | Official CLI is `xai-org/grok-build` on GitHub (Apache 2.0), the source behind the `grok` command; docs live at docs.x.ai/build/overview | https://github.com/xai-org/grok-build ; https://docs.x.ai/build/overview | CONFIRMED (primary — official xAI GitHub org + docs.x.ai) |
| 2 | Non-interactive auth via env var: `export XAI_API_KEY="xai-..."` works "for non-browser environments" | https://docs.x.ai/build/overview ; https://docs.x.ai/build/enterprise | CONFIRMED (primary, docs.x.ai, fetched successfully) |
| 3 | `grok login --device-auth` is the documented method for "headless or remote environments" — device-code flow, distinct from the plain `XAI_API_KEY` env-var path | https://docs.x.ai/build/cli/reference | CONFIRMED (primary) — but see caveat below: device-code auth still requires a one-time interactive step (visiting a URL / entering a code) even though it doesn't need a local browser, so it is not equivalent to "zero human involvement" the way `XAI_API_KEY` is |
| 4 | Login/session state cached at `~/.grok/auth` (enterprise doc) and `~/.grok/sessions` (named sessions, per CLI reference doc) | https://docs.x.ai/build/enterprise ; https://docs.x.ai/build/cli/headless-scripting | CONFIRMED (primary) — two docs give two related-but-not-identical paths; not reconciled against each other or against a real install, flagged as a discrepancy for human review |
| 5 | Enterprise OIDC auth also available via `GROK_OIDC_ISSUER` / `GROK_OIDC_CLIENT_ID` env vars, with refresh-token auto-renewal | https://docs.x.ai/build/enterprise | CONFIRMED (primary) |
| 6 | Headless invocation shape: `grok -p "<prompt>" --output-format streaming-json` (also `plain`, `json`); `--no-auto-update` recommended in CI/scripts | https://docs.x.ai/build/cli/headless-scripting ; https://docs.x.ai/build/cli/reference | CONFIRMED (primary) — matches the spec's pinned shape (`grok -p` + `--output-format streaming-json`) |
| 7 | `--always-approve` (alias `--yolo`) exists and must be paired with `--sandbox <profile>` (`off`/`workspace`/`devbox`/`read-only`/`strict`) per third-party security guidance; `--effort`, `--max-turns`, `-m/--model` all exist as documented flags | https://docs.x.ai/build/cli/reference | CONFIRMED for flag existence (primary, docs.x.ai/build/cli/reference) — the specific "never pair `--always-approve` unpaired with `--sandbox`" *rule* itself is Forge's own policy (spec's workspace-sandbox-pairing rule), not an xAI-stated requirement; xAI's docs describe the flags but were not confirmed to mandate that pairing |
| 8 | Grok Build (CLI) usage is drawn from the same "weekly usage pool" xAI introduced (June 2026) that unifies Chat/Imagine/Voice/Build/API consumption for paid consumer tiers (SuperGrok, X Premium+, etc.) | https://docs.x.ai/grok/faq | CONFIRMED the pool exists and that "Build" is named as one of the pool's constituent products ("the usage breakdown includes API, Build, Chat, Imagine, Voice") — **UNCONFIRMED**: exact numeric caps per tier (messages/tokens/compute-$ per week for SuperGrok vs SuperGrok Heavy vs Premium+) — the FAQ describes the mechanism but states no numbers in the fetched content |
| 9 | On exhausting the weekly pool: "paid features will pause until your weekly limit resets"; free-tier Chat/Voice access continues on its own separate schedule; Extra Usage Credits purchasable (web only, not yet in-app on mobile) to continue past the cap | https://docs.x.ai/grok/faq | CONFIRMED (primary, verbatim quote fetched) |
| 10 | `grok-build-0.1` is listed on the xAI developer pricing page as a standard token-metered API model ($1.00–$2.00 / 1M input tokens depending on prompt length) — i.e., API-key-billed usage is pay-per-token, separate from the subscription weekly pool | https://docs.x.ai/developers/pricing | CONFIRMED that the model is listed with token pricing — UNCONFIRMED whether CLI-via-`XAI_API_KEY` billing and CLI-via-subscription-login billing are two genuinely separate metering paths, or whether an API-key-authenticated CLI session still counts against a console team's rate-limit tier (RPS/TPM) as described generically on docs.x.ai/developers/rate-limits. Not reconciled in the fetched content. |
| 11 | Generic API rate limits (RPS/TPM) scale with a team's cumulative-spend tier, viewable in the xAI Console; HTTP 429 on exceed, exponential backoff recommended | https://docs.x.ai/developers/rate-limits | CONFIRMED (primary) — this is the general API rate-limit model; not confirmed to be the same mechanism that gates the CLI's consumer weekly pool (finding #8) |
| 12 | `x.ai/news/grok-build-cli` (the CLI launch announcement) | https://x.ai/news/grok-build-cli | **UNREACHABLE this pass — HTTP 403.** Matches the task brief's note that the 2026-07-19 research pass got 403s on some xAI pages; re-tried once, still 403. `docs.x.ai/grok/faq` (403 on a different fetch path earlier in this session, then succeeded on retry) shows these blocks are inconsistent/transient rather than a hard wall. |

## What is confirmed vs still open

**Confirmed (primary source, docs.x.ai / github.com/xai-org):**
- Non-interactive auth has (at least) two documented paths: `XAI_API_KEY` env var (simplest, no login flow) and `grok login --device-auth` (device-code flow, still needs one human-in-the-loop step the first time). Enterprise OIDC is a third path for org deployments.
- The exact invocation shape the spec pins (`grok -p ... --output-format streaming-json`, `--always-approve`, `--sandbox <profile>`, `--effort`, `--max-turns`, `--model`) — every flag named in the spec's Grok clause is a real, documented CLI flag.
- Grok Build CLI usage for consumer subscribers draws from the unified weekly usage pool (not a Build-specific separate cap), and exhaustion is a soft pause (not a hard error), with a paid top-up path.

**UNCONFIRMED (do not guess further — needs a human/live probe):**
- The exact numeric size of the weekly pool per tier (SuperGrok / SuperGrok Heavy / Premium+ / free), and specifically how much of it a typical `grok -p` headless CLI call consumes relative to a Chat message — the FAQ names the mechanism but not the numbers.
- Whether an `XAI_API_KEY`-authenticated CLI session is metered under the pay-per-token API rate-limit model (finding #11) or the subscription weekly pool (finding #8), or both depending on which credential resolves first (per the earlier `superagent-ai/grok-cli` community-doc note on credential precedence — that project is NOT the official CLI and was not used as a citation here beyond flagging the precedence-order concept exists in this ecosystem).
- The discrepancy between `~/.grok/auth` (enterprise doc) and `~/.grok/sessions` (CLI reference doc) as the login-state file/dir — not reconciled against a real install.
- Everything that requires actually running `grok --version`, `grok login`, and a real `grok -p` call and observing real headers/errors — none of this was possible since the CLI is not installed on this machine.

## GATE VERDICT

**Evidence is sufficient for a human to review the auth-path question** (multiple
primary-source docs.x.ai pages independently confirm the `XAI_API_KEY` env-var path and
the exact flag shape the spec pins). **Evidence is only partial for the rate-cap
question**: the mechanism (unified weekly pool, soft-pause-not-hard-block) is
primary-source confirmed, but the numeric shape (how many CLI calls per week per tier)
is not published anywhere reachable in this pass and remains UNCONFIRMED.

This pilot does **not** clear Grok for enablement — that decision is the human's, per
spec. To close the remaining gap before/alongside that review, what's left is:

1. A human installs the Grok Build CLI (Forge will not install it) and runs
   `grok --version`, `grok login --device-auth` (or sets `XAI_API_KEY` and runs a
   dry `grok -p "hi" --output-format streaming-json`), to confirm the documented
   flags/env var actually behave as documented on this machine.
2. If numeric rate-cap figures matter to the enablement decision, check the live
   xAI Console (`docs.x.ai/developers/rate-limits` links to team-specific per-model
   limits) and/or the subscriber's own app for the current weekly-pool size — neither
   is published as a stable public number in the docs fetched here.
3. Reconcile the `~/.grok/auth` vs `~/.grok/sessions` discrepancy against the real
   installed CLI's behavior.

The picker's Grok slot stays closed (detection-only stub) until a human completes that
review; this task does not and cannot flip it.
