Some teams define their crew using a declarative `agents.yaml` file instead
of Python. For reference, here is what that shape looks like:

```yaml
researcher:
  role: Senior Research Analyst
  goal: Uncover cutting-edge developments in AI and data science
  backstory: You work at a leading tech think tank.
```

This document is describing that format for a reader, not itself an agent
definition -- it has no frontmatter and the role/goal/backstory keys only
appear inside the illustrative code fence above, never at top level.
