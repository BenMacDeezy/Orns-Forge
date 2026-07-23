# Scout source priority

Search these in order; stop escalating once the stack is well-covered.

1. **Official MCP registry** — the native registry-search tools, deferred and
   reached via ToolSearch (`query: "mcp registry"`):
   `mcp__mcp-registry__search_mcp_registry`, `mcp__mcp-registry__suggest_connectors`,
   `mcp__mcp-registry__list_connectors`. Highest-trust source for MCP servers.
2. **`anthropics/skills`** — official skills; the packaging format Forge adopts,
   so these drop in without translation.
3. **Curated collections** — `wshobson/agents`, `VoltAgent/awesome-claude-code-subagents`,
   `obra/superpowers`. High-quality but third-party — vet harder.
4. **Web search** (WebSearch/WebFetch) — anything not covered above; treat as
   lowest trust and vet hardest.

Prefer the highest-priority source that satisfies a need; only escalate to lower
tiers for gaps the higher tiers do not fill.
