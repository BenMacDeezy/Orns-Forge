---
name: i18n-and-localization
description: Internationalize and localize user-facing strings — message extraction, ICU MessageFormat pluralization, RTL layout, and date/number formatting. Use when adding user-facing strings, adding a new locale, or building a component that must lay out correctly in a right-to-left language. Triggers on i18n, l10n, localization, translation, pluralization, RTL, locale, date formatting, number formatting.
---

# i18n and localization

Scope: i18n-and-localization — message extraction, ICU pluralization, RTL
layout, and date/number formatting for user-facing strings. It does not own
in-app content moderation, legal-notice translation review, or performance —
those stay with their existing owners.

## 1. Translation-key discipline

- **Never interpolate user-facing text with string concatenation.** Every
  user-facing string gets a stable, hierarchical **key**
  (`checkout.summary.itemCount`, not `"You have " + n + " items"`) —
  concatenation breaks the moment a translator needs to reorder words, and
  many languages do reorder them.
- **Keys describe location/purpose, not the English source text.** A key
  named after the English string (`"you_have_n_items"`) drifts the moment the
  English copy changes; a purpose-scoped key doesn't.
- **No string ever ships hardcoded outside the catalog** — including error
  messages, `alt`/`aria-label` text, empty states, and toast copy. A string
  left out of extraction is a string that silently stays English forever.
- Keep **one source-of-truth locale** (usually `en`) authoritative; every
  other locale is a translation of it, not an independent edit — otherwise
  locales drift out of sync with no way to tell what's stale.

## 2. Message extraction

- Use an extraction tool (`react-intl`/FormatJS's `extract`, `i18next-parser`,
  `lingui extract`) that scans source for the translation-call sites and
  generates/updates the catalog automatically — hand-maintained catalogs
  drift from the code the moment someone adds a string without remembering
  the second file.
- Run extraction in CI (or a pre-commit hook) and fail the build on an
  **unused key** (dead translation, safe to prune) or a **missing key**
  (string added to code but never extracted) — both are silent-drift bugs
  that are cheap to catch mechanically and expensive to catch by inspection.
- Provide **translator context**, not just the bare string: a description
  comment on the key when the string is short/ambiguous (`"Save"` the verb vs.
  `"Save"` the noun) — a translator working from a spreadsheet of bare strings
  guesses, and guesses are wrong often enough to matter.

## 3. ICU MessageFormat pluralization

Never branch plurals in application code (`count === 1 ? "item" :
"items"`) — that's an English-only rule (exactly two forms, cutoff at 1) and
breaks for every language that doesn't share it. Use **ICU MessageFormat**
`plural` syntax and let the i18n library pick the right CLDR plural category
for the active locale:

```
{count, plural,
  one {# item}
  other {# items}
}
```

- English has two categories (`one`, `other`); many languages need more.
  Arabic has six (`zero`, `one`, `two`, `few`, `many`, `other`); Polish and
  Russian distinguish `few` vs `many` by trailing digit, not just magnitude.
  Never hardcode a category list — the plural rule is locale data, and the
  i18n library resolves it from CLDR, not from your code.
- The same ICU syntax handles **gender/`select`** (`{gender, select, male
  {...} female {...} other {...}}`) and **nested** plural-inside-select for
  copy that varies on both axes — reach for `select`/`selectordinal` instead
  of a second bespoke branching mechanism.
- Interpolated values go inside the ICU string (`{count}`), never
  concatenated around the translated fragment — concatenation reintroduces
  the word-order problem key discipline (§1) exists to avoid.

## 4. RTL layout

A right-to-left locale (Arabic, Hebrew, Farsi, Urdu) doesn't just mirror
text — it mirrors the **whole layout axis**. Two failure modes to design
against:

- **Use logical, not physical, CSS properties.** `margin-inline-start` /
  `padding-inline-end` / `inset-inline-start`, not `margin-left` /
  `padding-right` / `left` — logical properties flip automatically with
  `dir="rtl"`; physical ones don't and require a manual RTL override
  stylesheet that inevitably falls out of sync with the LTR one.
- **Set `dir` at the document/root level** (`<html dir="rtl">` or the
  framework's locale-provider equivalent) so the browser's own bidi
  algorithm and logical-property resolution apply consistently, rather than
  toggling direction per-component.
- **Icons that encode direction must flip** — a "next"/"forward" chevron,
  a back arrow, a progress/reading-order indicator — while icons that don't
  encode direction (a search magnifier, a checkmark) must NOT flip. Flipping
  everything indiscriminately is as wrong as flipping nothing.
- **Mobile: `flexDirection` flips too.** React Native has no CSS cascade or
  logical properties (see `react-native-foundations`) — a `row` flex
  container laid out LTR reads left-to-right by explicit child order, so an
  RTL locale needs either `I18nManager.isRTL`-driven direction handling
  (`row` → `row-reverse`) or, on modern RN, opting into automatic RTL flip
  via `I18nManager.forceRTL`. Test the same screen in both directions — a
  layout that only looks right in the default direction has an RTL bug, not
  an RTL feature gap.
- Test with a real RTL locale, not a mirrored placeholder — pseudo-RTL
  catches gross layout breaks but not language-specific text issues (line
  height for Arabic diacritics, numeral direction inside RTL text).

## 5. Date and number formatting

- **Never hand-format dates/numbers/currency with string templates.** Use
  the platform's locale-aware formatter — `Intl.DateTimeFormat`,
  `Intl.NumberFormat`, `Intl.RelativeTimeFormat` on web/Node, or the i18n
  library's equivalent — and pass the active locale explicitly rather than
  relying on an implicit default.
- **Currency formatting needs both the amount and the currency code**
  (`Intl.NumberFormat(locale, { style: "currency", currency: "USD" })`) —
  the symbol, decimal separator, and thousands separator all vary by locale
  independently of the currency itself (`1,234.56` vs `1.234,56`).
  `payment-integration-discipline` owns the underlying money-handling
  correctness (decimal precision, integer minor units); this skill owns
  only how that amount is *displayed*.
- **Store timestamps in UTC, format at display time** in the viewer's
  locale/timezone — formatting once and storing the formatted string loses
  the ability to reformat for a different locale/timezone later and breaks
  sorting.
- **Relative time ("3 days ago") also needs `Intl.RelativeTimeFormat`**,
  not a hardcoded English unit table — pluralization rules (§3) apply to
  relative-time units too.

## Where this fits

Message extraction and the translation-key catalog are this skill's core
surface; the CSS/flex mechanics of RTL for web `flex-direction` live here,
and the React Native equivalent cross-references `react-native-foundations`
for the platform-specific API (`I18nManager`) rather than duplicating it.

## Sources

Adapted from:
- https://formatjs.io/docs/core-concepts/icu-syntax/
- https://cldr.unicode.org/index/cldr-spec/plural-rules
- https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties
- https://reactnative.dev/docs/next/i18nmanager
