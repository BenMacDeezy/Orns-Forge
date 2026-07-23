---
description: Build or refresh the Forge repo map
argument-hint: "[--refresh]"
---

Invoke the `forge:map` skill. Arguments: $ARGUMENTS

- If `.forge/map/architecture.md` is absent → run the **build protocol** (full map).
- If it exists → run the **incremental refresh protocol** (re-map only directories changed since the map's freshness-header commit). `--refresh` forces this path.
- Always rewrite every map file's freshness header to the current `git rev-parse HEAD` sha and a real `date -u` timestamp.
- Reply with: which files were written/updated, the new freshness commit, and the top 3 churn hotspots — nothing else.
