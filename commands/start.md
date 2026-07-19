---
description: Enter the Forge kernel loop and work the queue
argument-hint: "[--budget <tokens>] [--max-tasks <n>]"
---

While the Forge loop is active, do not auto-invoke any skill via description
matching. Skill use inside the loop is explicit only: skills named by the
kernel, a spawn contract, or an agent's Attached-skills list. In particular, do
not let review/security/git skills hijack a loop turn.

Invoke the `forge:kernel` skill and enter the loop. Arguments: $ARGUMENTS

- `--budget <tokens>` / `--max-tasks <n>` override forge.md for this session.
- Run until a stop condition; end with the kernel's session report.
