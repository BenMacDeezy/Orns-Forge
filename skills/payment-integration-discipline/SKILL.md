---
name: payment-integration-discipline
description: Integrate payments correctly — Stripe/RevenueCat, the mobile IAP regulatory surface, PCI-scope avoidance, and webhook idempotency. Use when a task touches payments, billing, subscriptions, checkout, or in-app purchase. Triggers on payment, billing, checkout, subscription, Stripe, RevenueCat, IAP, in-app purchase, webhook, invoice.
---

# Payment integration discipline

Scope: payment-integration-discipline — Stripe/RevenueCat integration
shape, the mobile IAP regulatory surface, PCI-scope avoidance, and webhook
idempotency. It does not own the legal/compliance judgment call on a given
feature (that's `feature-legal-risk-checklist`, §5) or general error-handling
mechanics beyond payment-specific idempotency (`error-handling-and-resilience`
owns retries/timeouts/circuit breakers generally).

**Any task that touches payments fires the forge-security review trigger.**
Money/payment is a NAMED trigger in the verification-economics conventions
(`docs/conventions.md`, "Verification economics — 2026-07-18") — a payment
diff is reviewed by `forge-security` on that named trigger regardless of how
small the change looks, the same way an auth/token/secret touch is. Don't
assume a "just adds a field" payment change is exempt; the trigger is on the
surface touched, not the diff size.

This skill pairs with `skills/feature-legal-risk-checklist` — that skill's
**Payments** risk area covers the compliance-checklist half (PCI-DSS scope
minimization, what to disclose); this skill covers the engineering-integration
half (how to actually keep raw card data out of your system, how to make
webhooks safe). Run both on any payment-touching task, not either/or.

## 1. Stripe and RevenueCat — pick by surface, not by preference

- **Stripe** (or an equivalent processor — Adyen, Braintree) is the default
  for **web/server-initiated payments**: one-time charges, subscriptions
  billed outside app-store rails, invoicing, marketplace payouts (Stripe
  Connect). Integrate via **Stripe Checkout** or **Payment Element** so card
  entry happens on Stripe's hosted/embedded surface, never your own form
  (§2).
- **RevenueCat** sits on top of Apple's StoreKit and Google Play Billing to
  unify **mobile in-app purchase** entitlement state (subscriptions,
  consumables) across both platforms and expose one server-side source of
  truth for "does this user have this entitlement" — it does not replace
  the platform IAP payment rails (§2 explains why it can't).
- **Don't cross the streams**: a digital good sold to a mobile app user goes
  through platform IAP (§2), not Stripe, even if the same product is sold
  through Stripe on web — this is a platform policy requirement, not an
  architectural preference.

## 2. The mobile IAP regulatory surface

**Apple and Google mandate their own in-app purchase mechanism for digital
goods and content consumed inside the app** — subscriptions, premium
features, in-game currency, unlockable content — and take a commission on
that revenue (Apple's Guideline 3.1.1; Google Play's Payments policy). A
payment flow that routes a mobile user around StoreKit/Play Billing for a
qualifying digital good is a store-policy violation that can get the app
rejected or pulled, not just a business-model choice to weigh.

- **Physical goods and services consumed outside the app are exempt** — a
  ride-hailing charge, a hotel booking, a physical product purchase can use
  Stripe/a processor directly even from a mobile app, because the goods
  aren't "digital content consumed within the app."
- **The external-payment-link landscape is actively shifting and
  jurisdiction-specific as of 2026** — U.S. court rulings have forced both
  Apple and Google to allow external purchase links/alternative billing for
  US storefronts (Apple's External Purchase Link Entitlement; Google's
  alternative billing / external offers program), each with its own
  reduced-but-nonzero commission and its own enrollment/compliance
  requirements, while most other storefronts still require standard
  platform IAP. **Treat exact terms (fee percentages, entitlement
  requirements, deadlines) as time-sensitive — verify current policy on
  Apple's/Google's developer docs before building an external-payment flow
  for mobile, don't rely on a remembered number.**
- RevenueCat (§1) is the common way to keep entitlement logic
  platform-agnostic while still routing the actual purchase through
  whichever rail (StoreKit, Play Billing, or an approved external link) the
  policy for that storefront/product type requires.

## 3. PCI-scope avoidance — never touch raw card data

**This code NEVER touches, stores, or logs raw card data** — the primary
account number (PAN), CVV, or full magnetic-stripe/chip track data. This
mirrors Forge's standing prohibition on ever handling credentials directly:
the same way an agent must never enter a password or API key into a field
on a user's behalf, application code must never let a card number pass
through your own server or client code as plaintext you could read, log, or
persist.

- **Route card entry through the processor's hosted/tokenizing surface** —
  Stripe Elements/Checkout, an equivalent SDK's drop-in card form — so the
  raw PAN goes directly from the user's browser/device to the processor and
  your code only ever sees an opaque token/PaymentMethod id.
- **Why this matters beyond "best practice":** touching raw card data pulls
  your entire system into **PCI-DSS scope** — a compliance burden (network
  segmentation, quarterly scans, annual audits, restricted data retention)
  that most teams have no reason to take on when a processor already
  carries that scope on your behalf. Storing a PAN "just for this one
  feature" moves the whole system into scope, not just that feature.
- **Never log a PAN, CVV, or full card number** — this is a stricter
  instance of the general "never log secrets" rule
  (`observability-logging-metrics-tracing` §1); a card number in a log
  aggregator is a breach regardless of intent, and unlike an API key it
  can't be rotated by the party who leaked it.
- If a raw card number ever appears in code, a request body your server
  parses, or a log line, treat it as a **P0 security finding**, not a style
  nit — this is exactly the kind of surface `forge-security` is spawned to
  catch on the named payment trigger above.

## 4. Webhook idempotency

Processors deliver webhooks **at-least-once** — the same event (e.g.
`invoice.paid`, a RevenueCat entitlement update) can arrive more than once,
out of order, or after a delay. Handle every payment webhook the same way
`error-handling-and-resilience` §6 requires for any at-least-once consumer:

- **Verify the webhook signature first**, before processing anything — an
  unauthenticated webhook endpoint lets anyone forge a "payment succeeded"
  event.
- **Dedupe by the event's own id** (Stripe's `event.id`, RevenueCat's event
  id) — persist processed event ids (or a hash) and skip re-processing one
  already seen, rather than trusting delivery count.
- **Make the handler's effect idempotent regardless of dedupe** — upsert
  entitlement/subscription state keyed by the underlying resource id
  (customer/subscription id), don't `INSERT` a new row per event — so even
  a dedupe-table miss (race, restart) doesn't double-grant or double-charge
  downstream state.
- **Never treat webhook receipt as the only source of truth for a critical
  state change** — reconcile periodically against the processor's API
  (list subscriptions, check entitlement) so a missed or permanently-failed
  webhook delivery doesn't leave state silently wrong forever.

## 5. Where this fits

`feature-legal-risk-checklist` §"Payments" owns the compliance-checklist
framing (PCI scope, what needs disclosing) for a feature that touches
payments — this skill owns the concrete integration mechanics that satisfy
it. `error-handling-and-resilience` owns idempotency/retry mechanics in
general; §4 above is the payment-specific instance of that same discipline.
`observability-logging-metrics-tracing` owns the general secret-redaction
rule that §3's PAN-logging prohibition is a stricter instance of.

## Sources

Adapted from:
- https://docs.stripe.com/security/guide (PCI scope minimization)
- https://developer.apple.com/app-store/review/guidelines/#in-app-purchase
- https://support.google.com/googleplay/android-developer/answer/9858738
- https://www.revenuecat.com/blog/engineering/app-to-web-purchase-guidelines
- https://docs.stripe.com/webhooks (signature verification, idempotency)
