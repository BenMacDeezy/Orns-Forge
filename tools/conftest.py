"""Repo-wide pytest hermeticity guard for tools/ tests (fg-a10904 3rd real-
machine-incident hardening; widened again after the adversarial verify
bounce that followed the first pass of this file -- see the P0/P1/P2
findings folded in below).

BACKGROUND: three separate real-machine incidents traced back to the same
root cause -- an unhermetic test run in tools/test_banner_takeover.py or
tools/test_banner_install.py that touched the real filesystem/registry
instead of a tempfile.TemporaryDirectory()-backed fake home. The most recent
incident: a broken claude.bat containing the literal TEST-FIXTURE
placeholder path 'C:\\real\\claude.exe', plus a forge-autorun.cmd wiring it
into the real HKCU AutoRun doskey macro -- doskey beats PATH in an
interactive cmd.exe session, so this silently hijacked and broke `claude`
in every CMD window on the user's real machine.

test_banner_takeover.py originally carried its own file-local
`_hermeticity_guard` fixture (still present in that file's own history, and
covered by its `TestHermeticityGuardTripsOnRegression` meta-test) that
guarded exactly banner.py's three real-write-capable primitives
(resolve_cli_target_path, _atomic_write_bytes, _fsync_write_bytes). This
module GENERALIZES that guard to the whole tools/ package as an autouse
fixture (so every test file benefits, not just the one that happened to
define it) and WIDENS its coverage per the incident's actual shape:

  (a) banner.py's patch-engine primitives: resolve_cli_target_path,
      _atomic_write_bytes, _fsync_write_bytes, AND (added after the verify
      bounce) _write_stamp and _unlink_path -- _write_stamp used to call
      Path.write_text() directly, and restore_patch() used to call
      Path.unlink() directly on both the stamp and the journal (whose path
      is read out of the STAMP'S OWN CONTENTS, not a passed-in tmp home),
      so both were reachable by a test calling _write_stamp()/
      restore_patch() directly without ever crossing the three originally-
      guarded primitives. _write_stamp now routes through
      _fsync_write_bytes instead of writing directly; every unlink in
      apply_patch/restore_patch/recheck_patch now routes through the new
      _unlink_path helper.
  (b) Every banner_install.py entry point that can write outside a passed
      tmp home: the PowerShell/bash-rc marker-block writers
      (install_into_file/uninstall_from_file), the cmd.exe shim/AutoRun-cmd
      writer/deleter (write_shim_file/unlink_shim_file -- restore_all()'s
      tagged-shim cleanup used to call Path.unlink() directly, same class
      of gap as (a)'s journal/stamp unlinks), and install_all/restore_all
      themselves (guarded at the home= boundary they accept -- a confirmed
      install or any restore run against a real, un-tempdir'd home is
      refused immediately, before any of the finer-grained (a)/(c) guards
      would even get a chance to fire).
  (c) ALL registry access: get_autorun_value/set_autorun_value/
      delete_autorun_value are wrapped to raise AssertionError
      unconditionally -- there is no "under tmp" exception for the
      registry (it is inherently a single real global namespace, unlike a
      filesystem path) -- unless the test carries the opt-in marker below.
      No test in this suite uses that marker; the registry's pure chaining
      logic (compute_new_autorun / compute_autorun_after_uninstall) and the
      install_autorun/uninstall_autorun orchestration are fully covered via
      injected get_fn/set_fn stubs instead, exactly as before.

RESOLVER SCOPE (verify-bounce P1 fix): guarded_resolve_cli_target_path used
to only reject a resolved path under the REAL Path.home() -- a real
installed claude under C:\\Program Files, an npm global prefix, or
/usr/local would have passed through untouched and could then be READ by
patch_report()/apply_patch() from inside a test. The guard now allows ONLY
a result under the OS temp root; anything else -- home or not -- is
rejected. Every legitimate test either mocks resolve_cli_target_path
outright or resolves a target it built itself under a
tempfile.TemporaryDirectory(), so this tightening does not narrow what any
real test needs.

Every wrapper below carries a __wrapped__ attribute pointing at the real
function, so inspect.unwrap()/inspect.getsource() can still see through the
guard to pin real orchestration logic (verify-bounce P2 fix -- this used to
be inconsistent across the banner_install.py wrappers and entirely absent
from the banner.py/registry wrappers).

Opt-in escape hatch: @pytest.mark.allow_real_home_access on a test function
or class disables this fixture for that test. No test currently uses it --
it exists solely so a future, deliberately-reviewed exception has a way to
opt in VISIBLY (a marker in the test source, reviewable in a diff) rather
than by accident (a forgotten mock).

WINDOWS ORDERING NOTE: tempfile.gettempdir() (…\\AppData\\Local\\Temp) lives
UNDER the real user home directory on Windows -- so the "is this path under
the OS temp root" check must run, and be allowed to short-circuit, BEFORE
any real-home-relative check runs, or every legitimate
tempfile.TemporaryDirectory() path (which is exactly what every hermetic
test in this package uses) would false-positive and this guard would block
the very tests it exists to protect.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

import pytest

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import banner  # noqa: E402
import banner_install  # noqa: E402

_ALLOW_REAL_HOME_MARKER = "allow_real_home_access"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        f"{_ALLOW_REAL_HOME_MARKER}: opt out of the tools/ repo-wide "
        "hermeticity guard (tools/conftest.py) for a deliberate, reviewed "
        "exception. No test currently uses this marker.",
    )


def _hermeticity_violation(kind, path, allowed_root):
    return AssertionError(
        f"HERMETICITY GUARD TRIPPED ({kind}): {path} is outside the "
        f"permitted test area ({allowed_root}). This is exactly the real-"
        "machine-incident class this guard exists to prevent -- mock the "
        "resolver/writer/registry function involved, or make sure every "
        "write target and every home= is built from "
        "tempfile.TemporaryDirectory()."
    )


def _registry_violation(fn_name):
    return AssertionError(
        f"HERMETICITY GUARD TRIPPED (registry access): {fn_name}() was "
        "called against the REAL Windows registry from a test. No test may "
        "touch HKCU at all, read-only or not -- use the injected get_fn/"
        "set_fn stub pattern (see TestAutoRunOrchestrationWithStubbedRegistry) "
        "instead."
    )


@pytest.fixture(autouse=True)
def _hermeticity_guard(request):
    if request.node.get_closest_marker(_ALLOW_REAL_HOME_MARKER) is not None:
        yield
        return

    real_home = pathlib.Path.home().resolve()
    tmp_root = pathlib.Path(tempfile.gettempdir()).resolve()

    def _is_under_tmp_root(resolved):
        # See the module docstring's WINDOWS ORDERING NOTE: this check must
        # run, and be allowed to short-circuit, before any real-home-
        # relative check below.
        return resolved == tmp_root or tmp_root in resolved.parents

    def _assert_safe_write_target(path):
        resolved = pathlib.Path(path).resolve()
        if _is_under_tmp_root(resolved):
            return
        if resolved == real_home or real_home in resolved.parents:
            raise _hermeticity_violation("write under real home", resolved, real_home)
        raise _hermeticity_violation("write outside OS temp dir", resolved, tmp_root)

    def _assert_safe_home(home):
        resolved = (pathlib.Path(home) if home else real_home).resolve()
        if _is_under_tmp_root(resolved):
            return
        raise _hermeticity_violation(
            "home= outside OS temp dir (None defaults to the real home)",
            resolved, tmp_root)

    # -----------------------------------------------------------------
    # (a) banner.py patch-engine primitives.
    # -----------------------------------------------------------------
    real_resolve_cli_target_path = banner.resolve_cli_target_path
    real_atomic_write_bytes = banner._atomic_write_bytes
    real_fsync_write_bytes = banner._fsync_write_bytes
    real_write_stamp = banner._write_stamp
    real_unlink_path = banner._unlink_path

    def guarded_resolve_cli_target_path(*args, **kwargs):
        result = real_resolve_cli_target_path(*args, **kwargs)
        if result is not None:
            resolved = pathlib.Path(result).resolve()
            # RESOLVER SCOPE (verify-bounce P1 fix): allow ONLY a result
            # under the OS temp root -- a real install under Program
            # Files, an npm global prefix, /usr/local, or anywhere else
            # non-home is rejected too, not just paths under real_home.
            if not _is_under_tmp_root(resolved):
                raise _hermeticity_violation(
                    "resolve_cli_target_path -> outside OS temp dir",
                    resolved, tmp_root)
        return result

    def guarded_atomic_write_bytes(path, data):
        _assert_safe_write_target(path)
        return real_atomic_write_bytes(path, data)

    def guarded_fsync_write_bytes(path, data):
        _assert_safe_write_target(path)
        return real_fsync_write_bytes(path, data)

    def guarded_write_stamp(stamp_path, data):
        _assert_safe_write_target(stamp_path)
        return real_write_stamp(stamp_path, data)

    def guarded_unlink_path(path):
        _assert_safe_write_target(path)
        return real_unlink_path(path)

    guarded_resolve_cli_target_path.__wrapped__ = real_resolve_cli_target_path
    guarded_atomic_write_bytes.__wrapped__ = real_atomic_write_bytes
    guarded_fsync_write_bytes.__wrapped__ = real_fsync_write_bytes
    guarded_write_stamp.__wrapped__ = real_write_stamp
    guarded_unlink_path.__wrapped__ = real_unlink_path

    banner.resolve_cli_target_path = guarded_resolve_cli_target_path
    banner._atomic_write_bytes = guarded_atomic_write_bytes
    banner._fsync_write_bytes = guarded_fsync_write_bytes
    banner._write_stamp = guarded_write_stamp
    banner._unlink_path = guarded_unlink_path

    # -----------------------------------------------------------------
    # (b) banner_install.py write-capable entry points.
    # -----------------------------------------------------------------
    real_install_into_file = banner_install.install_into_file
    real_uninstall_from_file = banner_install.uninstall_from_file
    real_write_shim_file = banner_install.write_shim_file
    real_unlink_shim_file = banner_install.unlink_shim_file
    real_install_all = banner_install.install_all
    real_restore_all = banner_install.restore_all

    def guarded_install_into_file(path, body, *args, **kwargs):
        _assert_safe_write_target(path)
        return real_install_into_file(path, body, *args, **kwargs)

    def guarded_uninstall_from_file(path, *args, **kwargs):
        _assert_safe_write_target(path)
        return real_uninstall_from_file(path, *args, **kwargs)

    def guarded_write_shim_file(path, content, *args, **kwargs):
        _assert_safe_write_target(path)
        return real_write_shim_file(path, content, *args, **kwargs)

    def guarded_unlink_shim_file(path):
        _assert_safe_write_target(path)
        return real_unlink_shim_file(path)

    def guarded_install_all(confirmed=False, home=None, *args, **kwargs):
        # confirmed=False (the default/preview path) never writes -- only
        # the confirmed write path needs a safe home. A missing home= means
        # "use the real Path.home()", which is exactly what a confirmed
        # install must never do from inside a test.
        if confirmed:
            _assert_safe_home(home)
        return real_install_all(confirmed, home, *args, **kwargs)

    def guarded_restore_all(home=None, *args, **kwargs):
        _assert_safe_home(home)
        return real_restore_all(home, *args, **kwargs)

    # __wrapped__ lets inspect.unwrap() (and inspect.getsource via it) see
    # through this guard to the real function -- e.g.
    # TestDedupeUserLevelOrnMotdOrchestration's source-level pin on
    # install_all()/uninstall_all() needs the REAL source, not this
    # wrapper's.
    guarded_install_into_file.__wrapped__ = real_install_into_file
    guarded_uninstall_from_file.__wrapped__ = real_uninstall_from_file
    guarded_write_shim_file.__wrapped__ = real_write_shim_file
    guarded_unlink_shim_file.__wrapped__ = real_unlink_shim_file
    guarded_install_all.__wrapped__ = real_install_all
    guarded_restore_all.__wrapped__ = real_restore_all

    banner_install.install_into_file = guarded_install_into_file
    banner_install.uninstall_from_file = guarded_uninstall_from_file
    banner_install.write_shim_file = guarded_write_shim_file
    banner_install.unlink_shim_file = guarded_unlink_shim_file
    banner_install.install_all = guarded_install_all
    banner_install.restore_all = guarded_restore_all
    banner_install.uninstall_all = guarded_restore_all

    # -----------------------------------------------------------------
    # (c) ALL registry access -- unconditional block, no tmp exception.
    # -----------------------------------------------------------------
    real_get_autorun_value = banner_install.get_autorun_value
    real_set_autorun_value = banner_install.set_autorun_value
    real_delete_autorun_value = banner_install.delete_autorun_value

    def guarded_get_autorun_value(*args, **kwargs):
        raise _registry_violation("get_autorun_value")

    def guarded_set_autorun_value(*args, **kwargs):
        raise _registry_violation("set_autorun_value")

    def guarded_delete_autorun_value(*args, **kwargs):
        raise _registry_violation("delete_autorun_value")

    guarded_get_autorun_value.__wrapped__ = real_get_autorun_value
    guarded_set_autorun_value.__wrapped__ = real_set_autorun_value
    guarded_delete_autorun_value.__wrapped__ = real_delete_autorun_value

    banner_install.get_autorun_value = guarded_get_autorun_value
    banner_install.set_autorun_value = guarded_set_autorun_value
    banner_install.delete_autorun_value = guarded_delete_autorun_value

    try:
        yield
    finally:
        banner.resolve_cli_target_path = real_resolve_cli_target_path
        banner._atomic_write_bytes = real_atomic_write_bytes
        banner._fsync_write_bytes = real_fsync_write_bytes
        banner._write_stamp = real_write_stamp
        banner._unlink_path = real_unlink_path

        banner_install.install_into_file = real_install_into_file
        banner_install.uninstall_from_file = real_uninstall_from_file
        banner_install.write_shim_file = real_write_shim_file
        banner_install.unlink_shim_file = real_unlink_shim_file
        banner_install.install_all = real_install_all
        banner_install.restore_all = real_restore_all
        banner_install.uninstall_all = real_restore_all

        banner_install.get_autorun_value = real_get_autorun_value
        banner_install.set_autorun_value = real_set_autorun_value
        banner_install.delete_autorun_value = real_delete_autorun_value
