"""Aggregate Forge queue task Routing records + Attempt logs into telemetry:
per-agent-slug dispatch counts, first-attempt PASS rate, bounce rate split by
MECHANICAL/JUDGMENT tag, verify-mode distribution, per-tier counts, and
ESCALATE occurrences. Read-only: never transitions a task. Zero dependencies.

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

TIER_RE = re.compile(r"\b(haiku|sonnet|opus|fable)/(low|medium|high)\b")
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
JUDGE_YIELD_RE = re.compile(
    r"^judge-yield:\s*([a-z][a-z0-9-]*)\s+raised=(\d+)\s+survived=(\d+)\s+changed=(\d+)"
    r"(?:\s+p0=(\d+)\s+p1=(\d+)\s+p2=(\d+)\s+p3=(\d+))?\s*$",
    re.I,
)


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
        "dispatch_count": 0,
        "verify_verdicts": [],  # [{attempt, kind, verdict, tier, tag}, ...]
        "bounces": [],  # [{attempt, tier, tag}, ...]
        "judge_yields": [],  # [{slug, raised, survived, changed}, ...]
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
        lower = line.lower()

        if "sampling audit" in lower:
            stats["sampling_audit"] = True
        if "low-risk verify: qualified" in lower:
            stats["low_risk_qualified"] = True

        if DISPATCH_RE.match(line):
            stats["parsed"] += 1
            stats["dispatch_count"] += 1
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
                    }
                )
            else:
                stats["unparsed"] += 1
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
        entries.append({"slug": _find_slug(line), "tier": _find_tier(line)})

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

        mode = _verify_mode(tier_field, routing, attempt_stats)
        report["verify_mode_counts"][mode] = report["verify_mode_counts"].get(mode, 0) + 1

    return report


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
