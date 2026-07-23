---
name: expo-eas-workflow
description: Operational workflow for shipping an Expo/React Native app with EAS — build profiles in eas.json, eas submit to the App/Play Store, OTA updates via channels and rollout percentages, update-compatibility rules (runtime version, native-code drift), and CI wiring with EAS Workflows YAML. EAS is a paid Expo Application Services product with free-tier limits — build/compute minutes and update bandwidth cost money past the free tier. Use when a task ships a build, submits to a store, publishes an OTA update, sets up a build profile, or wires EAS into CI. Triggers on "eas build", "eas submit", "eas update", "eas.json", "OTA update", "runtime version", "build profile", "EAS Workflows", "app store submission".
---
<!-- last-verified: 2026-07 -->

# Expo EAS operational workflow

> **EAS costs money past the free tier.** `eas build` and EAS Workflow jobs
> consume your plan's build/compute minutes; store submission needs paid
> Apple Developer and Google Play accounts; update bandwidth beyond the free
> allotment bills too. Check https://expo.dev/pricing before running cloud
> commands, and never assume a build/submit/update run is free just because
> local development is.

## 1. Build profiles (`eas.json`)

`eas.json` defines named **build profiles** under `build`, each mapping to a
distribution shape:

```json
{
  "cli": { "version": ">= 16.0.1", "appVersionSource": "remote" },
  "build": {
    "development": { "developmentClient": true, "distribution": "internal" },
    "preview":     { "distribution": "internal" },
    "production":  { "autoIncrement": true, "ios": { "resourceClass": "m-medium" } }
  },
  "submit": {
    "production": {
      "ios": { "appleId": "you@example.com", "ascAppId": "1234567890" },
      "android": { "serviceAccountKeyPath": "./service-account.json", "track": "internal" }
    }
  }
}
```

- **`development`**: dev-client build for local Metro-connected iteration —
  never submit this profile to a store.
- **`preview`**: internal-distribution build for QA/stakeholders (TestFlight
  internal group, Play internal track, or ad-hoc/APK) — not public.
- **`production`**: the store-ready profile; `autoIncrement: true` lets EAS
  bump build numbers automatically instead of hand-editing them per release.
- Run with `eas build -p <ios|android> --profile <name>`; omit `-p` to build
  both platforms in one invocation.

## 2. Submit

```bash
eas build -p ios --profile production --submit   # build + submit in one call
eas submit -p android --profile production        # submit an existing build
```

Android tracks progress `internal -> closed -> open -> production` inside
Play Console; iOS submission lands in TestFlight first regardless. Configure
credentials once via `eas credentials` rather than re-entering them per run.

## 3. OTA updates — channels, rollout, compatibility

`eas update` ships JS/asset changes over the air **without** an app-store
review, but only within the constraints below:

- **Channels** map to build profiles (typically `production`/`preview`) and
  decide which running installs receive which update — publish with
  `eas update --branch <branch> --channel <channel>` (or the simpler
  `eas update` if channel/branch are already linked in `eas.json`).
- **Rollout percentage.** Publish to a fraction of a channel's installs first
  (`eas update --channel production --rollout-percentage 10`), watch for
  crash/error signals, then widen — never publish a risky update to 100% of
  production in one step.
- **Update-compatibility rules — the sharp edge.** An OTA update can only
  replace JS/assets; it **cannot** change native code, add a native module,
  or bump a native dependency that isn't already compiled into the binary
  the client is running. Expo enforces this via **runtime version**: a
  client only accepts an update whose runtime version matches its own. WHEN
  a change touches native code or a native dependency, THE change requires a
  new **build**, not just an update — publishing it as an OTA update against
  an incompatible runtime silently fails to apply (or crashes) on-device
  rather than erroring loudly at publish time, so verify the change is
  JS/asset-only before treating it as OTA-shippable.

## 4. CI wiring — EAS Workflows

EAS Workflows (`.eas/workflows/*.yml`) automate the build → submit → update
pipeline as YAML jobs triggered by `on:` (push, PR, schedule, manual
dispatch). A workflow file's top-level keys: `name`, `on` (triggers,
required), `jobs` (required), `defaults`, `concurrency`. Reference dynamic
values with `${{ }}` against `github.*`, `inputs.*`, `needs.*`, `jobs.*`,
`steps.*`, `workflow.*` contexts.

**Do not hand-write workflow YAML from memory** — the schema evolves. Fetch
the live schema (`https://api.expo.dev/v2/workflows/schema`) and the current
syntax doc
(`https://raw.githubusercontent.com/expo/expo/refs/heads/main/docs/pages/eas/workflows/syntax.mdx`)
before generating or editing a workflow, validate required fields per job
type against that schema, and confirm every `needs`/`after` job reference
actually exists in the file.

## Quick triage

| Symptom | Most likely cause | Fix |
|---|---|---|
| OTA update doesn't reach devices | runtime version mismatch (native drift) | cut a new build instead of an update; verify the change is JS/asset-only |
| Build fails only in CI, works locally | missing/stale `eas.json` profile, credentials not configured | `eas credentials`, confirm the CI job targets the right profile |
| Submission stuck in "processing" forever | wrong track/ASC app id, or missing paid account | check `submit` profile config, confirm Apple Developer/Play Console account is active |
| Workflow YAML rejected | schema drift vs hand-written assumptions | re-fetch `api.expo.dev/v2/workflows/schema`, validate against it |
| Rollout update causes a spike in crashes | shipped at 100% instead of staged | always start rollout percentage low, watch signals, then widen |

## Sources

Adapted (not copied) from **github.com/expo/skills** (MIT License, ©
650 Industries/Expo) — specifically `eas-app-stores` and `eas-workflows`
under `plugins/expo/skills/`. Re-derived and re-scoped for Forge's mobile
craft-skill format rather than reproduced verbatim; the source repo's
`references/` subdocuments (app-store metadata, TestFlight, Play Store,
workflow schema fetch script) remain the deeper reference if a task needs
more than this operational summary.
