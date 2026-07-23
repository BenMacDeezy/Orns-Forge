"""Tests for tools/providers.py (fg-c0102 / bm-provider-cli-detection).

Hermetic: every subprocess interaction is mocked via unittest.mock.patch on
providers.subprocess.run / providers.shutil.which. These tests MUST pass on
a machine with none of the provider CLIs installed -- no test here depends
on codex/grok/antigravity actually being on PATH.
"""
import inspect
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import providers  # noqa: E402


class TestWhichMiss(unittest.TestCase):
    """A provider CLI absent from PATH -> installed False, authed None,
    for every known provider -- and detect() never calls the probe
    subprocess when the CLI isn't even found."""

    def test_codex_not_on_path(self):
        with patch("providers.shutil.which", return_value=None) as which_mock, \
                patch("providers.subprocess.run") as run_mock:
            result = providers.detect("codex")
        which_mock.assert_called_once_with("codex")
        run_mock.assert_not_called()
        self.assertEqual(result["installed"], False)
        self.assertIsNone(result["authed"])
        self.assertIsNone(result["version"])
        self.assertIn("not found", result["detail"])

    def test_grok_not_on_path(self):
        with patch("providers.shutil.which", return_value=None):
            result = providers.detect("grok")
        self.assertFalse(result["installed"])
        self.assertIsNone(result["authed"])

    def test_antigravity_not_on_path(self):
        with patch("providers.shutil.which", return_value=None):
            result = providers.detect("antigravity")
        self.assertFalse(result["installed"])
        self.assertIsNone(result["authed"])

    def test_unknown_provider(self):
        result = providers.detect("copilot")
        self.assertFalse(result["installed"])
        self.assertIsNone(result["authed"])
        self.assertIn("unknown provider", result["detail"])


class TestCodexProbeParsing(unittest.TestCase):
    """codex is the only provider with a real authed probe in this task
    (`codex login status`). Cover authed / not-authed / timeout / (via
    TestWhichMiss above) absent -- all against a mocked subprocess so no
    real codex CLI is required on the test machine."""

    def _fake_which(self, name):
        return "/fake/bin/codex" if name == "codex" else None

    def test_codex_authed(self):
        completed = subprocess.CompletedProcess(
            args=["codex", "login", "status"],
            returncode=0,
            stdout="Logged in using ChatGPT\n",
            stderr="",
        )
        with patch("providers.shutil.which", side_effect=self._fake_which), \
                patch("providers.subprocess.run", return_value=completed) as run_mock:
            result = providers.detect("codex")

        self.assertTrue(result["installed"])
        self.assertTrue(result["authed"])
        self.assertIn("logged in", result["detail"].lower())

        # Assert the probe invocation itself: non-mutating subcommand,
        # inherited environment (no env= kwarg at all).
        run_mock.assert_called_once()
        call_args, call_kwargs = run_mock.call_args
        argv = call_args[0]
        self.assertEqual(argv, ["/fake/bin/codex", "login", "status"])
        self.assertNotIn("env", call_kwargs)
        self.assertEqual(call_kwargs.get("timeout"), providers.PROBE_TIMEOUT_SECONDS)

    def test_codex_not_authed(self):
        completed = subprocess.CompletedProcess(
            args=["codex", "login", "status"],
            returncode=1,
            stdout="",
            stderr="Not logged in\n",
        )
        with patch("providers.shutil.which", side_effect=self._fake_which), \
                patch("providers.subprocess.run", return_value=completed):
            result = providers.detect("codex")

        self.assertTrue(result["installed"])
        self.assertFalse(result["authed"])
        self.assertIn("not logged in", result["detail"].lower())

    def test_codex_timeout_never_hangs(self):
        with patch("providers.shutil.which", side_effect=self._fake_which), \
                patch(
                    "providers.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(
                        cmd=["codex", "login", "status"],
                        timeout=providers.PROBE_TIMEOUT_SECONDS,
                    ),
                ):
            result = providers.detect("codex")

        self.assertTrue(result["installed"])
        self.assertIsNone(result["authed"])
        self.assertIn("timed out", result["detail"])

    def test_codex_launch_failure_is_clean_not_raised(self):
        with patch("providers.shutil.which", side_effect=self._fake_which), \
                patch("providers.subprocess.run", side_effect=OSError("boom")):
            result = providers.detect("codex")

        self.assertTrue(result["installed"])
        self.assertIsNone(result["authed"])
        self.assertIsInstance(result["detail"], str)


class TestPilotGatedStubs(unittest.TestCase):
    """grok / antigravity ship detection-only: installed reflects PATH,
    authed is always None, and the detail explains the pilot gate by name.
    Neither ever calls the probe subprocess -- no dispatch code exists for
    either provider in this task."""

    def test_grok_installed_returns_pilot_gated_stub(self):
        with patch("providers.shutil.which", return_value="/fake/bin/grok"), \
                patch("providers.subprocess.run") as run_mock:
            result = providers.detect("grok")

        run_mock.assert_not_called()
        self.assertTrue(result["installed"])
        self.assertIsNone(result["authed"])
        self.assertIsNone(result["version"])
        self.assertIn("bm-grok-pilot-test", result["detail"])

    def test_antigravity_installed_returns_pilot_gated_stub(self):
        with patch("providers.shutil.which", return_value="/fake/bin/antigravity"), \
                patch("providers.subprocess.run") as run_mock:
            result = providers.detect("antigravity")

        run_mock.assert_not_called()
        self.assertTrue(result["installed"])
        self.assertIsNone(result["authed"])
        self.assertIn("bm-antigravity-smoke-test", result["detail"])


class TestCredentialRuleStaticChecks(unittest.TestCase):
    """Mechanically pins the spec-e8a3 Risks-section credential rule:
    tools/providers.py must never construct an env dict carrying a
    key/token-shaped value, and no function in the module may even accept
    a credential-shaped parameter. This is deliberately a static/source
    check, not just behavioral coverage -- it fails loudly if a future
    edit reintroduces the pattern the spec calls out as the exfiltration
    risk, even in a code path no runtime test happens to exercise."""

    CREDENTIAL_NAME_FRAGMENTS = (
        "api_key", "apikey", "token", "secret", "credential", "password",
        "auth_key", "session_key",
    )

    def test_source_never_constructs_an_env_dict_with_key_token_vars(self):
        source = (REPO_ROOT / "tools" / "providers.py").read_text(encoding="utf-8")
        # Hard rule 2 (module docstring): no `env=` kwarg is ever passed to
        # subprocess in this file -- the probe always inherits the current
        # process environment in place. This also mechanically rules out
        # the "env dict containing a key/token-shaped value" risk, since
        # there is no env= construction of any kind to poison.
        self.assertNotIn(
            "env=",
            source,
            "tools/providers.py must never pass an env= kwarg to a "
            "subprocess call -- probes must inherit the current "
            "environment in place, never construct a fresh env block "
            "(spec-e8a3 Risks: credential-in-env-var exfiltration surface)",
        )
        self.assertNotIn(
            "os.environ.copy",
            source,
            "tools/providers.py must never build a mutable copy of the "
            "environment to inject a value into",
        )

    def test_no_function_accepts_a_credential_shaped_parameter(self):
        for name, func in inspect.getmembers(providers, inspect.isfunction):
            if func.__module__ != providers.__name__:
                continue
            sig = inspect.signature(func)
            for param_name in sig.parameters:
                lowered = param_name.lower()
                for fragment in self.CREDENTIAL_NAME_FRAGMENTS:
                    self.assertNotIn(
                        fragment,
                        lowered,
                        f"providers.{name}() has a credential-shaped "
                        f"parameter {param_name!r} (matches {fragment!r}) "
                        "-- this module must never accept a credential "
                        "value of any kind (spec-e8a3 Non-goals: Forge "
                        "never touches a provider credential)",
                    )

    def test_module_source_has_no_credential_shaped_module_level_state(self):
        source = (REPO_ROOT / "tools" / "providers.py").read_text(encoding="utf-8")
        lowered = source.lower()
        for fragment in ("api_key =", "apikey =", "session_token =", "password ="):
            self.assertNotIn(
                fragment,
                lowered,
                f"tools/providers.py must not define module-level "
                f"credential-shaped state ({fragment!r} found)",
            )


class TestDetectReturnShape(unittest.TestCase):
    """Every detect() result has exactly the four documented keys, with
    the documented types, regardless of provider or outcome."""

    def test_return_shape_is_stable_across_all_providers(self):
        with patch("providers.shutil.which", return_value=None):
            for provider in ("codex", "grok", "antigravity"):
                result = providers.detect(provider)
                self.assertEqual(
                    set(result.keys()), {"installed", "authed", "version", "detail"}
                )
                self.assertIsInstance(result["installed"], bool)
                self.assertIsInstance(result["detail"], str)
                self.assertIn(result["authed"], (True, False, None))


if __name__ == "__main__":
    unittest.main()
