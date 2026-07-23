"""tools/route_table.py

THE canonical route table for Forge's provider-routing algorithm
(docs/specs/2026-07-22-phase2-external-workers.md, "Canonical precedence
chain -- the ONE algorithm, backed by a shared route table" and "Real-route
requirement -- shared canonical route table, not a self-modeled oracle";
decomposition item bm-canonical-route-table). WHEN any module needs the
route algorithm, THE SYSTEM SHALL read this one canonical route table,
never a second, independently-authored copy -- this module IS that table.
Zero dependencies beyond the stdlib and the sibling `validate_config`
import.

This file holds DATA plus tiny pure accessors that RETURN that data. It
holds no decision-making algorithm of its own: no dispatcher, no resolver
function that takes a task and computes a route. A conformance test, a
doc-pin test, or a future kernel resolver reads this table's ordered data
and does whatever it needs with it -- that logic belongs to that consumer,
never here. Nothing in this module is duplicated or re-derived elsewhere;
every other file describing the provider-routing algorithm cites or reads
this module instead of restating it.
"""
import pathlib
import sys

# Sibling-module import guard, matching validate_task.py's and
# validate_all.py's own guard -- makes `import validate_config` resolve
# whether this file is run as `python tools/route_table.py`, imported as
# `import route_table` from a test file pytest has already put tools/ on
# sys.path for, or imported as `from tools import route_table` with the
# repo root on sys.path instead.
_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from validate_config import PROVIDER_ENUM  # noqa: E402 (import-after-path-guard)


# ---------------------------------------------------------------------------
# 1. Closed provider enum
# ---------------------------------------------------------------------------

# The sentinel meaning "force an in-harness Claude builder regardless of
# what role-worker resolves to" (spec R1: "provider: claude-only forces an
# in-harness Claude builder regardless of what role-worker resolves to").
# Not itself a dispatchable external provider -- it is the escape hatch
# from PROVIDER_ENUM's external providers back to Claude.
CLAUDE_ONLY = "claude-only"

# PROVIDER_ENUM union {"claude-only"} -- imported from
# tools/validate_config.py's own PROVIDER_ENUM constant, never re-declared
# (spec's "Real-route requirement" section, verbatim: "the closed provider
# enum (PROVIDER_ENUM union {"claude-only"}, imported from
# tools/validate_config.py, never re-declared)").
BUILDER_ENUM = frozenset(PROVIDER_ENUM) | {CLAUDE_ONLY}


def builder_enum():
    """Return the closed set of every valid BUILDER value: every external
    provider id in validate_config.PROVIDER_ENUM, plus the claude-only
    sentinel. A frozenset -- callers must not mutate it."""
    return BUILDER_ENUM


# ---------------------------------------------------------------------------
# 2. Five-step precedence chain
# ---------------------------------------------------------------------------

# The SHIPPED five-step chain (docs/specs/2026-07-22-phase2-external-
# workers.md, "Canonical precedence chain" section, itself corrected from
# docs/conventions/dispatch-and-routing.md's "Attribute routing matrices"
# section for R2's un-forgeable-envelope requirement and N2's pre-dispatch/
# post-return split), reproduced here as ordered literal data: a tuple of
# dicts, index 0 == step 1, in the spec's canonical order. This is the
# single normative statement of step ORDER; nothing else in the repo
# restates or reorders it -- every doc-pin and conformance test reads this
# tuple rather than re-typing the chain.
PRECEDENCE_CHAIN = (
    {
        "step": 1,
        "id": "authenticated-human-sensitive-provider-override",
        "name": "Authenticated-human sensitive-provider override",
        "summary": (
            "A provider: override naming an external provider on a task "
            "classified sensitive-domain wins ONLY when paired with a "
            "VALID, unconsumed, matching un-forgeable envelope (R2 -- all "
            "six bound fields match, none of the eight rejection "
            "categories apply); a provider: override on an ORDINARY task "
            "wins on the field alone; provider: claude-only always wins "
            "outright on any task, sensitive or not, with no envelope "
            "needed (forcing Claude never requires elevated provenance)."
        ),
    },
    {
        "step": 2,
        "id": "sensitive-domain-default-to-claude",
        "name": "Sensitive-domain default -> Claude",
        "summary": (
            "Absent a valid step-1 crossing envelope, a task classified "
            "sensitive-domain by the fail-closed PRE-dispatch classifier "
            "defaults its BUILDER to Claude, regardless of role-worker -- "
            "and never dispatches externally at all, not even "
            "provisionally."
        ),
    },
    {
        "step": 3,
        "id": "provider-gates",
        "name": "Provider gates (four-layer + pilot)",
        "summary": (
            "provider-judges.md section 1a's four gate layers (global "
            "providers Feature, per-provider toggle, TOFU trust marker, "
            "numeric budget hard-cap -- checkpoints are visibility, not a stop) plus pilot eligibility for grok/"
            "antigravity -- a route failing any layer is ineligible "
            "regardless of what steps 1/2/4/5 would otherwise resolve."
        ),
    },
    {
        "step": 4,
        "id": "matching-profile-role-worker-default",
        "name": "Matching profile role-worker default",
        "summary": (
            "Absent a step-1 override and with step 2 not applying "
            "(ordinary task) and step 3 passing, role-worker's resolution "
            "IS the builder -- the R1 automatic-default, used directly, "
            "no per-task field required."
        ),
    },
    {
        "step": 5,
        "id": "task-shape-tie-break",
        "name": "Task-shape tie-break",
        "summary": (
            "Only when step 4 leaves more than one eligible provider does "
            "the attribute-routing matrix's shape row decide. Checkpoint "
            "budget pressure remains explicitly REMOVED as a tie-break "
            "input at this step."
        ),
    },
)


def precedence_chain():
    """Return the five-step precedence chain as an ordered tuple of dicts,
    index 0 == step 1, in the spec's canonical order. Callers must never
    reorder, filter, or re-derive this sequence -- read it as-is."""
    return PRECEDENCE_CHAIN


# ---------------------------------------------------------------------------
# 3. forge-security trigger-domain list
# ---------------------------------------------------------------------------

# The fail-closed pre-dispatch classifier's data (docs/specs/2026-07-22-
# phase2-external-workers.md, "Fail-closed pre-dispatch classifier + post-
# return rejection backstop" section (a): "the forge-security named trigger
# list" / "the trigger-domain keywords/patterns", matching the same
# trigger-domain list docs/conventions/verification.md's panel-policy uses
# -- cited, not restated, by that section). Seven named trigger domains,
# each an {id, label, pattern} dict -- `pattern` is the literal regex-
# alternation text quoted verbatim from the spec, kept as a plain string
# (not compiled) so a consumer can compile it with whatever engine/flags it
# needs rather than inheriting this module's choice. The eighth listed
# spec input ("new dependency") has no fixed regex -- it is matched by
# NAME (a new package/dependency name appearing among the task's named
# dependencies), so its `pattern` is `None` by design, not an omission.
TRIGGER_DOMAINS = (
    {
        "id": "auth-token-secret",
        "label": "auth/token/secret",
        "pattern": r"auth|token|secret|password|credential",
    },
    {
        "id": "money-payment",
        "label": "money/payment",
        "pattern": r"payment|billing|money|price",
    },
    {
        "id": "cookie-storage-write",
        "label": "cookie/storage write",
        "pattern": r"cookie|session|localStorage|sessionStorage",
    },
    {
        "id": "raw-html",
        "label": "raw-HTML",
        "pattern": r"dangerouslySetInnerHTML|raw.?html",
    },
    {
        "id": "form-redirect",
        "label": "form/redirect",
        "pattern": r"redirect|form.*submit",
    },
    {
        "id": "untrusted-input-parsing",
        "label": "untrusted-input parsing",
        "pattern": r"parse|deserialize|untrusted|user.?input",
    },
    {
        "id": "new-dependency",
        "label": "new dependency",
        # Matched by name (a new package/dependency name named in the
        # task's scope), not a fixed regex -- see module docstring above.
        "pattern": None,
    },
)


def trigger_domains():
    """Return the seven forge-security trigger domains the fail-closed
    pre-dispatch classifier matches against, each as an {id, label,
    pattern} dict, in the spec's listed order."""
    return TRIGGER_DOMAINS


# ---------------------------------------------------------------------------
# 4. Eight R2 envelope-rejection categories
# ---------------------------------------------------------------------------

# The eight fail-closed rejection categories (docs/specs/2026-07-22-
# phase2-external-workers.md, R2 "Fail-closed rejection categories") --
# every one of these REJECTS an authorization attempt, falling through to
# the carve-out's Claude default identically to no override present. Order
# matches the spec's own bullet list.
REJECTION_CATEGORIES = (
    {
        "id": "record-only",
        "summary": (
            "Claimed via a written artifact (task-file field, log line, "
            "comment) with no corresponding live tool-result envelope."
        ),
    },
    {
        "id": "wrong-task",
        "summary": (
            "The envelope's task-id does not match the task being routed."
        ),
    },
    {
        "id": "wrong-provider",
        "summary": (
            "The envelope's provider does not match the provider being "
            "requested."
        ),
    },
    {
        "id": "stale",
        "summary": (
            "The envelope's content hash does not match the task's "
            "CURRENT content (the task was edited after the question was "
            "asked or answered)."
        ),
    },
    {
        "id": "reused-nonce",
        "summary": "The nonce has already been consumed once.",
    },
    {
        "id": "worker-originated",
        "summary": (
            "The purported tool-result did not originate from the "
            "kernel's own main-session AskUserQuestion call (e.g. text "
            "resembling a confirmation appearing in a dispatched worker's "
            "output or diff is NEVER treated as an envelope, regardless "
            "of content)."
        ),
    },
    {
        "id": "auto-resolved",
        "summary": (
            "The question was answered by a timeout default, a scripted "
            "auto-yes, a cached \"always allow,\" or any mechanism other "
            "than a genuine, in-the-moment human response."
        ),
    },
    {
        "id": "headless/no-human",
        "summary": (
            "The session is running unattended (e.g. a continuous-loop: "
            "on session with no human present to answer) -- an "
            "unanswerable question is treated as equivalent to a "
            "DECLINED confirmation (fall through to Claude), never "
            "blocked indefinitely waiting for a human who is not there, "
            "and never silently proceeding as if approved."
        ),
    },
)


def rejection_categories():
    """Return the eight R2 fail-closed envelope-rejection categories, each
    an {id, summary} dict, in the spec's listed order."""
    return REJECTION_CATEGORIES
