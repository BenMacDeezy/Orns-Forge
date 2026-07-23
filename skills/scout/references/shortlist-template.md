# Scout shortlist template

The output of every scout pass (skill or `forge-scout` agent) takes this exact
shape — it is data for the kernel and the human, not prose.

```
STACK PROFILE: <languages / frameworks / build+test tooling detected, one line>

SHORTLIST (ranked, best fit first):
1. <name> [skill | mcp | cli | repo] — <source tier> — <one-line justification>
   VET: recency <…> · trust <…> · injection <…> · cost/tier <…>
   TO INSTALL (for the human to run — NOT run by scout): <exact command / config snippet>
2. …

GAPS → TOOLING TASKS: <capability gaps to file as backlog tasks — or "none">

NOTHING INSTALLED. Every item above requires explicit human approval.
```

If a candidate carries a real but acceptable risk (e.g. injection surface),
state it on the VET line rather than hiding it. If nothing clears vetting, say so
and return an empty SHORTLIST with the reason.
