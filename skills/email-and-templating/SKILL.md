---
name: email-and-templating
description: Send transactional email correctly — provider choice (Resend/Postmark/SES), react-email/MJML templating, and SPF/DKIM/DMARC deliverability basics. Use when a task sends email — signup confirmation, password reset, receipt, notification digest. Triggers on email, transactional email, Resend, Postmark, SES, react-email, MJML, SPF, DKIM, DMARC, deliverability.
---

# Email and templating

Scope: email-and-templating — transactional email provider selection,
react-email/MJML templating, and SPF/DKIM/DMARC deliverability basics. It
does not own marketing/broadcast email strategy, unsubscribe/consent policy
(`feature-legal-risk-checklist`'s "Email / messaging" risk area owns the
CAN-SPAM-style compliance framing), or general webhook idempotency beyond
what a provider's delivery-event webhook needs (`error-handling-and-resilience`
owns that mechanic generally).

## 1. Provider choice — Resend, Postmark, SES

All three are transactional (not bulk/marketing) email APIs; pick by what
the task actually needs, not by default habit:

- **Resend** — optimizes for developer experience: a modern TypeScript SDK,
  first-class **react-email** integration (templates are React components,
  rendered server-side), and a generous free/low-volume tier. Under the
  hood Resend routes sends through Amazon SES infrastructure rather than
  running its own — so it inherits SES's deliverability floor while adding
  DX on top. Good default for a new project already on React/Node that
  wants templates-as-components with minimal setup.
- **Postmark** — optimizes for deliverability and transactional-specific
  operational tooling: separate **message streams** for transactional vs.
  broadcast mail (so a bulk send never risks the transactional stream's
  reputation), detailed bounce/spam-complaint tracking, and fast, reliable
  delivery. Reach for it when deliverability guarantees and delivery
  observability matter more than templating ergonomics — e.g. password
  resets, payment receipts, anything time-sensitive and high-stakes.
- **Amazon SES** — optimizes for cost at high volume (materially cheaper
  per-email at scale than Resend or Postmark) at the cost of a rawer API,
  weaker built-in deliverability tooling, and more manual reputation/warm-up
  management. Reach for it directly (not via Resend) when volume is high
  enough that per-email cost dominates the decision and the team is willing
  to own deliverability operations itself.
- **This landscape shifts** — pricing tiers and feature sets change; verify
  current pricing/limits on the provider's own docs before committing to
  one for a cost-sensitive decision, rather than trusting a remembered
  number.
- Whichever provider is chosen, **use its API/SDK, not raw SMTP**, for
  transactional sends — the API path gives structured delivery-event
  webhooks (bounce, complaint, delivered) that raw SMTP doesn't, and those
  events are what deliverability monitoring (§3) depends on.

## 2. Templating: react-email vs. MJML

- **react-email** — write email templates as React components
  (`<Html>`, `<Body>`, `<Section>`, `<Text>` etc. from `@react-email/components`),
  rendered to inline-styled HTML at send time. The natural choice when the
  team already writes React — the same component/props mental model
  applies, and templates can be previewed with the `react-email` dev server
  before sending. Resend integrates with it directly; other providers
  accept the rendered HTML string.
- **MJML** — a markup language (`<mjml><mj-section><mj-column>...`)
  purpose-built for email, compiled to responsive, client-tested HTML with
  inline styles. The choice when the team isn't React-based, or wants a
  markup-first templating layer with an existing library of MJML components
  and a mature compiler independent of any particular frontend stack.
- **Regardless of templating tool**, email HTML must be **self-contained
  and defensively simple**: inline CSS (many clients strip `<style>`
  blocks or ignore external stylesheets), table-based layout for the
  clients that don't support modern flex/grid (Outlook's rendering engine
  is the usual constraint), and no reliance on JavaScript (email clients
  don't execute it). Both react-email and MJML handle this compilation for
  you — hand-writing raw HTML email without one of these tools means
  re-deriving those constraints manually.
- **Always send a plain-text alternative** alongside the HTML body
  (`multipart/alternative`) — some clients/spam filters penalize
  HTML-only email, and plain text is the fallback for anything that can't
  render the HTML.
- **Test rendering across real clients** before shipping a new template —
  Gmail, Outlook, and Apple Mail each diverge from web CSS support in
  different ways; a template that looks right in the browser preview can
  break in Outlook specifically.

## 3. Deliverability basics: SPF, DKIM, DMARC

Getting a send accepted by the provider's API is not the same as it
reaching the inbox — these three DNS-based records are what receiving mail
servers check to decide "is this really from who it claims, and should I
trust it":

- **SPF (Sender Policy Framework)** — a DNS TXT record on the sending
  domain listing which mail servers are authorized to send on its behalf.
  The transactional provider publishes the record value to add; without it,
  receiving servers can't confirm the send came from an authorized source
  for that domain.
- **DKIM (DomainKeys Identified Mail)** — the provider cryptographically
  signs each outgoing message with a private key; the matching public key
  is published as a DNS record, so the receiving server can verify the
  message wasn't altered in transit and genuinely came from a holder of
  the private key. Set this up through the provider's domain-verification
  flow (Resend/Postmark/SES all require it before allowing sends from a
  custom domain).
- **DMARC (Domain-based Message Authentication, Reporting & Conformance)**
  — a DNS TXT record that tells receiving servers what to do when a message
  **fails** both SPF and DKIM alignment (quarantine, reject, or none) and
  where to send aggregate failure reports. Publish DMARC only after SPF and
  DKIM are correctly configured and passing — a `reject` policy published
  before authentication is solid will silently drop legitimate mail.
- **All three must be configured on the actual sending domain** (or a
  verified subdomain of it), not left on the provider's shared/default
  domain, before sending anything that matters — sending transactional
  email from an unauthenticated domain is the single most common cause of
  landing in spam, independent of which provider is used.
- Monitor the provider's **bounce and spam-complaint webhooks** (§1) and
  suppress future sends to addresses that hard-bounce or complain —
  continuing to send to a hard-bounced address degrades the sending
  domain's reputation for every recipient, not just that one.

## Where this fits

`feature-legal-risk-checklist`'s "Email / messaging" risk area owns the
CAN-SPAM-style compliance framing (sender identity, unsubscribe,
opt-out handling) for a feature that sends email — this skill owns getting
the email built and delivered correctly. Delivery-event webhook handling
(bounce/complaint) follows the same idempotency discipline
`error-handling-and-resilience` §6 and `payment-integration-discipline` §4
apply to any at-least-once webhook consumer.

## Sources

Adapted from:
- https://resend.com/docs
- https://postmarkapp.com/compare/resend-alternative
- https://react.email/docs
- https://documentation.mjml.io/
- https://www.rfc-editor.org/rfc/rfc7208 (SPF)
- https://www.rfc-editor.org/rfc/rfc6376 (DKIM)
- https://www.rfc-editor.org/rfc/rfc7489 (DMARC)
