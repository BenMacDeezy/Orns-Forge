#!/usr/bin/env python
"""Forge update check (fg-a10914).

Stdlib only. Compares the installed plugin version
(`.claude-plugin/plugin.json`) against the newest semver release tag on the
public mirror repo, throttled to at most one remote check per 24h via a
timestamp cache file. Prints exactly one line when a newer release exists;
stays completely silent otherwise.

SECURITY FLOOR (see fg-a10914 acceptance criteria): this module is
version-compare ONLY.
  - It never executes, evals, or writes anything fetched from the remote.
  - The only thing ever read from the remote is a list of git tag names
    (`git ls-remote --tags`), each strictly validated against
    ``^v?\\d+\\.\\d+\\.\\d+$`` before being treated as a version.
  - The only thing this module ever writes to disk is the throttle cache
    file (machine-local state, never inside the repo).
  - Every failure path (network error, timeout, malformed remote data,
    missing/unparseable plugin.json) is silent: it returns None / exits 0,
    never raises out of the public entry points.

MIRROR_URL is deliberately single-sourced here. Nowhere else in this repo
should hardcode a second mirror URL; if it ever changes, update it here
only.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
from typing import Iterable, Optional, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"

# Public mirror repo (fg-a10913 / fg-a10915). Set at first public release --
# see docs/releasing.md's pre-first-release checklist.
MIRROR_URL = "https://github.com/BenMacDeezy/Orns-Forge.git"

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
CACHE_TTL_SECONDS = 24 * 60 * 60
REMOTE_TIMEOUT_SECONDS = 2

SemverTuple = Tuple[int, int, int]


def _cache_path() -> pathlib.Path:
    base = (
        os.environ.get("TMPDIR")
        or os.environ.get("TEMP")
        or os.environ.get("TMP")
        or "/tmp"
    )
    return pathlib.Path(base) / "forge-update-check-cache"


def parse_semver(value: str) -> Optional[SemverTuple]:
    """Strict semver parse: ``^v?\\d+\\.\\d+\\.\\d+$`` or None.

    Anything else (a partial version, a 4-segment version, the literal
    string "latest", shell/format-string injection attempts, ...) is
    rejected — never partially parsed, never coerced.
    """
    if not isinstance(value, str):
        return None
    match = SEMVER_RE.match(value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _installed_version() -> Optional[str]:
    try:
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = data.get("version") if isinstance(data, dict) else None
    if parse_semver(version) is None:
        return None
    return version.strip()


def _cache_is_fresh(path: pathlib.Path, ttl: int = CACHE_TTL_SECONDS) -> bool:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return False
    return (time.time() - mtime) < ttl


def _touch_cache(path: pathlib.Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def _kill_process_tree(proc: "subprocess.Popen") -> None:
    """Best-effort reap of the ENTIRE process tree rooted at proc.

    `proc.kill()` alone only terminates the direct child (git.exe). For an
    http(s) remote, git spawns a transport-helper grandchild
    (git-remote-http) that inherits the stdout/stderr pipes; if that
    grandchild is still alive when the parent is killed, it keeps the pipes
    open and `communicate()` blocks until the grandchild's own (much
    longer, OS-default) TCP timeout — measured ~21s against an unroutable
    host, five times the <=2s the check is supposed to cap at.

    Windows: `taskkill /F /T /PID <pid>` walks and kills the whole tree
    (`/T`), which is why `_fetch_remote_tags` launches git with
    `CREATE_NEW_PROCESS_GROUP` — taskkill needs that to reliably find the
    children. POSIX: the process was started in its own session
    (`start_new_session=True`), so `os.killpg` reaches every descendant.
    """
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=3,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def _fetch_remote_tags(mirror_url: str, timeout: int = REMOTE_TIMEOUT_SECONDS) -> Iterable[str]:
    """Return raw tag names from the mirror. Any failure -> empty list.

    Uses `git ls-remote --tags`, which only lists refs — it never clones,
    fetches objects, or executes anything from the remote.

    Wall-clock is bounded by TWO independent belts, since neither alone is
    a complete guarantee on every git transport:
      1. `-c http.connectTimeout=<timeout>` (+ low-speed knobs) tells git's
         own http transport to give up fast — but does not cover every
         transport path (e.g. a helper that ignores/predates these knobs).
      2. The required guarantee: `communicate(timeout=...)` plus, on
         TimeoutExpired, `_kill_process_tree` — this reaps the whole
         process tree (git.exe AND any grandchild transport helper) rather
         than just the direct child, so a wedged grandchild can never hold
         the pipe open past our own cap.
    """
    popen_kwargs: dict = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True

    git_transport_timeouts = [
        "-c", f"http.connectTimeout={timeout}",
        "-c", "http.lowSpeedLimit=1000",
        "-c", f"http.lowSpeedTime={timeout}",
    ]

    try:
        proc = subprocess.Popen(
            ["git", *git_transport_timeouts, "ls-remote", "--tags", mirror_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **popen_kwargs,
        )
    except (OSError, ValueError):
        return []

    try:
        stdout, _stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        try:
            # Drain now that the whole tree is dead so no zombie/handle
            # leaks; the tree is gone so this returns almost immediately,
            # but it still gets its own short bound rather than trusting
            # that.
            stdout, _stderr = proc.communicate(timeout=2)
        except Exception:
            return []
    except Exception:
        _kill_process_tree(proc)
        return []

    if proc.returncode != 0:
        return []

    tags = []
    for line in (stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        ref = parts[1].strip()
        if not ref.startswith("refs/tags/"):
            continue
        tag = ref[len("refs/tags/"):]
        if tag.endswith("^{}"):
            tag = tag[: -len("^{}")]
        tags.append(tag)
    return tags


def _latest_remote_version(tags: Iterable[str]) -> Optional[str]:
    best_parsed: Optional[SemverTuple] = None
    best_raw: Optional[str] = None
    for tag in tags:
        parsed = parse_semver(tag)
        if parsed is None:
            continue
        if best_parsed is None or parsed > best_parsed:
            best_parsed = parsed
            best_raw = tag.strip().lstrip("vV")
    return best_raw


def check_for_update(
    mirror_url: Optional[str] = None,
    cache_path: Optional[pathlib.Path] = None,
    installed_version: Optional[str] = None,
) -> Optional[str]:
    """Return the newer remote version string, or None.

    None covers every "nothing to report" case: mirror unset, cache still
    fresh (throttled), installed version unreadable, remote unreachable/
    timed out, remote has no valid semver tags, or remote <= installed.
    Never raises.
    """
    try:
        url = MIRROR_URL if mirror_url is None else mirror_url
        if not url or not url.strip():
            return None

        cache_path = cache_path or _cache_path()
        if _cache_is_fresh(cache_path):
            return None

        # Throttle regardless of outcome: this counts as "the one remote
        # check" for the next 24h even if it fails below.
        _touch_cache(cache_path)

        installed = installed_version if installed_version is not None else _installed_version()
        installed_parsed = parse_semver(installed) if installed is not None else None
        if installed_parsed is None:
            return None

        tags = _fetch_remote_tags(url)
        latest = _latest_remote_version(tags)
        if latest is None:
            return None

        latest_parsed = parse_semver(latest)
        if latest_parsed is None:
            return None

        if latest_parsed > installed_parsed:
            return latest
        return None
    except Exception:
        # Belt-and-suspenders: this function must never raise. Every
        # sub-step above already fails silent on its own, but a change
        # there must not turn into a session-start crash here.
        return None


def main(argv=None) -> int:
    newer = check_for_update()
    if newer:
        print(f"forge v{newer} available — run /forge:update")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
