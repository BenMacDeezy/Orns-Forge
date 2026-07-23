---
name: feature-legal-risk-checklist
description: Legal risk review of a feature or spec touching PII/personal data, authentication, payments, messaging/email, analytics/tracking, user-generated content, minors, or third-party data; privacy policy; GDPR/CCPA; terms of service needs. Use when a spec or task description mentions collecting personal data, accounts, payments, tracking, UGC, minors, or messaging.
---

# Feature legal-risk checklist

You produce a checklist, not a legal opinion. For every risk area a feature
touches, output **what needs addressing and why** — never drafted legal text,
never a jurisdiction-specific ruling on whether the feature is compliant.
"Is this legal" is a question for counsel; "what does this feature need to
have addressed before shipping" is the question you answer.

## Method

1. Read the feature/spec and identify which risk areas below it actually
   touches — don't run the whole checklist against a feature that touches
   none of it.
2. For each area touched, emit one line per concrete item in the format:
   `[area] → [what to address] → [why, one line] → [GREEN|YELLOW|RED]`.
3. Never skip an area the feature clearly touches to keep the list short —
   an omitted area is a worse failure than a long list.

## Risk areas

- **PII / personal data collection** → disclose the collection in the
  privacy policy, apply data minimization (collect only what the feature
  needs), define a retention/deletion path → *why*: undisclosed collection
  and unbounded retention are the two most common triggers for regulatory
  and user complaints.
- **Auth / accounts** → credential handling (hashing, never logging
  passwords/tokens in plaintext), breach-notification awareness (does the
  team have a documented path if this data leaks) → *why*: credential
  compromise has both a security and a legal-notification dimension.
- **Payments** → minimize PCI scope — route card data through a processor
  (Stripe, etc.), never store or log PANs/CVVs directly → *why*: storing
  card data yourself pulls the whole system into PCI-DSS scope, which is an
  expensive, ongoing compliance burden most features don't need to take on.
- **Analytics / tracking** → consent posture appropriate to the
  jurisdictions served — GDPR requires opt-in consent before non-essential
  tracking; CCPA/CPRA requires an opt-out mechanism ("do not sell/share") —
  these are different postures, not interchangeable → *why*: shipping a
  GDPR-scoped consent banner doesn't satisfy CCPA's opt-out requirement and
  vice versa.
- **User-generated content (UGC)** → a DMCA notice-and-takedown path (or
  equivalent) and a moderation hook (report/remove mechanism) → *why*:
  hosting UGC without a takedown process forfeits safe-harbor protection in
  jurisdictions that offer one.
- **Email / messaging** → CAN-SPAM-style requirements — clear sender
  identity, working unsubscribe, honoring opt-outs promptly → *why*:
  unsubscribe/opt-out failures are the most commonly enforced violation in
  this area.
- **Minors** → treat any feature knowingly directed at or collecting data
  from children as a **RED escalation, not a checklist item** — flag it for
  counsel immediately rather than listing sub-items (COPPA and equivalent
  regimes carry outsized penalties and the age-detection/consent mechanics
  are genuinely jurisdiction-specific).
- **Export / cryptography** → note when relevant (the feature ships or uses
  non-trivial cryptography across borders, or handles export-controlled
  technical data) — surface as a FOR COUNSEL item, do not attempt to
  classify export-control status yourself.

## Urgency tagging

- **RED** — high-risk area with no existing mitigation identified (minors,
  undisclosed PII collection, stored card data, UGC with no takedown path).
- **YELLOW** — area touched, mitigation partially exists or is unverified
  (e.g. a privacy policy exists but may not cover this specific new
  collection).
- **GREEN** — area touched but an adequate, verifiable mitigation already
  exists in the project (e.g. payments already routed through a processor
  with no new PAN handling introduced).

## Explicit rule — questions, not conclusions

The output identifies **questions for qualified counsel**; it never answers
them with a legal conclusion. Do not write "this is GDPR-compliant" or "this
does not require a privacy policy update" — write "does this collection
require a privacy-policy update: unresolved, ask counsel" instead. Never
produce a jurisdiction-specific legal opinion (e.g. "under California law,
this qualifies as a sale of data") — that determination belongs to counsel,
even when the answer seems obvious from the checklist.

---
This skill produces engineering-side license/compliance analysis, not legal
advice. Findings must be verified with qualified counsel before relying on
them for shipping, licensing, or contractual decisions. Cite sources for
every non-obvious judgment so a human can independently verify.

---
Adapted from: general practice around GDPR (Regulation (EU) 2016/679),
CCPA/CPRA (Cal. Civ. Code §1798.100 et seq.), COPPA (15 U.S.C. §6501 et
seq.), CAN-SPAM Act (15 U.S.C. §7701 et seq.), DMCA §512 notice-and-takedown,
and PCI-DSS scope-minimization guidance (PCI Security Standards Council).
