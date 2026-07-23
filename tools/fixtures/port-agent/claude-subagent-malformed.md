---
name: acme-half-agent
model: sonnet
---

This frontmatter block is missing the required `description` field, so it
does not satisfy the Claude Code subagent frontmatter contract even though
it has the `---` fences. The detector must not guess a mapping here -- it
should report "unrecognized format" instead.
