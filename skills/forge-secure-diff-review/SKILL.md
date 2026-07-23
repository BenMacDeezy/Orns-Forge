---
name: forge-secure-diff-review
description: Diff-scoped secure code review methodology — OWASP secure code review flow, CWE Top 25 (2025) fast-triage checklist, deep-checks for injection/broken authz/SSRF/insecure deserialization/secrets exposure, a 5-minute STRIDE pass, a secrets-in-diff scan, and a money/financial-logic checklist (TOCTOU, replay, rounding, idempotency). Use when reviewing a diff for security defects, when forge-security starts a review, or before judging changes that touch authentication, input handling, secrets/credentials, or money/payment flows.
---
<!-- last-verified: 2026-07 -->

# Secure diff review

You judge one diff. Never edit code — findings only. Scope is the changed
lines and their immediate call graph, not the whole repo: a diff-based review
answers "did this change introduce or regress a security control?", not "is
this codebase secure?" (OWASP Secure Code Review Cheat Sheet).

**Scope arbitration (marketplace `cybersecurity` skill):** within a Forge
review, this skill governs diff-scoped security review — the same role
`forge-security.md` already assigns it relative to the `security-review`
skill. The marketplace `cybersecurity` skill (8-agent, repo-wide audit) is for
broader, user-initiated security work outside the Forge pipeline, not for
judging one task's diff. Do not double-fire both on the same ask.

## Review flow (diff-based, not baseline)

1. **Impact on existing controls** — does the diff touch, remove, or bypass an existing auth check, validator, or sanitizer?
2. **New attack vectors** — does it add a new entry point (route, API, deserialization target, file write, shell-out, outbound call)?
3. **Trust boundaries** — anywhere it crosses one (user input → query/filesystem, service → service, client → server), verify enforcement still holds on the new path.
4. **New integrations** — new dependency, external call, or credential/token use: vet it independently, don't assume the author did.
5. **Regression check** — would this diff have silently defeated a prior test or control even if nothing in it looks wrong standalone?

## CWE Top 25 (2025) fast triage

Walk changed lines against this list; skip entries the diff's language/stack
can't reach (e.g. memory-safety CWEs are moot for a pure-Python diff). List
per CWE Top 25 2025; verify against cwe.mitre.org on next refresh.

`CWE-79` XSS · `CWE-787`/`CWE-125`/`CWE-119` OOB write/read/buffer bounds ·
`CWE-89` SQL injection · `CWE-352` CSRF · `CWE-22` path traversal ·
`CWE-78`/`CWE-77` OS/command injection · `CWE-416` use-after-free ·
`CWE-862`/`CWE-863` missing/incorrect authorization · `CWE-434` unrestricted
dangerous file upload · `CWE-94` code injection · `CWE-20` improper input
validation · `CWE-287` improper authentication · `CWE-269` improper
privilege management · `CWE-502` deserialization of untrusted data ·
`CWE-200` sensitive info exposure · `CWE-918` SSRF · `CWE-476` null deref ·
`CWE-798` hardcoded credentials · `CWE-190` integer overflow · `CWE-400`
uncontrolled resource consumption · `CWE-306` missing auth for critical
function.

## Category deep-checks

- **Injection (SQLi/command/template):** string-built query, shell command, or template render fed by request/user data without parameterization or an allowlist. Check ORMs too — raw-SQL escape hatches defeat them.
- **Broken authz / IDOR:** every new handler that reads/writes a resource by ID must check the caller owns/is entitled to that ID, not just that they're authenticated. Watch for the check on the wrong object, or client-side only.
- **SSRF:** any new outbound request (webhook, URL fetch, image proxy, import-from-URL) with a user-influenced target. Require an allowlist or metadata-endpoint block (`169.254.169.254`, `localhost`, internal CIDRs).
- **Insecure deserialization / RCE:** `pickle`/`yaml.load`/native deserializers, `eval`/`exec`, dynamic `require`/`import` on user data, unsandboxed template engines with code execution.
- **Secrets exposure:** see the secrets-in-diff scan below.

## STRIDE-per-diff (5 minutes, not a full threat model)

- **S**poofing — reachable while impersonating another identity (missing signature/token check)?
- **T**ampering — can trusted request/stored data be modified in transit or at rest undetected?
- **R**epudiation — does a new sensitive action (money, permission change, delete) hit an audit log with actor + timestamp?
- **I**nfo disclosure — does a new response/log/error leak more than the caller is entitled to?
- **D**oS — unbounded loop, unpaginated query, or attacker-sized allocation reachable pre-auth?
- **E**levation — can the new path grant more privilege than the caller already had?

## Secrets-in-diff scan

Scan only the changed lines (`+` lines of the diff), not the whole file.
gitleaks is fast regex/entropy matching — good as a first pass but produces
false positives on test fixtures and high-entropy non-secret strings;
trufflehog additionally attempts live credential verification, which cuts
noise but requires network egress and isn't always available in-session.
If either is on PATH, run it and fold real (not fixture/placeholder) hits
into FINDINGS:

```
gitleaks detect --no-git -v --source <changed-file-or-dir>
semgrep --config p/secrets <changed-file-or-dir>
```

On Windows/Git Bash, prefix semgrep with `PYTHONUTF8=1` (it otherwise hits a
cp1252 encoding error fetching rules): `PYTHONUTF8=1 semgrep --config p/secrets <path>`.

Treat `semgrep --config p/security-audit` output the same way if `semgrep`
is on PATH — fold genuine findings in, don't just append the raw tool output.

## Money / financial-logic checklist

- **TOCTOU races (CWE-367):** balance/inventory checked then acted on in two separate operations without a lock, atomic conditional update, or `SELECT ... FOR UPDATE`. Could two concurrent requests both pass the check?
- **Replay:** does a payment/transfer/refund endpoint accept the same request twice (retry, double-click, replayed webhook) and execute it twice?
- **Rounding/precision:** money represented as float, or rounding applied per-line instead of once at settlement.
- **Missing idempotency:** no idempotency key on a create-payment / create-charge / create-transfer endpoint.
- **Authorization-before-amount:** amount/currency read straight from client input and used, instead of the check authorizing "this caller may move up to X" independent of the client's claim.

## Output contract (exactly forge-security's contract — never deviate)

```
VERDICT: PASS | CHANGES REQUESTED
COUNTS: <N critical, M important>
SURFACE: <which of auth / input / secrets / money this diff touches>
FINDINGS:
- [Critical|Important|Minor] <file:line> — <vulnerability> — <exploit scenario>
NOTES: <or "none">
```

Any Critical or Important finding forces `VERDICT: CHANGES REQUESTED`. Every
finding needs a concrete `file:line` and a one-sentence exploit scenario —
not a category name. You judge; you never edit source.

---
Adapted from: https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html
Adapted from: https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html
Adapted from: https://owasp.org/www-community/pages/vulnerabilities/race_conditions
Adapted from: https://github.com/anthropics/claude-code-security-review
