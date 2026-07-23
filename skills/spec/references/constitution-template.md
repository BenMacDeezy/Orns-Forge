# Constitution — <project>

Per-project non-negotiables. Each rule is written so the verifier can check it
**mechanically**: on every full-tier task (and any task when this file exists)
it returns a yes/no plus concrete evidence for every rule. A rule the verifier
cannot evaluate mechanically is a bug in the rule — rewrite it.

Rules are numbered and stable; audit references depend on the numbers. Add by
appending; retire by marking `(retired <date>)`; never renumber or delete.

1. Every bug fix ships with a test that fails without the fix and passes with it.
2. No speculative abstraction: no interface, config flag, or indirection is
   introduced for a caller that does not exist in this diff.
3. Tests exist before implementation for standard-and-full-tier tasks: the diff
   adds or extends tests covering each EARS clause, not implementation only.
4. No new dependency (package, service, MCP server) without a one-line stated
   reason recorded in the task Outcome and, for full tier, the linked spec.
5. No secret, key, or token is committed to the repo.

<!-- Edit freely: add project rules below, keep each mechanically checkable. -->
