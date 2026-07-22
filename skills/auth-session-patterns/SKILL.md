---
name: auth-session-patterns
description: Build authentication and session handling correctly the first time — OAuth/OIDC flows, session-vs-token storage per platform (httpOnly cookies on web, secure keychain/MMKV on mobile), refresh-token rotation, CSRF, and RBAC basics. Use when adding sign-in, wiring an OAuth/OIDC provider, choosing where a session or token lives, implementing token refresh, or scoping role/permission checks. Triggers on auth, login, sign-in, OAuth, OIDC, session, token, refresh, CSRF, RBAC, permissions.
---
<!-- last-verified: 2026-07 -->

# Auth & session patterns

**`auth` / `token` / `secret` is a named `forge-security` dispatch trigger**
(`docs/conventions.md`, "Verification economics"). Any diff that touches
authentication, session storage, or credential/token handling pulls
`forge-security` into review regardless of task tier — this skill builds the
change correctly, it does not substitute for that review.

## 1. OAuth / OIDC flow shape

Authorization Code + PKCE is the baseline flow for both web and native/mobile
clients in 2026 — the implicit flow is deprecated (OAuth 2.1 drops it
entirely). PKCE closes the authorization-code-interception gap for public
clients (SPAs, mobile apps) that can't hold a client secret.

- **Server-rendered / full-stack app**: authorization code exchange happens
  on the server, using a confidential client secret. The browser never sees
  the code-for-token exchange.
- **SPA / mobile (public client)**: no client secret exists to protect —
  PKCE (code_verifier/code_challenge) is mandatory, not optional-hardening.
- **OIDC vs plain OAuth**: OAuth authenticates *access* (what you can call);
  OIDC layers an identity assertion (the `id_token`, a signed JWT) on top for
  *who the user is*. If the app needs "who is this user" (not just "can this
  client call this API"), it needs OIDC's `id_token` — validate its
  signature, `iss`, `aud`, and `exp`, don't just decode and trust it.
- Validate `state` on the callback (CSRF on the auth flow itself) and `nonce`
  in the `id_token` (replay protection) — both are part of the spec, not
  extra hardening.

## 2. Session vs. token storage, per platform

The 2026 baseline pattern most mature providers (Auth0, Clerk, Supabase)
converge on: **short-lived access token in memory, refresh token in an
`httpOnly`, `Secure`, `SameSite` cookie** — never put a refresh token
somewhere JS can read it.

- **Web**:
  - Session/refresh token → `httpOnly` cookie (`Secure`, `SameSite=Lax` or
    `Strict`). `httpOnly` blocks the #1 theft vector (XSS reading
    `document.cookie`); it does not block CSRF — that's a separate control
    (§4).
  - Access token → short-lived, kept in memory (a JS variable/store), never
    `localStorage`/`sessionStorage`. Storage APIs are readable by any script
    on the page — one XSS hole exfiltrates every token sitting there.
- **Mobile (React Native)**:
  - Tokens (access + refresh) → OS-level secure storage: `expo-secure-store`
    (Keychain on iOS, Keystore-backed Encrypted SharedPreferences on
    Android), or the bare-RN equivalent (`react-native-keychain`). This is
    the credential store — encryption happens at the OS level, independent
    of app code.
  - `react-native-mmkv` is **not** a substitute for secure storage: it's a
    fast key-value cache for app state, preferences, and non-secret data.
    MMKV's own encryption depends on a key that, if embedded directly in JS,
    gives weak protection — if you use MMKV's encryption at all, source the
    encryption key from `expo-secure-store` rather than hardcoding it.
    Practical split: SecureStore/Keychain for secrets, MMKV for everything
    else.
- Either platform: never log tokens, never put them in URL query strings
  (they end up in server logs, browser history, and Referer headers).

## 3. Refresh-token rotation

Static, long-lived refresh tokens are a standing liability — one leak grants
indefinite access. Rotation bounds the blast radius:

- Each use of a refresh token issues a **new** refresh token and invalidates
  the old one (one-time use).
- **Reuse detection**: if an already-invalidated refresh token is presented
  again, that's a signal the token was stolen and used out-of-band (attacker
  and legitimate client racing, or a replay after theft) — revoke the entire
  token family (every token descended from that session), not just the one
  presented, and force re-authentication.
- Keep the refresh token's lifetime bounded even with rotation (e.g. sliding
  window with an absolute cap) — rotation limits a single leaked token's
  window, it doesn't make the session eternal.
- Auth.js/NextAuth v5 does not rotate OAuth provider access tokens for you
  out of the box — that's implemented in the `jwt`/`session` callbacks
  against the provider's refresh endpoint; don't assume any library does
  this silently without checking its docs for your specific provider.

## 4. CSRF

`httpOnly` stops XSS from reading a cookie; it does nothing to stop a
different origin's page from *triggering* a request that rides the cookie
automatically — that's CSRF, and needs its own control on every
state-changing (non-GET) endpoint:

- **`SameSite=Lax` (default in modern browsers) or `SameSite=Strict`** on the
  session cookie is the first line — it blocks the cookie from being sent on
  most cross-site requests. Lax still allows top-level navigation (a link
  click), so it is not sufficient alone for highly sensitive actions.
  `SameSite=None` requires `Secure` and reopens the cross-site-send case —
  only use it when the app genuinely needs cross-site cookie delivery (e.g.
  an embedded widget), and pair it with an explicit CSRF token.
- **Double-submit cookie or synchronizer token pattern** as the explicit
  control: a token issued to the client and required back on the request
  (header or body) that the browser's automatic cookie-attachment can't
  forge, since a cross-site attacker page can't read the cookie to copy its
  value into the header.
- Never rely on `SameSite` alone for a session that guards money movement,
  permission changes, or account-security actions — layer the explicit token
  check.

## 5. RBAC basics

- **Authorization is a server-side check on every request**, not a
  client-side conditional that merely hides a button — a client-only check
  is cosmetic; the caller can hit the endpoint directly.
  (`forge-secure-diff-review` §"Category deep-checks" — broken authz/IDOR is
  the same failure mode.)
- Model roles as a set of **permissions**, not a hardcoded role-name switch
  scattered through handlers — `if (user.role === "admin")` sprinkled across
  the codebase drifts out of sync the moment a new role is added; a
  permission check (`can(user, "invoice:refund")`) centralizes the mapping.
  Prefer this for anything beyond 2-3 static roles.
  <!-- forge-security-trigger: this bullet's "authorization is a server-side
       check on every request" restates the CWE-862/863 category in
       forge-secure-diff-review's fast-triage list; keep the two in sync if
       either is revised. -->
- Authorization-before-amount/scope: check what the caller **is entitled
  to**, not what the request **claims** — e.g. authorize "this caller may
  refund up to $X on orders they own," don't trust an `amount` or
  `resourceId` read straight from client input as the authorization boundary
  itself.
- Every new resource-by-ID handler needs an ownership/entitlement check on
  that specific ID, not just "caller is authenticated" — this is exactly
  `forge-secure-diff-review`'s broken-authz/IDOR check, and it fires on
  every new authenticated route this skill produces.

## 6. Library citations — independent-vetting caveat

**Every library named below is a starting point, not an endorsement taken on
the vendor's word.** Before adopting one, independently verify its current
security posture (recent CVEs, maintenance cadence, how it actually
implements the claims below) rather than trusting the project's own
marketing copy — the same standard `forge-secure-diff-review` applies to any
new dependency/integration in a diff (§"New integrations").

- **Auth.js / NextAuth v5**: full rewrite, stable since late 2024;
  OAuth/OIDC-provider integrations, JWTs encrypted (JWE, A256GCM) by default
  when using the JWT session strategy. Does not rotate OAuth provider access
  tokens automatically — implement rotation in the `jwt` callback per
  provider. Verify: https://authjs.dev/getting-started/migrating-to-v5 and
  https://authjs.dev/guides/refresh-token-rotation (checked 2026-07).
- **Clerk**: hosted/managed auth; stores its session token as an `httpOnly`
  cookie and documents `SameSite` configuration for CSRF mitigation. Managed
  services shift *operational* trust to the vendor but do not remove the
  need to independently verify their security claims before relying on them
  for a sensitive app. Verify: https://clerk.com/docs/guides/how-clerk-works/overview
  (checked 2026-07).
- **Lucia**: no longer a maintained framework/library as of its v3 sunset —
  its docs now ship as a reference/pattern guide ("copy the code you need")
  rather than an installed dependency. Treat anything sourced from it as
  code you own and must maintain, not a package with upstream security
  patches. Verify: https://lucia-auth.com/sessions/basic (checked 2026-07)
  and https://github.com/lucia-auth/lucia/discussions/112.
- **expo-secure-store / react-native-keychain**: wrap OS keychain/keystore
  APIs; the security property comes from the OS, not the wrapper — verify
  the wrapper hasn't silently fallen back to unencrypted storage on a given
  platform/version before trusting it in production.

## Before you ship — checklist

- [ ] Auth flow uses Authorization Code + PKCE (never implicit) for any
      public client (SPA, mobile)
- [ ] `id_token` (OIDC) is signature-, `iss`-, `aud`-, and `exp`-validated,
      not just decoded
- [ ] `state` and `nonce` are checked on the OAuth/OIDC callback
- [ ] Web: refresh/session token in an `httpOnly Secure SameSite` cookie;
      access token in memory only — never `localStorage`/`sessionStorage`
- [ ] Mobile: tokens in `expo-secure-store`/Keychain, never in MMKV/AsyncStorage
      unprotected; MMKV encryption key (if used) itself comes from secure storage
- [ ] Refresh tokens rotate on use, with reuse detection revoking the token family
- [ ] Every state-changing endpoint has an explicit CSRF control beyond `SameSite`
- [ ] Every authenticated handler checks server-side entitlement on the
      specific resource ID, not just "is logged in"
- [ ] Any auth library's security claims were checked against its own current
      docs/changelog, not taken on the vendor's word
- [ ] This diff was flagged for `forge-security` review (auth/token/secret trigger)

---
Adapted from:
- Auth.js — https://authjs.dev/getting-started/migrating-to-v5, https://authjs.dev/guides/refresh-token-rotation (checked 2026-07)
- Clerk — https://clerk.com/docs/guides/how-clerk-works/overview, https://clerk.com/articles/authentication-security-in-web-applications (checked 2026-07)
- Lucia — https://lucia-auth.com/sessions/basic, https://lucia-auth.com/sessions/cookies/ (checked 2026-07)
- Expo SecureStore — https://docs.expo.dev/versions/latest/sdk/securestore/ (checked 2026-07)
- OAuth 2.1 / PKCE — https://oauth.net/2.1/
