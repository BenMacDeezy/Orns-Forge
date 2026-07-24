# Curated palettes and pairings

Reference data to inform token choices in `design-tokens-pipeline` — not a
style picker. Nothing here is a "pick your industry, get your palette"
lookup table; that would hand back exactly the generic-default output
`anti-generic-design-restraint` exists to veto. Use this to calibrate a
choice already made for the brief, never to make the choice for you.

## Font pairings

Ten proven display+body pairings, adapted from the mined source (never
verbatim), each with the character it reads as and the weights worth
loading — load only the weights actually used, not the full family.

| Display | Body | Character | Weights to load |
|---|---|---|---|
| Playfair Display | Inter | High-contrast serif elegance against a clean workhorse sans — editorial, premium. | Display 500/600/700; body 400/500/600 |
| Space Grotesk | DM Sans | Geometric with a distinctive ear on the G/g — technical without being cold. | Display 500/600/700; body 400/500 |
| Cormorant Garamond | Libre Baskerville | All-serif, literary register — two serifs at different optical sizes, not a mismatch. | Display 500/600; body 400/700 |
| Fredoka | Nunito | Rounded terminals both faces — genuinely playful, not playful-as-decoration. | Display 500/600; body 400/600 |
| Bebas Neue | Source Sans 3 | All-caps condensed display, hero/headline sizes only — never body, never sentence case. | Display 400 (single weight); body 400/600 |
| Lora | Raleway | Organic serif curves with an elegant geometric sans — calm, unhurried register. | Display 500/600; body 400/500 |
| JetBrains Mono | IBM Plex Sans | Mono for code/data, humanist sans for UI chrome around it — technical-precise. | Mono 400/500; sans 400/500/600 |
| Outfit | Work Sans | Both geometric, display face carries more personality — safe general-purpose pair. | Display 500/600; body 400/500 |
| Newsreader | Roboto | Built for long-form reading paired with a neutral UI workhorse — content-heavy register. | Display 500/600; body 400/500 |
| Syne | Manrope | Unusual, angular display against a readable geometric sans — avant-garde, spend with restraint. | Display 600/700; body 400/500 |

Pair a characterful display face used with restraint against a quieter body
face — never the same family stretched across both roles unless the register
is deliberately minimal (a Swiss/functional brief is the one case a single
family earns its keep).

## Palette construction, by principle not by industry

Don't reach for a pre-built "SaaS blue" or "wellness green" — that's the
generic-default trap in color form. Construct the palette from three moves
instead, in this order:

1. **Neutrals first.** Build the neutral scale before touching any hue — 9
   to 12 lightness steps from near-white to near-black. Every text, border,
   and surface role derives from this scale before a single saturated color
   enters the system. A palette with a strong accent sitting on a weak or
   arbitrary neutral scale still reads unfinished.
2. **One saturated accent.** Pick exactly one high-chroma color for
   interactive/CTA use (links, primary buttons, focus rings). Everything
   else stays desaturated or lightly tinted neutral. Two competing
   saturated colors fighting for attention is the tell of an unconsidered
   palette, not a rich one.
3. **Dark mode as a luminance flip, not an inversion.** Don't literally
   invert values. Flip the *direction* of the lightness ramp (background
   moves from near-white at the light end to near-dark at the dark end)
   while holding hue and chroma relationships steady, then re-tune the
   accent's lightness so it still clears contrast against the new dark
   surface — the same hue at the same chroma often needs a lighter L step
   to read correctly on dark.

## OKLCH-first

Author the palette in OKLCH, not HSL or raw hex. OKLCH's lightness channel
is perceptually uniform across hue — two colors at the same `L` read as
equally light regardless of hue, which HSL's lightness does not guarantee
(a pure blue and a pure yellow at "the same" HSL lightness look nothing
alike in perceived brightness). That property is exactly what neutrals-first
scale construction and the dark-mode luminance flip above depend on: step
the scale by `L`, and every step — and its dark-mode counterpart — lands at
a predictable, comparable contrast.

## Sources

Mined from, never a wholesale adoption:
- nextlevelbuilder/ui-ux-pro-max-skill (MIT) — font-pairing data
  (`data/typography.csv`) adapted into the table above. Its companion
  `data/colors.csv` is a by-industry palette pick-list (SaaS, e-commerce,
  fintech, …); this file deliberately does not mine that shape of data —
  synthesizing register-level construction principles instead is the point,
  per `anti-generic-design-restraint`.
