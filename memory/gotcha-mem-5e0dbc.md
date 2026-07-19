---
name: mem-5e0dbc
description: On Windows, bash on PATH may resolve to the WSL stub, breaking subprocess hook/shell tests — prefix PATH with Git's bash.
type: gotcha
created: 2026-07-17T23:00:14Z
updated: 2026-07-17T23:00:14Z
superseded-by: null
schema-version: 1
agents:
  - forge-worker
  - forge-verifier
---

On Windows, `bash` on `PATH` can resolve to the WSL stub at
`C:\Windows\system32\bash.exe` instead of a real POSIX shell. That stub
either launches a WSL distro (if one is installed) or fails outright — either
way it silently breaks any subprocess call that assumes a working `bash`,
including hook tests and shell-invoking gate commands. Symptoms look like a
hook or test hanging, prompting for a WSL install, or failing with an opaque
launch error that has nothing to do with the code under test.

Fix: prefix `PATH` with Git for Windows' bash directory before running
anything that shells out, e.g.:

```
PATH="/c/Program Files/Git/bin:$PATH" python -m pytest tools/ -q
```

or in PowerShell:

```
$env:PATH = "C:\Program Files\Git\bin;$env:PATH"
```

This resolves `bash` to Git Bash instead of the WSL stub. Relevant whenever a
worker or verifier runs gate commands, hook regression tests
(`tools/test_hooks.py`), or anything else that shells out to `bash` on a
Windows runner.
