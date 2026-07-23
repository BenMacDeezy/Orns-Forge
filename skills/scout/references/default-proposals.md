# Scout default proposals

Worth proposing on most projects (spec §10). Each is still vetted every pass and
still requires human approval — "default" is not "trusted".

- **context7** (MCP) — up-to-date library/framework docs in-context. Vet note:
  has had a poisoning CVE and a free-tier reduction; confirm current tier and
  integrity before proposing.
- **grep.app MCP** — search real-world usage across public repos; good for "how
  is this API actually used". Vet note: read-only external content — injection
  surface is the query results.
- **Serena-class LSP server** (MCP) — symbol-precise queries (definitions,
  references, call sites). Complements the narrative repo map, which deliberately
  does not encode call graphs (spec §7.2). Vet note: runs a language server over
  your code locally; confirm the specific server's provenance.

Propose these only when they fit the profiled stack. Never install them — present
the command and let the human decide.
