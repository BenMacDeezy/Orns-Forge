---
name: seo-fundamentals
description: Make a page discoverable and correctly represented when shared or crawled — meta/OG tags, structured data, sitemap/robots. Use when a task affects a public page's discoverability, social-share preview, or search-engine indexing. Triggers on SEO, meta tags, Open Graph, structured data, schema.org, sitemap, robots.txt, canonical URL, search engine.
---

# SEO fundamentals

Scope: seo-fundamentals — meta/OG tags, structured data, and sitemap/robots
for discoverability and correct crawling/sharing. **Duty split with
`core-web-vitals-for-ui`: this skill owns discoverability (can the page be
found, indexed, and correctly represented when shared); `core-web-vitals-for-ui`
owns the performance half (LCP/INP/CLS) that search engines also factor into
ranking — a page can be perfectly discoverable per this skill and still rank
poorly on Core Web Vitals, and vice versa, so treat the two as complementary
checklists, not overlapping ones.**

## 1. Meta tags and Open Graph

- **Every public page needs a unique, accurate `<title>` and
  `<meta name="description">`** — these are what search results and most
  share previews fall back to when Open Graph tags (below) are absent. A
  site-wide default title/description on every page (or worse, none) makes
  every page look identical to a crawler and a search results page alike.
- **Open Graph (`og:*`) tags control how a link renders when shared** on
  platforms that read them (Slack, Discord, iMessage, most social
  platforms) — at minimum set `og:title`, `og:description`, `og:image`,
  `og:url`, and `og:type`. Without them, a shared link falls back to
  whatever the platform can scrape from `<title>`/`<meta description>`/the
  first image, which is inconsistent and often wrong.
- **`og:image` needs an absolute URL** (not relative) and a reasonable fixed
  size (1200×630 is the common safe default) — most consuming platforms
  won't resolve a relative path and some silently drop images outside
  expected aspect ratios.
- **Twitter/X needs its own `twitter:card` tags** (`twitter:card`,
  `twitter:title`, `twitter:description`, `twitter:image`) even though they
  overlap conceptually with Open Graph — X's crawler prefers its own tags
  over `og:*` when both are present, so omitting them degrades the preview
  on that one platform specifically even if OG is fully set.
- **Set a `<link rel="canonical">`** on every page, pointing at the single
  preferred URL for that content — without it, the same content reachable
  via multiple URLs (with/without trailing slash, tracking params, `www.`
  vs. not) can be indexed as duplicate content and split ranking signal
  across copies instead of consolidating it on one URL.

## 2. Structured data (schema.org)

- **Structured data (JSON-LD, embedded as a `<script type="application/ld+json">`
  block) tells a crawler explicitly what a page *is*** — an article, a
  product, an FAQ, a recipe, an event — rather than making it infer that
  from prose. This is what unlocks rich results (star ratings, price,
  breadcrumbs, FAQ accordions directly in search results) beyond a plain
  blue link.
- **Use the schema.org type that actually matches the content**
  (`Product`, `Article`, `FAQPage`, `BreadcrumbList`, `Organization`, etc.)
  — a JSON-LD block claiming a type the page doesn't deliver (e.g.
  `Product` with no purchasable product) risks a manual action from the
  search engine, not just a missed opportunity.
- **JSON-LD is preferred over microdata/RDFa** — it lives in one script
  block, doesn't require interleaving markup attributes through the visible
  DOM, and is what current search-engine documentation recommends as the
  default format.
- **Validate before shipping** — run the markup through the search engine's
  own rich-results testing tool (or an equivalent structured-data validator)
  rather than assuming hand-written JSON-LD matches the schema; a malformed
  or mistyped property silently fails to produce the rich result with no
  visible error on the page itself.

## 3. Sitemap and robots.txt

- **`sitemap.xml`** lists the canonical URLs the site wants crawled/indexed
  — generate it programmatically from the actual route/content set (not
  hand-maintained) so it never drifts out of sync with what the site
  actually serves, and keep it capped to indexable, canonical URLs only
  (not every URL variant). Submit it to search engines' webmaster tools and
  reference it from `robots.txt` (`Sitemap: https://example.com/sitemap.xml`).
- **`robots.txt`** controls crawler *access*, not indexing directly —
  `Disallow` tells a well-behaved crawler not to fetch a path at all. It is
  **not** a reliable way to keep a page out of search results: a disallowed
  URL can still be indexed (typically with no snippet) if other pages link
  to it, because the crawler never fetches it to see a no-index instruction.
- **To actually keep a page out of the index, use `<meta name="robots"
  content="noindex">`** (or the `X-Robots-Tag` HTTP header for non-HTML
  responses) on the page itself — that requires the crawler to be *allowed*
  to fetch it (don't `Disallow` a path you're also trying to `noindex`; the
  crawler needs to reach the page to see the `noindex` instruction at all).
- **Never `Disallow: /` on a production robots.txt** — this blocks the
  entire site from crawling and is a common accidental regression when a
  staging/preview environment's robots.txt (correctly blocking everything)
  gets deployed to production by mistake; treat this file as environment-
  specific config, not a static asset copied unchanged across environments.

## Where this fits — the SEO / Core Web Vitals duty split

**This skill owns discoverability — meta/OG tags, structured data, and
sitemap/robots; `core-web-vitals-for-ui` owns the performance half (LCP,
INP, CLS) — both feed search ranking but are separate implementation
concerns with separate checklists, and a task touching public-page SEO
should consult both rather than assuming either one covers the full
ranking surface.** A page with perfect structured data and a slow LCP still
under-ranks on the performance signal; a fast page with no `canonical`/OG
tags still under-performs on the discoverability signal. Treat them as
complementary, not redundant.

## Sources

Adapted from:
- https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- https://developers.google.com/search/docs/crawling-indexing/robots/intro
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview
- https://ogp.me/
- https://developer.x.com/en/docs/x-for-websites/cards/overview/markup
