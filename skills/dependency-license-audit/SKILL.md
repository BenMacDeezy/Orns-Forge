---
name: dependency-license-audit
description: Auditing the license of a dependency, package, vendored code, GitHub repo, skill, or plugin before adopting it; license compatibility; copyleft; NOTICE/attribution files; SPDX. Use before adding a dependency, vendoring code, installing a skill/plugin/MCP server, or when asked to check a license, copyleft risk, or attribution obligations.
---

# Dependency license audit

You produce engineering-side license analysis — bucket the license, check
compatibility against the project's own license, list obligations. You never
decide whether a license is legally acceptable to ship; that's counsel's call.

## 1. Resolve the declared license — in this order

1. **Package manifest metadata** — `package.json` `"license"`,
   `pyproject.toml`/`METADATA` `License-Expression`/`Classifier`, `Cargo.toml`
   `license` (`go.mod` has none — check the repo root instead).
2. **`gh repo view <owner>/<repo> --json licenseInfo`** — for anything
   GitHub-sourced (repo, skill, plugin, vendored code copied from a repo).
   Zero-install, run first for GitHub-sourced items even before the manifest
   — one command, authoritative on what GitHub itself detected.
3. **The LICENSE/COPYING file text itself** — read when (1) and (2) disagree,
   are absent, or the manifest just says `"SEE LICENSE IN LICENSE"`.

If all three disagree, or none resolve a clear answer, classify the
dependency **unlicensed/unclear — treat as all-rights-reserved until
resolved**. Never guess a license from context (stars, README tone,
"probably MIT") — silence on licensing is not permission.

## 2. Classification buckets

- **Permissive** — MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC.
- **Weak copyleft** — LGPL (2.1/3.0), MPL-2.0, EPL (1.0/2.0).
- **Strong copyleft** — GPL-2.0, GPL-3.0, AGPL-3.0. AGPL adds a network-use
  trigger GPL doesn't have: modifying and running AGPL code as a network
  service triggers source-disclosure obligations even without distributing
  the binary (GNU AGPL-3.0, §13).
- **Source-available, non-OSI** — BUSL (Business Source License), SSPL
  (Server Side Public License), Elastic License, Commons Clause. Not open
  source by the OSI definition; usually carry field-of-use or competitive-use
  restrictions — read the specific grant, don't assume it behaves like a
  copyleft license.
- **Public-domain-equivalent** — Unlicense, CC0, 0BSD. No attribution
  obligation, but confirm the file itself carries the grant (CC0 on a repo
  README doesn't automatically cover every file in it).
- **Unlicensed** — no license found anywhere; default copyright applies
  (all rights reserved). Treat as unusable until the maintainer clarifies.

## 3. Compatibility check against the project's own license

Read the project's own LICENSE file first — every compatibility call is
relative to it. **If the project has no LICENSE file, that is itself the
first finding** (RED: the project's own IP posture is undefined, so no
downstream compatibility call can be made with confidence).

Contamination rules:

- **Strong copyleft**, linked or derived into the project → the project's
  own license must be compatible with that copyleft license (e.g. a
  permissively-licensed project cannot statically link GPL-3.0 code without
  the combined work becoming GPL-3.0). Flag RED and name the specific
  incompatibility.
- **Weak copyleft** → obligations are usually file- or library-level (LGPL
  dynamic linking, MPL file-level copyleft) rather than infecting the whole
  project. Verify the actual usage pattern (static vs dynamic link, modified
  vs unmodified file) before asserting scope — don't default to "it's fine"
  or "it's viral" without checking which.
- **Permissive** → attribution obligations only (§4). No contamination risk.

Cite sources by tier, and note their framing:

- **GNU license list** (gnu.org/licenses/license-list.html) — authoritative
  for GPL-family calls, but carries FSF advocacy framing (editorializes on
  which licenses are "good"/"bad" for freedom); pair with SPDX or
  choosealicense.com for a neutral restatement of the same fact.
- **SPDX** (spdx.org/licenses) — canonical identifiers; use SPDX IDs in every
  finding so they're machine- and human-verifiable.
- **choosealicense.com** — plain-English "can/cannot/must" summaries; not a
  substitute for the license text on an edge case.
- **Blue Oak Council** (blueoakcouncil.org/list) — a drafting-quality signal
  for permissive licenses (gaps/ambiguity in the text itself), not a
  compatibility authority — use it to flag weak drafting, not answer copyleft.

## 4. Obligations output

For every dependency you're keeping (GREEN or YELLOW), state the concrete
attribution/NOTICE obligation and produce the actual entry text, e.g.:

```
Copyright (c) <year> <holder>
Licensed under the <SPDX-ID>. <one-line permission summary>. Full text: <path-or-URL>.
```

If the project has a `NOTICE` or `THIRD_PARTY_LICENSES` file convention,
match its existing format instead of inventing a new one.

## 5. Optional accelerators — only if already available, never installed

Phrase every one of these as "if available on PATH / if the relevant
manifest exists" — never assume, never install:

- **`npx license-checker-rseidelsohn`** — if a JS/TS lockfile exists and npx
  is on PATH, run it for a full dependency-tree license inventory instead of
  auditing `package.json` files by hand one at a time.
- **`pip-licenses`** — if a Python environment is active and the package is
  installed, use it for the same purpose in a Python project.
- **`reuse lint`** — for auditing *this repo's own* SPDX header/attribution
  hygiene (FSFE REUSE spec), not third-party dependencies.

**Deep-audit escalation only (never the default path):** ScanCode Toolkit
for forensic full-text license detection on ambiguous vendored code where
manifest/LICENSE-file resolution genuinely fails — heavyweight, reserve for
cases §1 couldn't resolve.

Do NOT reference FOSSA, Snyk, or licensee — not vetted for this workflow.

## 6. Output framing

One row per dependency:

| Dependency | License (SPDX) | Bucket | Compatibility verdict | Obligations |
|---|---|---|---|---|

Tag every row GREEN / YELLOW / RED:

- **RED** — incompatible with the project's license, or unlicensed/unclear.
- **YELLOW** — compatible but carries obligations (attribution, NOTICE,
  file-level copyleft), or license metadata itself was unclear/conflicting
  before resolution.
- **GREEN** — compatible, obligations trivial (permissive, attribution-only,
  already satisfied by existing NOTICE conventions).

---
This skill produces engineering-side license/compliance analysis, not legal
advice. Findings must be verified with qualified counsel before relying on
them for shipping, licensing, or contractual decisions. Cite sources for
every non-obvious judgment so a human can independently verify.

---
Adapted from: https://spdx.org/licenses/
Adapted from: https://choosealicense.com/
Adapted from: https://www.gnu.org/licenses/license-list.html
Adapted from: https://www.gnu.org/licenses/agpl-3.0.en.html (§13, network use)
Adapted from: https://blueoakcouncil.org/list
Adapted from: https://reuse.software/
Adapted from: https://cli.github.com/manual/gh_repo_view
