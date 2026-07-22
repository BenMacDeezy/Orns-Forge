"""Aggregate Forge queue task Routing records + Attempt logs into telemetry:
per-agent-slug dispatch counts, first-attempt PASS rate, bounce rate split by
MECHANICAL/JUDGMENT tag, verify-mode distribution, per-tier counts, ESCALATE
occurrences, and (fg-a10212) MEASURED per-spawn/per-layer token totals parsed
from the optional `[tokens: ...]` Attempt-log suffix. Read-only: never
transitions a task. Zero dependencies.

Forge's Agent-Manager analogue -- the Attempt logs already on disk are the
telemetry source; this is the first thing that reads them in aggregate.

Grammar this parser keys on is documented in docs/conventions.md, "Telemetry
vocabulary -- 2026-07" (NORMATIVE: keep the parser and that section in sync).
"""
import json
import pathlib
import re
import sys

# Reuse validate_task's frontmatter/section helpers rather than re-implement
# them -- same fence-aware, line-anchored section parsing every other tool
# in this repo relies on.
_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import validate_task

TASK_DIR_DEFAULT = ".forge/queue/tasks"

# Longest-first so a substring match (e.g. "forge-ui" inside
# "forge-ui-verifier") never shadows the more specific slug.
# Promoted project-local agents (skills/agent-factory/SKILL.md, "On
# APPROVE") get their slug appended here by hand at promotion time --
# this list stays manually maintained, never dynamically discovered.
AGENT_SLUGS = sorted(
    [
        "forge-worker", "forge-verifier", "forge-ui-verifier", "forge-reviewer",
        "forge-security", "forge-legal", "forge-architect", "forge-debugger",
        "forge-ui", "forge-animator", "forge-test-writer", "forge-researcher",
        "forge-migrator", "forge-scout", "forge-mapper", "forge-librarian",
        "forge-spec-writer", "forge-triage", "forge-data", "finder",
    ],
    key=len,
    reverse=True,
)

TIER_RE = re.compile(r"\b(haiku|sonnet|opus|fable)/(low|medium|high|max)\b")
VERDICT_RE = re.compile(r"\b(PASS|FAIL|ESCALATE)\b")
# Telemetry honesty (docs/conventions.md, Finding filter): a verify recorded as
# PASS-after-filter (verifier findings all FILTERED by the kernel spot-check)
# still COUNTS as a FAIL verdict.  Checked before VERDICT_RE because \b matches
# the S/- boundary in "PASS-after-filter", which would misparse it as PASS.
PASS_AFTER_FILTER_RE = re.compile(r"\bPASS-after-filter\b", re.I)
TAG_RE = re.compile(r"\b(MECHANICAL|JUDGMENT)\b", re.I)
GATE_INLINE_RE = re.compile(r"gate:\s*(execute\s+)?inline", re.I)

DISPATCH_RE = re.compile(r"^attempt (\d+): dispatched\b")
VERIFY_RE = re.compile(r"^attempt (\d+) (verify|re-verify|verdict):\s*(.*)$")
BOUNCE_RE = re.compile(r"^attempt (\d+) \(bounce,([^)]*)\):\s*(.*)$")
ROUTING_ENTRY_RE = re.compile(r"^(attempt \d+:|GATE:|Delegation GATE:)")
# Consensus-rollout records deliberately use a compact, strict line instead
# of attempting to infer outcome/cost from provider prose.  They are written
# by the consensus ledger owner; telemetry only reads and aggregates them.
CONSENSUS_ROLLOUT_RE = re.compile(
    r"^consensus-rollout: c1-rejects=(\d+) c1-resolved=(\d+) "
    r"c2-rejects=(\d+) c2-resolved=(\d+) cap-out=(yes|no) "
    r"baseline-cost=(\d+) consensus-cost=(\d+) "
    r"baseline-latency-ms=(\d+) consensus-latency-ms=(\d+)$"
)

# fg-a11023 (docs/audits/2026-07-18-protocol-overhead-audit.md Recommendation
# 2): a large block of tasks predating the canonical "attempt N verify:"/
# "attempt N (bounce, TAG):" phrasing instead wrote free-prose Attempt-log
# lines. VERIFY_RE/BOUNCE_RE's exact-form requirement silently drops these
# clean, well-evidenced verdicts into the unparsed tally instead of
# first_attempt/verify_verdicts/bounces -- a real, growing undercount, not
# a cosmetic gap. These two patterns recognize the two recurring legacy
# shapes actually found in this repo's own committed queue history (not
# invented forms); free-text narrative that matches neither shape still
# correctly falls through to unparsed (coverage honesty is unchanged).
#
# Shape 1 -- "attempt N: verifier PASS|FAIL (tier...)" / "attempt N: ...
# re-verify PASS|FAIL (tier...)" (fg-9a0101/fg-9a0301/fg-9a0303/fg-9b0101/
# fg-9b0302/fg-9b0304/fg-9b0303/fg-9b0102/fg-9a0304 live lines). Lazily
# scans from "attempt N:" to the FIRST "verifier"/"re-verify" + PASS/FAIL
# pair in the line -- when a line narrates two events (a bounce followed
# by a re-verify, e.g. fg-9b0102), this recovers the FIRST recognizable
# verdict rather than silently dropping the whole line; the tier is then
# located via _find_tier's normal (line-wide) search, tolerating a tier
# token that shares its parenthetical with extra prose (fg-9b0303).
LEGACY_VERIFY_RE = re.compile(
    r"^attempt (\d+):.*?\b(verifier|re-verify)\s+(PASS|FAIL)\b", re.I
)
# Shape 2 -- a FAIL immediately followed by a "(bounce N[/M])" marker
# (fg-a100's live line: "... fails verification -> FAIL (bounce 1/2)."),
# predating the canonical "attempt N (bounce, TAG):" prefix form BOUNCE_RE
# matches -- the same "(bounce...)" idiom, just placed after the verdict
# instead of at the line's start. Deliberately narrow (requires the literal
# "FAIL" + "(bounce <digits>" adjacency) so it never fires on the unrelated
# "(bounce pre-check)" finding-filter mechanism name used elsewhere in this
# repo's Attempt logs (fg-a10205/fg-a10208/fg-a10504 live lines all read
# "kernel filter (bounce pre-check): ..." with no digit after "bounce").
LEGACY_BOUNCE_RE = re.compile(r"\bFAIL\b.*?\(bounce\s*(\d+)(?:/\d+)?\)", re.I)
# Judge-yield lines (fg-a10901, docs/conventions.md "Verification economics
# — 2026-07-18"): findings raised -> survived the finding filter -> changed
# the outcome. Strict shape; a malformed line counts as unparsed (coverage
# honesty), never as a silent zero.
#
# fg-a10911 (docs/conventions.md "Finding severity + confidence —
# 2026-07-18 (fg-a10911)") extends this BACKWARD-COMPATIBLY with an optional
# trailing severity-distribution suffix `p0=A p1=B p2=C p3=D` (counts of
# RAISED findings per P-level). The base `raised=N survived=M changed=K`
# shape still parses with no suffix present; a suffix that is present but
# malformed (missing a p-level, non-numeric, wrong order) fails the WHOLE
# match -- the line falls through to unparsed, never a silent partial parse.
#
# fg-c0106 (spec-e8a3 Phase 1, docs/conventions/verification.md "Verification
# economics -- 2026-07-18 (fg-a10901)" judge-yield shape, extended for
# provider judges via skills/kernel/references/provider-judges.md section 5):
# the slug may carry an OPTIONAL provider prefix, `<provider>:<agent-slug>`
# (e.g. `codex:forge-verifier`) -- backward-compatible with every existing
# bare-slug line (no colon). A malformed prefix (double colon, empty
# provider/agent segment) fails the WHOLE match, same coverage-honesty
# discipline as the p0-p3 suffix above -- the line falls through to
# unparsed, never a silent partial parse.
JUDGE_YIELD_RE = re.compile(
    r"^judge-yield:\s*([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)\s+raised=(\d+)\s+survived=(\d+)\s+changed=(\d+)"
    r"(?:\s+p0=(\d+)\s+p1=(\d+)\s+p2=(\d+)\s+p3=(\d+))?\s*$",
    re.I,
)

# Per-spawn token capture (fg-a10212, docs/conventions.md "Token capture —
# 2026-07-19", amending "Telemetry vocabulary — 2026-07"). An OPTIONAL
# trailing suffix on a dispatch/verify/re-verify/bounce Attempt-log line:
# `[tokens: NNNNN]` when the harness reported a real count at that spawn's
# completion, `[tokens: unreported]` when it didn't -- absent data is
# recorded, never invented or silently dropped. TOKEN_LOOSE_RE detects
# "something suffix-shaped is here" for the malformed-vs-absent distinction;
# TOKEN_RE is the strict grammar. A line with NO suffix at all is untouched
# -- byte-for-byte backward compatible with every line shape that predates
# this amendment.
TOKEN_RE = re.compile(r"\[tokens:\s*(\d+|unreported)\]\s*$", re.I)
TOKEN_LOOSE_RE = re.compile(r"\[tokens:[^\]]*\]\s*$", re.I)


def _strip_token_suffix(line):
    """Detect and remove a trailing `[tokens: ...]` suffix from an Attempt
    log line. Returns (line_without_suffix, tokens, malformed):

    - No suffix-shaped bracket at the end -> (line, None, False) -- the line
      is returned COMPLETELY unchanged, so every pre-amendment line shape
      (dispatch/verify/bounce/judge-yield) parses exactly as it always has.
    - A strictly-formed suffix -> (line-with-suffix-stripped, int-or-
      "unreported", False).
    - A suffix-shaped bracket that fails the strict grammar (non-numeric,
      wrong keyword, missing bracket) -> (line, None, True); the caller
      must treat this as a whole-line parse failure (coverage honesty --
      mirrors JUDGE_YIELD_RE's strict-whole-match discipline: a malformed
      suffix never produces a silent partial parse of the rest of the line).
    """
    loose = TOKEN_LOOSE_RE.search(line)
    if not loose:
        return line, None, False
    strict = TOKEN_RE.match(line, loose.start())
    if not strict:
        return line, None, True
    raw = strict.group(1)
    tokens = "unreported" if raw.lower() == "unreported" else int(raw)
    return line[: loose.start()].rstrip(), tokens, False


def _find_tier(text):
    m = TIER_RE.search(text)
    return f"{m.group(1)}/{m.group(2)}" if m else None


AGENT_SLUG_RES = [
    (slug, re.compile(r"\b" + re.escape(slug) + r"\b")) for slug in AGENT_SLUGS
]


def _find_slug(text):
    # Word-boundary match, not bare substring -- a token that merely embeds
    # a real slug (e.g. "pathfinder" embedding "finder") must never
    # attribute a dispatch (fg-a10503). Longest-first order (AGENT_SLUGS is
    # sorted reverse by len) still prevents a shorter slug like "forge-ui"
    # from shadowing "forge-ui-verifier" for the same line.
    for slug, slug_re in AGENT_SLUG_RES:
        if slug_re.search(text):
            return slug
    if re.search(r"\binline\b", text, re.I):
        return "kernel-inline"
    return None


# Captures the dispatch-target token: everything between "attempt N:" and
# the first field separator -- an em dash, arrow, or hyphen with whitespace
# on both sides (docs/conventions.md, "Routing record line shapes":
# `attempt N: <slug> — <model>/<tier> — <rationale>`; a plain " - " hyphen
# is also accepted, and so is "->"/"→", matching the separator-variant
# tolerance this module already applies elsewhere for the same field-
# boundary role, e.g. VERIFY_RE's "->"/"→" -- fg-a10928: a routing line
# using "->" as its separator (e.g. "attempt 1: forge-spec-writer -> part
# of the fg-a10601 spec; ...") must match here too, or it falls through to
# whole-line search and _find_slug picks up a slug merely MENTIONED in the
# rationale instead of the actual dispatch target. Whitespace-padding
# around the separator is what distinguishes a real field boundary from a
# hyphen embedded inside a slug itself (e.g. "forge-ui" must not split at
# its own internal "-"); "->" is tried before the bare "-" alternative so
# the arrow is matched whole rather than as a lone hyphen that then fails
# on the trailing ">".
ATTEMPT_TARGET_RE = re.compile(r"^attempt \d+:\s*(.+?)\s(?:->|—|→|-)\s")


def _dispatch_target_text(line):
    """Return the slice of `line` that names the actual dispatch target --
    the token right after "attempt N:" and before the first field
    separator -- instead of the whole line. `_find_slug` must only be
    scoped to this token when looking for the routing entry's slug: a slug
    merely mentioned later in the line's rationale text (e.g. "forge-ui"
    dispatched but "forge-ui-verifier" mentioned in passing) must never be
    picked up as if it were the dispatch target (fg-a10504 telemetry-
    corruption class of bug).

    Lines that don't match the "attempt N: ..." shape (GATE:/Delegation
    GATE: lines, which carry no slug token at all) fall back to the whole
    line, unchanged from prior behavior -- those rely on _find_slug's bare
    "inline" fallback, not a dispatch-target token.
    """
    m = ATTEMPT_TARGET_RE.match(line)
    return m.group(1) if m else line


# fg-a11029: the SAME misattribution class as fg-a10504/fg-a10928
# (_dispatch_target_text above), applied to the tier field instead of the
# slug field. Canonical Routing record lines are 3-field: `attempt N:
# <slug> — <model>/<tier> — <rationale>` -- for a properly-delimited line
# like this, field 2 (the tier) always appears BEFORE any tier-shaped text
# the rationale (field 3) might separately mention, so plain first-match
# search over the whole line was never actually wrong for this shape.
# The real, reproducible misattribution only happens on a LEGACY/malformed
# line that skips the tier field entirely -- just `attempt N: <slug> -
# <rationale>` (one separator, not two) -- where a bounce-and-retry
# rationale narrates BOTH the old and the new tier ("previously bounced
# from opus/high; retry at sonnet/low"): first-match search picks up the
# stale "opus/high" mention instead of the real, currently-routed
# "sonnet/low" one. Requires the SAME two-separator shape
# ATTEMPT_TARGET_RE's own docstring describes, capturing the text between
# separator 1 and separator 2 when both are present.
ATTEMPT_TIER_RE = re.compile(
    r"^attempt \d+:\s*.+?\s(?:->|—|→|-)\s*(.+?)\s(?:->|—|→|-)\s"
)


def _dispatch_tier(line):
    """Return the routed model/tier for a Routing record entry line.

    Extraction here is a STRICT SUPERSET of HEAD's plain `_find_tier(line)`
    (whole-line, first-match) behavior -- every branch below only REFINES
    that baseline when it finds a real, better answer; it never trades a
    baseline hit away for a scoped miss. This is load-bearing: the live
    Routing-record corpus is far more heterogeneous than the canonical
    3-field `attempt N: <slug> — <tier> — <rationale>` shape suggests --
    e.g. a tier stated with no separator before it at all (fg-a10909:
    "forge-worker sonnet/medium or Grud..."), an extra field between slug
    and tier (fg-9b0201: "finder — verification: kernel synthesis (mode
    3) — sonnet/high — ..."), or a spurious separator-shaped em-dash/arrow
    INSIDE the rationale before the real tier is even reached (fg-a10901's
    "(likely — pipelining...)"; fg-a10902's two "->" dispatch-chain
    arrows). In every one of these, HEAD's simple whole-line search
    already finds the tier correctly (it is the ONLY tier-shaped
    substring in the line); a field-scoped search that stops too early
    must not be allowed to turn that correct hit into `None`.

    - Legacy/malformed line with only ONE separator (no delimited tier
      field was ever written -- straight from slug to rationale prose):
      search the rationale (text after the dispatch target) for the LAST
      tier mention rather than the first, matching this shape's own
      "previously X; retry at Y" temporal convention where the most
      recently stated tier is the current one (fg-a11029) -- but only
      when that search finds something; an empty result falls back to
      the whole-line baseline rather than reporting `None` when HEAD
      would have found a tier sitting inside the target token itself
      (fg-a10909).
    - Two-separator line: the tier is read from field 2 first (mirrors
      `_dispatch_target_text`'s slug-field scoping) -- but when field 2
      doesn't itself contain a tier (the field-2/field-3 assumption
      doesn't hold for this line's shape, e.g. fg-9b0201/fg-a10901/
      fg-a10902 above), fall back to the whole-line baseline rather than
      `None`.
    - No separator at all (GATE:/Delegation GATE:/garbage lines): whole-
      line, first-match search via `_find_tier`, byte-identical to
      pre-fix -- unchanged.
    """
    tier_field = ATTEMPT_TIER_RE.match(line)
    if tier_field:
        return _find_tier(tier_field.group(1)) or _find_tier(line)
    target = ATTEMPT_TARGET_RE.match(line)
    if target:
        matches = list(TIER_RE.finditer(line, target.end()))
        if matches:
            m = matches[-1]
            return f"{m.group(1)}/{m.group(2)}"
        return _find_tier(line)
    return _find_tier(line)


def parse_attempt_log(body):
    """Parse a task's '## Attempt log' body into per-line stats.

    Every non-blank line is classified parsed or unparsed -- coverage is
    total over every line, never a silently-dropped subset (fg-a10101
    acceptance clause 2). Never raises on garbage input.
    """
    stats = {
        "lines_total": 0,
        "parsed": 0,
        "unparsed": 0,
        "verify_verdicts": [],  # [{attempt, kind, verdict, tier, tag}, ...]
        "bounces": [],  # [{attempt, tier, tag}, ...]
        "judge_yields": [],  # [{slug, raised, survived, changed}, ...]
        "dispatches": [],  # [{attempt, tokens}, ...] -- fg-a10212
        "sampling_audit": False,
        "low_risk_qualified": False,
    }
    if not body:
        return stats

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line == "(pending)":
            continue
        stats["lines_total"] += 1

        # fg-a10212 token-suffix strip happens before any shape match so
        # every regex below sees the exact same text it always has when no
        # suffix is present (backward compatibility by construction).
        line, tokens_value, malformed = _strip_token_suffix(line)
        if malformed:
            stats["unparsed"] += 1
            continue

        lower = line.lower()

        if "sampling audit" in lower:
            stats["sampling_audit"] = True
        if "low-risk verify: qualified" in lower:
            stats["low_risk_qualified"] = True

        dm = DISPATCH_RE.match(line)
        if dm:
            stats["parsed"] += 1
            stats["dispatches"].append(
                {"attempt": int(dm.group(1)), "tokens": tokens_value}
            )
            continue

        m = VERIFY_RE.match(line)
        if m:
            rest = m.group(3)
            if PASS_AFTER_FILTER_RE.search(rest):
                # Counts as FAIL per the conventions telemetry-honesty rule.
                stats["parsed"] += 1
                stats["verify_verdicts"].append(
                    {
                        "attempt": int(m.group(1)),
                        "kind": m.group(2),
                        "verdict": "FAIL",
                        "tier": _find_tier(rest),
                        "tag": None,
                        "tokens": tokens_value,
                    }
                )
                continue
            verdict_m = VERDICT_RE.search(rest)
            if verdict_m:
                stats["parsed"] += 1
                verdict = verdict_m.group(1)
                tag_m = TAG_RE.search(rest) if verdict == "FAIL" else None
                stats["verify_verdicts"].append(
                    {
                        "attempt": int(m.group(1)),
                        "kind": m.group(2),
                        "verdict": verdict,
                        "tier": _find_tier(rest),
                        "tag": tag_m.group(1).upper() if tag_m else None,
                        "tokens": tokens_value,
                    }
                )
            else:
                stats["unparsed"] += 1
            continue

        m2 = LEGACY_VERIFY_RE.match(line)
        if m2:
            stats["parsed"] += 1
            verdict = m2.group(3).upper()
            kind = "verify" if m2.group(2).lower() == "verifier" else "re-verify"
            tag_m = TAG_RE.search(line) if verdict == "FAIL" else None
            stats["verify_verdicts"].append(
                {
                    "attempt": int(m2.group(1)),
                    "kind": kind,
                    "verdict": verdict,
                    "tier": _find_tier(line),
                    "tag": tag_m.group(1).upper() if tag_m else None,
                    "tokens": tokens_value,
                }
            )
            continue

        m = BOUNCE_RE.match(line)
        if m:
            stats["parsed"] += 1
            paren, rest = m.group(2), m.group(3)
            tag_m = TAG_RE.search(paren) or TAG_RE.search(rest)
            stats["bounces"].append(
                {
                    "attempt": int(m.group(1)),
                    "tier": _find_tier(paren) or _find_tier(rest),
                    "tag": tag_m.group(1).upper() if tag_m else None,
                    "tokens": tokens_value,
                }
            )
            continue

        m2 = LEGACY_BOUNCE_RE.search(line)
        if m2:
            stats["parsed"] += 1
            tag_m = TAG_RE.search(line)
            stats["bounces"].append(
                {
                    "attempt": int(m2.group(1)),
                    "tier": _find_tier(line),
                    "tag": tag_m.group(1).upper() if tag_m else None,
                    "tokens": tokens_value,
                }
            )
            continue

        m = JUDGE_YIELD_RE.match(line)
        if m:
            stats["parsed"] += 1
            entry = {
                "slug": m.group(1).lower(),
                "raised": int(m.group(2)),
                "survived": int(m.group(3)),
                "changed": int(m.group(4)),
            }
            # p0-p3 suffix (fg-a10911) is entirely optional -- only present
            # when the judge-yield line named it -- so a plain no-suffix
            # line still produces the exact same dict shape it always has.
            if m.group(5) is not None:
                entry["severity"] = {
                    "p0": int(m.group(5)),
                    "p1": int(m.group(6)),
                    "p2": int(m.group(7)),
                    "p3": int(m.group(8)),
                }
            stats["judge_yields"].append(entry)
            continue

        stats["unparsed"] += 1

    return stats


def parse_routing_record(body):
    """Best-effort extraction of agent-slug/model-tier dispatch entries plus
    verify-mode signals (kernel synthesis, gates-inline) from a task's
    '## Routing record' body.

    Not subject to the Attempt-log unparsed-tally contract -- fg-a10101's
    acceptance clause 2 names the Attempt log specifically. A routing line
    that doesn't look like a dispatch entry is skipped, not tallied; a line
    that does look like one but names no recognizable slug/tier still
    contributes an entry (slug/tier None) rather than being dropped, so
    legacy-format records never crash the parse.
    """
    entries = []
    kernel_synthesis = False
    gates_inline = False
    if not body:
        return {"entries": entries, "kernel_synthesis": False, "gates_inline": False}

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line == "(pending)":
            continue
        lower = line.lower()
        if "kernel synthesis" in lower:
            kernel_synthesis = True
        if GATE_INLINE_RE.search(line) or "inline (kernel)" in lower:
            gates_inline = True
        if not ROUTING_ENTRY_RE.match(line):
            continue
        entries.append(
            {
                "slug": _find_slug(_dispatch_target_text(line)),
                "tier": _dispatch_tier(line),
            }
        )

    return {
        "entries": entries,
        "kernel_synthesis": kernel_synthesis,
        "gates_inline": gates_inline,
    }


def _verify_mode(tier_field, routing, attempt_stats):
    if attempt_stats["sampling_audit"]:
        return "sampling"
    if attempt_stats["low_risk_qualified"]:
        return "low-risk"
    if routing["kernel_synthesis"]:
        return "kernel-synthesis"
    if routing["gates_inline"] or (
        tier_field == "trivial" and not attempt_stats["verify_verdicts"]
    ):
        return "gates-inline"
    if attempt_stats["verify_verdicts"]:
        return "verifier"
    return "pending"


def parse_consensus_rollout(body):
    """Parse one strict consensus-rollout ledger line, or return None.

    The line records P0/P1 REJECT ids only.  ``*-resolved`` is the number
    of those ids closed by that critique; cost is provider-invocation units
    and latency is elapsed milliseconds.  A malformed or absent record is
    deliberately ignored: unlike Attempt logs, the consensus ledger has no
    whole-section coverage contract yet, so telemetry must not fabricate a
    zero-valued escalation from partial prose.
    """
    if not body:
        return None
    records = []
    for raw_line in body.splitlines():
        match = CONSENSUS_ROLLOUT_RE.match(raw_line.strip())
        if not match:
            continue
        values = [int(value) for value in match.groups()[:4]]
        values.extend(int(value) for value in match.groups()[5:])
        c1_rejects, c1_resolved, c2_rejects, c2_resolved, baseline_cost, \
            consensus_cost, baseline_latency, consensus_latency = values
        records.append({
            "c1_rejects": c1_rejects,
            "c1_resolved": c1_resolved,
            "c2_rejects": c2_rejects,
            "c2_resolved": c2_resolved,
            "cap_out": match.group(5) == "yes",
            "baseline_cost": baseline_cost,
            "consensus_cost": consensus_cost,
            "baseline_latency_ms": baseline_latency,
            "consensus_latency_ms": consensus_latency,
        })
    # A ledger invocation writes exactly one summary line.  Treat duplicate
    # summaries as malformed rather than silently selecting one.
    return records[0] if len(records) == 1 else None


def _empty_consensus_rollout():
    return {
        "escalations": 0,
        "cap_outs": 0,
        "cap_out_rate": None,
        "judge_yield": {
            "c1": {"rejects": 0, "resolved": 0, "rate": None},
            "c2": {"rejects": 0, "resolved": 0, "rate": None},
        },
        "cost_vs_single_pass": {"baseline": 0, "consensus": 0, "delta": 0, "ratio": None},
        "latency_ms_vs_single_pass": {"baseline": 0, "consensus": 0, "delta": 0, "ratio": None},
    }


def _accumulate_consensus_rollout(metrics, record):
    metrics["escalations"] += 1
    metrics["cap_outs"] += int(record["cap_out"])
    for critique in ("c1", "c2"):
        yield_ = metrics["judge_yield"][critique]
        yield_["rejects"] += record[f"{critique}_rejects"]
        yield_["resolved"] += record[f"{critique}_resolved"]
    for key, prefix in (("cost_vs_single_pass", "cost"),
                        ("latency_ms_vs_single_pass", "latency")):
        metric = metrics[key]
        metric["baseline"] += record[f"baseline_{prefix}" + ("_ms" if prefix == "latency" else "")]
        metric["consensus"] += record[f"consensus_{prefix}" + ("_ms" if prefix == "latency" else "")]


def _finalize_consensus_rollout(metrics):
    if metrics["escalations"]:
        metrics["cap_out_rate"] = metrics["cap_outs"] / metrics["escalations"]
    for yield_ in metrics["judge_yield"].values():
        if yield_["rejects"]:
            yield_["rate"] = yield_["resolved"] / yield_["rejects"]
    for key in ("cost_vs_single_pass", "latency_ms_vs_single_pass"):
        metric = metrics[key]
        metric["delta"] = metric["consensus"] - metric["baseline"]
        if metric["baseline"]:
            metric["ratio"] = metric["consensus"] / metric["baseline"]


def aggregate(task_dir):
    """Read every *.md task file in `task_dir`, aggregate telemetry, return
    a plain-dict report. Read-only: never writes or transitions a task.
    Missing/empty directories yield a clean, all-zero report rather than
    raising.
    """
    task_dir = pathlib.Path(task_dir)
    report = {
        "tasks_scanned": 0,
        "attempt_lines_parsed": 0,
        "attempt_lines_unparsed": 0,
        "agent_dispatch_counts": {},
        "first_attempt": {"pass": 0, "total": 0},
        "bounces": {"MECHANICAL": 0, "JUDGMENT": 0, "untagged": 0, "total": 0},
        "verify_mode_counts": {},
        "tier_counts": {},
        "escalate_count": 0,
        "judge_yield": {},  # slug -> {raised, survived, changed, verdicts}
        # fg-c0106 (spec-e8a3 Phase 1): the same funnel, bucketed by
        # provider instead of exact slug -- "codex" for every
        # "codex:<agent-slug>" line, "claude" for every bare (no-prefix)
        # line, aggregated separately from per-Claude-agent yield above.
        "judge_yield_by_provider": {},  # provider -> {raised, survived, changed, verdicts}
        # fg-a10212: MEASURED per-spawn token totals from the `[tokens: ...]`
        # Attempt-log suffix -- deliberately separate from any relative-cost
        # ESTIMATE (docs/audits/2026-07-18-protocol-overhead-audit.md, A.3),
        # which this module has never computed and does not start computing
        # here. "measured" sums real harness-reported counts only.
        "tokens": {
            "measured": {"build": 0, "verify": 0, "bounce": 0, "total": 0},
            "unreported": 0,  # spawns that completed with no harness number
            "lines_with_tokens": 0,  # numeric + unreported suffix lines
            "per_slug": {},  # slug -> {build, verify, bounce, total}
        },
        "consensus_rollout": _empty_consensus_rollout(),
    }

    try:
        paths = sorted(
            p for p in task_dir.glob("*.md") if p.is_file() and p.stat().st_size > 0
        )
    except OSError:
        paths = []

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        fm, _fm_errors, body = validate_task._parse_frontmatter(text)
        if fm is None or body is None:
            continue
        report["tasks_scanned"] += 1

        tier_field = fm.get("tier")
        report["tier_counts"][tier_field] = report["tier_counts"].get(tier_field, 0) + 1

        routing_body = validate_task._section_body(body, "## Routing record") or ""
        attempt_body = validate_task._section_body(body, "## Attempt log") or ""
        consensus_body = validate_task._section_body(body, "## Plan consensus record") or ""

        routing = parse_routing_record(routing_body)
        attempt_stats = parse_attempt_log(attempt_body)

        report["attempt_lines_parsed"] += attempt_stats["parsed"]
        report["attempt_lines_unparsed"] += attempt_stats["unparsed"]

        for entry in routing["entries"]:
            slug = entry["slug"]
            if slug:
                report["agent_dispatch_counts"][slug] = (
                    report["agent_dispatch_counts"].get(slug, 0) + 1
                )

        first = next(
            (
                v
                for v in attempt_stats["verify_verdicts"]
                if v["attempt"] == 1 and v["kind"] != "re-verify"
            ),
            None,
        )
        if first and first["verdict"] in ("PASS", "FAIL"):
            report["first_attempt"]["total"] += 1
            if first["verdict"] == "PASS":
                report["first_attempt"]["pass"] += 1

        for b in attempt_stats["bounces"]:
            report["bounces"]["total"] += 1
            tag = b["tag"] or "untagged"
            report["bounces"][tag] = report["bounces"].get(tag, 0) + 1

        report["escalate_count"] += sum(
            1 for v in attempt_stats["verify_verdicts"] if v["verdict"] == "ESCALATE"
        )

        for jy in attempt_stats["judge_yields"]:
            bucket = report["judge_yield"].setdefault(
                jy["slug"], {"raised": 0, "survived": 0, "changed": 0, "verdicts": 0}
            )
            bucket["raised"] += jy["raised"]
            bucket["survived"] += jy["survived"]
            bucket["changed"] += jy["changed"]
            bucket["verdicts"] += 1
            # fg-a10911: sum the optional p0-p3 severity suffix per-slug.
            # The "severity" key is added to a bucket ONLY the first time a
            # judge-yield line for that slug carries it -- a slug whose
            # every judge-yield line omits the suffix keeps the exact same
            # 4-key bucket shape telemetry has always produced (backward
            # compatibility with no-suffix judge-yield lines).
            severity = jy.get("severity")
            if severity:
                bucket.setdefault(
                    "severity", {"p0": 0, "p1": 0, "p2": 0, "p3": 0}
                )
                for level in ("p0", "p1", "p2", "p3"):
                    bucket["severity"][level] += severity[level]

            # fg-c0106: provider-bucket rollup -- "codex:forge-verifier" and
            # "codex:forge-security" both roll into the "codex" bucket; a
            # bare "forge-verifier" rolls into "claude". Summed independent
            # of the exact-slug bucket above, never replacing it.
            provider = jy["slug"].split(":", 1)[0] if ":" in jy["slug"] else "claude"
            pbucket = report["judge_yield_by_provider"].setdefault(
                provider, {"raised": 0, "survived": 0, "changed": 0, "verdicts": 0}
            )
            pbucket["raised"] += jy["raised"]
            pbucket["survived"] += jy["survived"]
            pbucket["changed"] += jy["changed"]
            pbucket["verdicts"] += 1

        mode = _verify_mode(tier_field, routing, attempt_stats)
        report["verify_mode_counts"][mode] = report["verify_mode_counts"].get(mode, 0) + 1

        _accumulate_tokens(report["tokens"], routing, attempt_stats)
        consensus_record = parse_consensus_rollout(consensus_body)
        if consensus_record:
            _accumulate_consensus_rollout(report["consensus_rollout"], consensus_record)

    _finalize_consensus_rollout(report["consensus_rollout"])
    return report


# fg-a10212: (layer name, attempt_stats key) -- the three completion-line
# shapes a `[tokens: ...]` suffix can attach to, per "Token capture —
# 2026-07-19" (amends "Telemetry vocabulary — 2026-07"). judge-yield lines
# are a separate accounting instrument (fg-a10901/fg-a10911), not a spawn-
# completion narrative line, so they are deliberately excluded here.
_TOKEN_LAYERS = (
    ("build", "dispatches"),
    ("verify", "verify_verdicts"),
    ("bounce", "bounces"),
)


def _accumulate_tokens(tokens_report, routing, attempt_stats):
    """Fold one task's `[tokens: ...]` suffixes into `tokens_report` (the
    `report["tokens"]` dict `aggregate` builds), split by layer (build /
    verify / bounce) and attributed per-slug using the SAME Routing-record
    entries `agent_dispatch_counts` already uses -- a task's measured totals
    are added to every slug named in its Routing record, mirroring that
    existing attribution rather than inventing a new per-attempt join.
    """
    task_layers = {"build": 0, "verify": 0, "bounce": 0}
    for layer, key in _TOKEN_LAYERS:
        for entry in attempt_stats[key]:
            t = entry.get("tokens")
            if isinstance(t, int):
                task_layers[layer] += t
                tokens_report["lines_with_tokens"] += 1
            elif t == "unreported":
                tokens_report["unreported"] += 1
                tokens_report["lines_with_tokens"] += 1

    task_total = sum(task_layers.values())
    for layer, n in task_layers.items():
        tokens_report["measured"][layer] += n
    tokens_report["measured"]["total"] += task_total

    if not task_total:
        return
    for entry in routing["entries"]:
        slug = entry["slug"]
        if not slug:
            continue
        bucket = tokens_report["per_slug"].setdefault(
            slug, {"build": 0, "verify": 0, "bounce": 0, "total": 0}
        )
        for layer, n in task_layers.items():
            bucket[layer] += n
        bucket["total"] += task_total


# --- Routing-tuning recommendations (fg-a10102, Evolve analogue) ----------
#
# Builds ON the aggregates above (per-agent-slug dispatch counts from
# parse_routing_record, first-attempt verdicts + bounces from
# parse_attempt_log) -- no new parsing. Thresholds are canonically stated
# once in docs/conventions.md, "Routing-tuning recommendations (Evolve
# analogue) — 2026-07" (NORMATIVE, changeable only by human edit of that
# section); keep these two constants in sync with it.
RECOMMEND_MIN_DISPATCHES = 5
RECOMMEND_MIN_FAIL_RATE = 0.40

# The routed model ladder is haiku -> sonnet -> opus, opus is the hard
# ceiling. `fable` is a human-authorized escalation, never a route
# (docs/conventions.md, "Model vocabulary — fable amendment (2026-07-17)")
# -- it is deliberately absent from this ladder so a recommendation can
# NEVER suggest it, no matter how bad a pairing's numbers are.
_MODEL_LADDER = ["haiku", "sonnet", "opus"]
_EFFORT_LADDER = ["low", "medium", "high"]


def _next_tier_up(tier):
    """Given a routed "<model>/<effort>" tier, return the next tier up the
    ladder, or None if already at the ceiling (opus at its highest effort,
    OR a fable/* input -- see below).

    Model bumps first (same effort carried across), then -- once at opus --
    effort bumps. Never returns anything outside haiku|sonnet|opus (never
    fable; see the module-level ladder comment above).

    fable/* is a HARD CEILING, not a rung on the ladder: fable is a human-
    authorized escalation (docs/conventions.md, "Model vocabulary -- fable
    amendment"), never a routing target, so a pairing that was itself
    dispatched at fable/<effort> (a human overrode the router) has nowhere
    automated left to recommend -- it is treated exactly like the opus/high
    ceiling and yields None, regardless of effort. This guarantees fable can
    NEVER appear as an output tier, matching the never-fable invariant this
    function's own comment asserts (fg-a10502).
    """
    model, _, effort = tier.partition("/")
    if model == "fable":
        return None  # already past the automated ceiling; never escalate further
    if model in _MODEL_LADDER and model != _MODEL_LADDER[-1]:
        next_model = _MODEL_LADDER[_MODEL_LADDER.index(model) + 1]
        return f"{next_model}/{effort}"
    if effort in _EFFORT_LADDER and effort != _EFFORT_LADDER[-1]:
        next_effort = _EFFORT_LADDER[_EFFORT_LADDER.index(effort) + 1]
        return f"{model}/{next_effort}"
    return None  # already at the ceiling: opus at its highest effort


def compute_pairing_stats(task_dir):
    """Cross-tab each task's routed (slug, tier) pairing -- taken from the
    FIRST entry in its Routing record, i.e. the tier it was actually
    dispatched at -- against whether that task's first attempt was a
    FAIL-or-bounce. Read-only; never writes or transitions a task.

    Reuses parse_routing_record/parse_attempt_log verbatim (fg-a10101) --
    this is a new aggregation over the same per-task parse, not new parsing.
    """
    task_dir = pathlib.Path(task_dir)
    pairings = {}  # (slug, tier) -> {"dispatches": int, "fail_or_bounce": int}

    try:
        paths = sorted(
            p for p in task_dir.glob("*.md") if p.is_file() and p.stat().st_size > 0
        )
    except OSError:
        paths = []

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        fm, _fm_errors, body = validate_task._parse_frontmatter(text)
        if fm is None or body is None:
            continue

        routing_body = validate_task._section_body(body, "## Routing record") or ""
        attempt_body = validate_task._section_body(body, "## Attempt log") or ""

        routing = parse_routing_record(routing_body)
        attempt_stats = parse_attempt_log(attempt_body)

        first_entry = routing["entries"][0] if routing["entries"] else None
        if not first_entry or not first_entry["slug"] or not first_entry["tier"]:
            continue  # inline/kernel-synthesis/legacy entries carry no tier

        key = (first_entry["slug"], first_entry["tier"])

        first_verdict = next(
            (
                v
                for v in attempt_stats["verify_verdicts"]
                if v["attempt"] == 1 and v["kind"] != "re-verify"
            ),
            None,
        )
        failed_first = bool(first_verdict and first_verdict["verdict"] == "FAIL")
        bounced = bool(attempt_stats["bounces"])

        stats = pairings.setdefault(key, {"dispatches": 0, "fail_or_bounce": 0})
        stats["dispatches"] += 1
        if failed_first or bounced:
            stats["fail_or_bounce"] += 1

    return pairings


def compute_recommendations(task_dir):
    """Return the list of qualifying routing-tuning recommendations: pairings
    with >= RECOMMEND_MIN_DISPATCHES dispatches AND a first-attempt
    FAIL-or-bounce rate >= RECOMMEND_MIN_FAIL_RATE. Each recommendation
    carries its counts (honesty rule -- a recommendation never hides the
    numbers behind it) and the suggested next tier up (None means already
    at the opus/high ceiling).
    """
    pairings = compute_pairing_stats(task_dir)
    recs = []
    for (slug, tier), stats in sorted(pairings.items()):
        dispatches = stats["dispatches"]
        if dispatches < RECOMMEND_MIN_DISPATCHES:
            continue
        fail_or_bounce = stats["fail_or_bounce"]
        rate = fail_or_bounce / dispatches
        if rate < RECOMMEND_MIN_FAIL_RATE:
            continue
        recs.append(
            {
                "slug": slug,
                "tier": tier,
                "dispatches": dispatches,
                "fail_or_bounce": fail_or_bounce,
                "rate": rate,
                "next_tier": _next_tier_up(tier),
            }
        )
    return recs


def render_recommendations(recs):
    if not recs:
        return (
            "no recommendations\n"
            f"(thresholds: dispatches >= {RECOMMEND_MIN_DISPATCHES}, "
            f"first-attempt FAIL-or-bounce rate >= "
            f"{int(RECOMMEND_MIN_FAIL_RATE * 100)}%)"
        )

    lines = []
    for r in recs:
        pct = 100.0 * r["rate"]
        lines.append(
            f"{r['slug']} {r['tier']}: {r['fail_or_bounce']}/{r['dispatches']} "
            f"first-attempt FAIL-or-bounce ({pct:.1f}%, "
            f">= {RECOMMEND_MIN_DISPATCHES} dispatches / "
            f">= {int(RECOMMEND_MIN_FAIL_RATE * 100)}% threshold)"
        )
        if r["next_tier"]:
            lines.append(f"  -> recommend {r['next_tier']} for this class")
        else:
            lines.append(
                "  -> already at ceiling — investigate task-class instead"
            )
    return "\n".join(lines)


def _coverage_line(report):
    return (
        f"{report['attempt_lines_parsed']} attempt-lines parsed, "
        f"{report['attempt_lines_unparsed']} unparsed"
    )


def render_table(report):
    lines = []
    lines.append(f"Forge telemetry -- {report['tasks_scanned']} task(s) scanned")
    lines.append(_coverage_line(report))
    lines.append("")

    lines.append("Per-agent-slug dispatch counts:")
    counts = report["agent_dispatch_counts"]
    if counts:
        width = max(len(s) for s in counts) + 2
        for slug, n in sorted(counts.items()):
            lines.append(f"  {slug:<{width}}{n}")
    else:
        lines.append("  (none)")
    lines.append("")

    fa = report["first_attempt"]
    if fa["total"]:
        pct = 100.0 * fa["pass"] / fa["total"]
        lines.append(f"First-attempt PASS rate: {fa['pass']}/{fa['total']} ({pct:.1f}%)")
    else:
        lines.append("First-attempt PASS rate: n/a (0 first-attempt verdicts)")
    lines.append("")

    b = report["bounces"]
    lines.append(
        f"Bounce tally: {b['total']} total "
        f"(MECHANICAL {b.get('MECHANICAL', 0)}, "
        f"JUDGMENT {b.get('JUDGMENT', 0)}, "
        f"untagged {b.get('untagged', 0)})"
    )
    lines.append("")

    lines.append("Verify-mode distribution (gates-inline / verifier / "
                  "kernel-synthesis / low-risk / sampling):")
    modes = report["verify_mode_counts"]
    if modes:
        width = max(len(m) for m in modes) + 2
        for mode, n in sorted(modes.items()):
            lines.append(f"  {mode:<{width}}{n}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Per-tier counts:")
    tiers = report["tier_counts"]
    if tiers:
        for tier, n in sorted(tiers.items(), key=lambda kv: (kv[0] is None, str(kv[0]))):
            lines.append(f"  {str(tier):<12}{n}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append(f"ESCALATE occurrences: {report['escalate_count']}")
    lines.append("")

    consensus = report["consensus_rollout"]
    lines.append("Consensus rollout (ledger-backed):")
    if consensus["escalations"]:
        lines.append(
            f"  cap-out rate: {consensus['cap_outs']}/{consensus['escalations']} "
            f"({100 * consensus['cap_out_rate']:.1f}%)"
        )
        for critique in ("c1", "c2"):
            yield_ = consensus["judge_yield"][critique]
            rate = "n/a" if yield_["rate"] is None else f"{100 * yield_['rate']:.1f}%"
            lines.append(
                f"  {critique.upper()} judge yield: {yield_['resolved']}/"
                f"{yield_['rejects']} ({rate})"
            )
        for label, metric in (("cost", consensus["cost_vs_single_pass"]),
                              ("latency ms", consensus["latency_ms_vs_single_pass"])):
            ratio = "n/a" if metric["ratio"] is None else f"{metric['ratio']:.2f}x"
            lines.append(
                f"  {label} vs single-pass: {metric['consensus']}/"
                f"{metric['baseline']} (delta {metric['delta']}, {ratio})"
            )
    else:
        lines.append("  n/a (0 ledger records)")
    lines.append("")

    # fg-a10212: MEASURED (real harness-reported counts) -- labeled plainly
    # so it is never mistaken for the audit's earlier relative-cost ESTIMATE
    # (docs/audits/2026-07-18-protocol-overhead-audit.md, A.3), which this
    # module has never computed.
    lines.append("Token usage -- MEASURED, not the legacy relative-cost estimate "
                  "(build/verify/bounce):")
    tok = report.get("tokens", {})
    measured = tok.get("measured", {})
    if tok.get("lines_with_tokens"):
        lines.append(
            f"  build {measured.get('build', 0)}, verify {measured.get('verify', 0)}, "
            f"bounce {measured.get('bounce', 0)}, total {measured.get('total', 0)} "
            f"({tok.get('lines_with_tokens', 0)} suffixed line(s), "
            f"{tok.get('unreported', 0)} unreported)"
        )
        per_slug = tok.get("per_slug", {})
        if per_slug:
            width = max(len(s) for s in per_slug) + 2
            for slug, v in sorted(per_slug.items()):
                lines.append(
                    f"    {slug:<{width}}build {v['build']}, verify {v['verify']}, "
                    f"bounce {v['bounce']}, total {v['total']}"
                )
    else:
        lines.append("  (none recorded -- no Attempt-log line carries a "
                      "[tokens: ...] suffix yet)")
    lines.append("")

    lines.append("Judge yield (raised -> survived filter -> changed outcome):")
    jy = report.get("judge_yield", {})
    if jy:
        width = max(len(s) for s in jy) + 2
        for slug, v in sorted(jy.items()):
            line = (
                f"  {slug:<{width}}{v['raised']} -> {v['survived']} -> "
                f"{v['changed']}  ({v['verdicts']} verdict(s))"
            )
            # fg-a10911: show the p0-p3 severity distribution only when a
            # nonzero count was actually recorded for this slug -- a slug
            # with no severity data (all judge-yield lines pre-date the
            # suffix, or the suffix was all-zero) renders exactly as before.
            sev = v.get("severity")
            if sev and any(sev.values()):
                line += (
                    f"  [P0={sev['p0']} P1={sev['p1']} "
                    f"P2={sev['p2']} P3={sev['p3']}]"
                )
            lines.append(line)
    else:
        lines.append("  (none recorded)")

    # fg-c0106 (spec-e8a3 Phase 1): per-provider rollup, distinct from the
    # per-exact-slug table above -- "codex" (every codex:<slug> line summed)
    # vs. "claude" (every bare, no-prefix line summed).
    lines.append("")
    lines.append("Judge yield by provider (raised -> survived filter -> changed outcome):")
    jyp = report.get("judge_yield_by_provider", {})
    if jyp:
        width = max(len(p) for p in jyp) + 2
        for provider, v in sorted(jyp.items()):
            lines.append(
                f"  {provider:<{width}}{v['raised']} -> {v['survived']} -> "
                f"{v['changed']}  ({v['verdicts']} verdict(s))"
            )
    else:
        lines.append("  (none recorded)")

    return "\n".join(lines)


def main(argv):
    as_json = "--json" in argv
    task_dir = TASK_DIR_DEFAULT
    if "--dir" in argv:
        i = argv.index("--dir")
        if i + 1 < len(argv):
            task_dir = argv[i + 1]

    if "--recommend" in argv:
        recs = compute_recommendations(task_dir)
        if as_json:
            print(json.dumps(recs, indent=2, sort_keys=True))
        else:
            print(render_recommendations(recs))
        return 0  # read-only reporter: always exits 0 on a valid run

    report = aggregate(task_dir)

    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_table(report))

    return 0  # read-only reporter: always exits 0 on a valid run


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
