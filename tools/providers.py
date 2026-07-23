# tools/providers.py
"""Non-mutating provider CLI availability + authed-state detection.

Binding contract: spec-e8a3 (.forge/specs/2026-07-19-provider-profiles.md),
sections "Per-repo opt-in and per-provider trust" and "Provider-specific
enablement gates", and the spec's Risks section (credential-leak
mitigation). This module is the `tools/providers.py` the Risks section
names as the enforcement point for "never place a credential in job/env
vars" -- read that spec before changing the rules below.

Scope of THIS task (fg-c0102 / bm-provider-cli-detection): DETECTION ONLY.
- installed?  -> `shutil.which(<cli>)`
- authed?     -> the provider's own non-mutating "login status"-equivalent
                 probe, parsed from exit code / stdout, never interactive.

Codex is the only provider with a real probe here (spec: "PRIMARY,
fully-enabled-at-ship target ... `codex login status` for the
non-mutating auth probe"). Grok and Antigravity are DETECTION-ONLY STUBS:
the spec hard-gates both behind their own pilot-test tasks
(bm-grok-pilot-test / bm-antigravity-smoke-test) before any real dispatch,
so this task ships no dispatch code and no real authed-probe for either --
just an `installed` check plus a stub `detail` explaining the gate.

HARD RULES (normative, restated from spec-e8a3's Risks section -- this
module is the enforcement point, not just a description of intent):
  1. This module never reads, stores, requests, transmits, or forwards any
     credential, API key, or token value. It has no parameter, return
     field, or local variable that ever holds one.
  2. This module never constructs an env block (a `dict` passed as a
     subprocess "env" keyword argument) containing a key/token-shaped
     value. Every probe below invokes the CLI with the INHERITED
     environment, in place -- no "env" keyword argument is passed to
     subprocess at all, anywhere in this file.
  3. Every probe is non-mutating: `login status`-equivalent checks only,
     never `login`, `logout`, or any state-changing subcommand.
  4. Every subprocess call is bounded by a 5-second timeout. A timeout
     produces a clean, typed result with an explanatory `detail` -- never
     a hang, never an uncaught exception propagating to the caller.

Public surface: detect(provider) -> dict with keys
  installed: bool
  authed:    bool | None   (None = unknown/not probed, e.g. not installed
                             or a detection-only stub)
  version:   str | None    (currently always None -- no provider probe
                             below parses a version string; reserved for a
                             future task, never fabricated here)
  detail:    str           (human-readable explanation, always present)

Stdlib-only. Zero third-party dependencies.
"""
import shutil
import subprocess
import sys

PROBE_TIMEOUT_SECONDS = 5

# CLI executable name per provider, per spec-e8a3's pinned invocation
# shapes ("Provider-specific enablement gates").
_CLI_NAME = {
    "codex": "codex",
    "grok": "grok",
    "antigravity": "antigravity",
}

# Providers gated behind their own pilot-test task (spec-e8a3 Non-goals +
# "Provider-specific enablement gates"): detection-only until a human
# reviews that task's evidence. Never used for dispatch by this module --
# this module ships no dispatch code at all.
_PILOT_GATED_DETAIL = {
    "grok": (
        "grok CLI detection-only: real dispatch is gated behind "
        "bm-grok-pilot-test (fg-c0104) confirming the non-interactive "
        "auth path and subscription rate-cap shape; no authed probe is "
        "run until a human reviews docs/pilots/2026-07-19-grok-pilot.md "
        "(auth path confirmed via XAI_API_KEY env var / "
        "`grok login --device-auth`; rate-cap numeric shape still "
        "unconfirmed)."
    ),
    "antigravity": (
        "antigravity CLI detection-only: real dispatch is gated behind "
        "bm-antigravity-smoke-test (fg-c0105) clearing reported non-TTY "
        "stdout/hang behavior; no authed probe is run until that smoke "
        "test lands."
    ),
}


def _empty_result(detail):
    return {"installed": False, "authed": None, "version": None, "detail": detail}


def _run_probe(argv):
    """Run a non-mutating probe subprocess with the inherited environment.

    No "env" keyword argument is ever passed -- the subprocess inherits this
    process's environment in place, exactly as hard rule 2 above requires.
    Returns (returncode, stdout, stderr) on completion, or None on
    timeout/launch failure (caller decides the resulting `detail`).
    """
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return None
    return (proc.returncode, proc.stdout or "", proc.stderr or "")


def _detect_codex(which_path):
    result = _run_probe([which_path, "login", "status"])
    if result is None:
        return {
            "installed": True,
            "authed": None,
            "version": None,
            "detail": (
                "codex found at "
                f"{which_path} but `codex login status` timed out after "
                f"{PROBE_TIMEOUT_SECONDS}s or failed to launch; authed "
                "state unknown"
            ),
        }
    returncode, stdout, stderr = result
    output = (stdout + stderr).strip()
    if returncode == 0:
        return {
            "installed": True,
            "authed": True,
            "version": None,
            "detail": f"codex login status: logged in ({output or 'exit 0'})",
        }
    return {
        "installed": True,
        "authed": False,
        "version": None,
        "detail": (
            f"codex login status: not logged in (exit {returncode}; "
            f"{output or 'no output'})"
        ),
    }


def _detect_pilot_gated(provider, which_path):
    return {
        "installed": True,
        "authed": None,
        "version": None,
        "detail": _PILOT_GATED_DETAIL[provider],
    }


def detect(provider):
    """Return a non-mutating installed/authed detection result for
    `provider` ("codex", "grok", or "antigravity").

    Never accepts a credential parameter of any kind -- there is nothing
    to authenticate WITH here, only a query of the CLI's own already-
    established local session state (spec-e8a3: "auth is exclusively the
    provider CLI's own flow and its own local session state").
    """
    if provider not in _CLI_NAME:
        return _empty_result(
            f"unknown provider {provider!r}; expected one of "
            f"{sorted(_CLI_NAME)}"
        )

    which_path = shutil.which(_CLI_NAME[provider])
    if which_path is None:
        return _empty_result(
            f"{_CLI_NAME[provider]} CLI not found on PATH; not installed"
        )

    if provider == "codex":
        return _detect_codex(which_path)

    # grok / antigravity: detection-only stubs (pilot-gated, see module
    # docstring). No authed probe is run for either.
    return _detect_pilot_gated(provider, which_path)


def main(argv):
    providers = argv or ["codex", "grok", "antigravity"]
    exit_code = 0
    for provider in providers:
        result = detect(provider)
        print(f"{provider}: {result}")
        if provider not in _CLI_NAME:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
