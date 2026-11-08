# The dark theme: what it measures and what it was retuned to

The maintainer found the dark theme hard to read and supplied a reference brief on
2026-11-08: principles, WCAG 2 and APCA targets, an example palette from another product,
and a test checklist. The maintainer's instruction was to use it as guidance and adapt it to
Leffavuoro's own colours, not to copy its palette. This file holds what was measured, what
the targets are, and which ones the retune meets.

## Sources

- The maintainer's brief, read 2026-11-08. It is kept outside this repository. Its targets
  are restated in the table below where they are used.
- WCAG 2.2, 1.4.3, 1.4.6 and 1.4.11, for the contrast ratio.
- APCA in a Nutshell, read 2026-11-08 (git.apcacontrast.com/documentation). Lc 75 is its
  body-text minimum, Lc 60 the minimum for content text that is not body text, Lc 45 for
  headlines at 24 px bold or 36 px, and Lc 30 the absolute minimum, which covers disabled
  and placeholder text.
- `scripts/accent_check.py --theme dark`, for the chain markers.

## Method

Measured 2026-11-08 at `bcd7643a03`, on the committed data.

1. Every visible element with its own text, in nine app views and three generated pages:
   the start page, the Ajat list for Helsinki (all chains), the Leffat list for Finnkino
   Sello, the film sheet with a past screening, the ticket menu with an item hovered, the
   venue picker at rest and with a row hovered, the calendar, a filter chip hovered, a
   theatre page in Finnish and English, and a city page. Placeholders are read from
   `::placeholder`.
2. Colours from `getComputedStyle`, composited down to opaque: a translucent background is
   blended over what is under it, and an element or ancestor with `opacity` below 1 is
   blended over the colour behind that group.
3. WCAG 2 ratio and APCA-W3 Lc (0.0.98G-4g constants). The implementation reproduces the
   published Lc of 63.056 for `#888` on white, -68.54 for white on `#888`, and the brief's
   -82, -63 and -94 for its own three text pairs.
4. Chromium and WebKit (Playwright 1.62.0), 1200 x 900. Both engines gave the same 102
   distinct dark pairs and the same numbers. Dark mode set by the stored switch and by the
   OS setting gave identical records in both themes.

The token-level table below is what the scan found, grouped by the token pair drawn. Where
a state was not on screen in the fixture data (a sold-out ticket, a thin rating ring, an
inactive legend button), the pair is computed from the CSS rule and the tokens.

## Findings, before the retune

Dark tokens: `--bg #0D0E12`, `--surface #16181F`, `--chip-bg #1C1F28`, `--ink #EDEDEA`,
`--muted #AEB5C2`, `--line #262A33`, `--accent` and `--accent-text #E8B84B`,
`--accent-soft #2A2415`, `--accent-on-ink #8A6508`, `--past #4A4F5A`.

Lowest contrast first. Lc is shown as a magnitude. A miss is marked **miss**.

| Pair as drawn | Where | WCAG | Lc | Brief target | |
|---|---|---|---|---|---|
| `--past` time, ticket at opacity .45 | past ticket, sheet and Leffat | 1.28 | 0.0 | disabled 4.3, Lc 30 | **miss** |
| `--muted` at .28 on `--surface` | calendar days out of range | 1.82 | 8.7 | disabled 4.3, Lc 30 | **miss** |
| `--ink` at .3 | calendar arrow, disabled | 2.44 | 15.9 | disabled 4.3, Lc 30 | **miss** |
| `--muted`, ticket at .45 | past ticket room and language | 2.59 | 16.8 | disabled 4.3, Lc 30 | **miss** |
| `--muted` at .5 on `--bg` | chain legend button, off | 3.13 | 20.7 | disabled 4.3, Lc 30 | **miss** |
| `--accent-on-ink` on `--ink` | "Tänään" on the selected day | 4.54 | 65.5 | label 7, Lc 60 | **miss** |
| `--ink` at .55 | sold-out ticket time | 5.07 | 37.8 | disabled 4.3, Lc 30 | |
| `--ink` at .55 on `--bg` | rating ring with few votes | 5.48 | 38.6 | disabled 4.3, Lc 30 | |
| `--muted` at .75 on `--bg` | picker's city and region counts | 5.66 | 39.7 | muted 7, Lc 60 | **miss** |
| `--muted` on `--accent-soft` | ticket menu item's detail line | 7.48 | 59.2 | muted 7, Lc 60 | **miss** |
| `--muted` on `--chip-bg` | ticket room, language, price | 7.98 | 60.1 | muted 7, Lc 60 | |
| `--muted` on `--surface` | day chip weekday, filter chips | 8.60 | 60.9 | muted 7, Lc 60 | |
| `--accent-text` on `--chip-bg` | | 8.93 | 66.1 | link 7, Lc 60 | |
| `--muted` on `--bg` | synopsis on pages, votes, footer | 9.36 | 61.7 | muted 7, Lc 60 | |
| `--accent-text` on `--bg` | cinema name in Ajat, trailer link | 10.46 | 67.7 | link 7, Lc 60 | |
| `--ink` on `--accent-soft` | hovered picker row, menu item | 13.15 | 93.1 | body 9-13, Lc 75-90 | **miss** |
| `--ink` on `--chip-bg` | ticket time | 14.03 | 94.0 | body 9-13, Lc 75-90 | **miss** |
| `--ink` on `--surface` | day chip date, picker label | 15.11 | 94.8 | body 9-13; headings 15 max | **miss** |
| `--ink` on `--bg` | titles, sheet synopsis, picker rows | 16.44 | 95.7 | body 9-13; headings 15 max | **miss** |
| `--bg` on `--ink` | pressed chip, selected day | 16.44 | 94.8 | filled 7, Lc 60 | |

Non-text:

| Pair | WCAG | Brief target | |
|---|---|---|---|
| `--bg` to `--surface` | 1.09 | step 1.1-1.2 | **miss** |
| `--surface` to `--chip-bg` | 1.08 | step 1.1-1.2 | **miss** |
| `--line` on `--chip-bg`, `--surface`, `--bg` | 1.15, 1.23, 1.34 | divider 1.4-1.7 | **miss** |
| `--accent` on each surface (focus ring, pressed border) | 8.93 to 10.46 | 3 | |
| chain markers, weakest, Bio Forum on `--chip-bg` | 3.00 | 3 | |

Other checklist items: the app set no `color-scheme`, so the browser's own parts
(scrollbars, form-control defaults) were drawn for a light scheme in the dark theme (MDN,
`color-scheme`). The generated
pages already set it. `-webkit-font-smoothing:antialiased` is on `body` in both. No image
is filtered or inverted in dark; only a sold-out ticket is greyscaled, in both themes.

**What made it hard to read, as measured:** text was brighter than the brief allows. The
main ink measured 16.4:1 and Lc 95.7 on a page close to black, above the 9 to 13:1 the
brief gives body text and above its 15:1 ceiling for headings, which is the halation case
the brief describes. The faded states went the other way: a past ticket was 1.28:1 and a
calendar day outside the data 1.82:1, so they could not be read at all. The divider and
surface steps sat below the brief's range, so tickets and fields had weak edges.

## The constraint that bounds the surfaces

`--chip-bg #1C1F28` cannot get lighter. The chain markers' dark shades are held to 3:1
against every dark surface (CLAUDE.md, `accent_check.SURFACES`). They are all lighter
than the surfaces, so the lightest surface is the binding one, and five shades already
measure 3.00:1 on it, Bio Forum's `#905F0C` among them. A lighter ticket ground would need
new chain shades and a new ΔE00 solve. The brief's step of 1.1 to 1.2 between page, panel
and dialog would then need a page darker than the one it replaced, which is the opposite
of its third principle. The retune keeps `--chip-bg`, lifts the page and the panel toward
it, and gives the edges to `--line` instead.

## The retune

On 2026-11-08 the maintainer added that the design must not change: only the colour values
of the dark theme move, its tokens and the hard-coded dark colours that bypass them. No
layout, size, opacity, typography or light value changes, and the gold and chain markers
stay unless a measured target requires a dark shade to move. Same token names, same gold,
same chain shades. Light theme untouched.

| Token | Before | After | Why |
|---|---|---|---|
| `--bg` | `#0D0E12` | `#111318` | Off near-black, same cool grey, still below `--chip-bg`. |
| `--surface` | `#16181F` | `#171A20` | Kept between page and ticket. |
| `--chip-bg` | `#1C1F28` | unchanged | Bound by the marker rule above. |
| `--ink` | `#EDEDEA` | `#D7D7D4` | 12.9:1 on the page, top of the body range; same warm off-white. |
| `--muted` | `#AEB5C2` | `#B3B9C5` | Clears Lc 60 on `--accent-soft` and on tickets. |
| `--line` | `#262A33` | `#343842` | 1.40 to 1.58:1 on all three surfaces. |
| `--accent-on-ink` | `#8A6508` | `#523C05` | The gold label on the light chip reaches 7:1; same hue, darker. |
| `--past` | `#4A4F5A` | `#B3B9C5` | The past time reads at the level of its own details. |
| `--chip-hover-ink` | `#0D0E12` | `#111318` | Follows `--bg`, as before. Unused by any rule. |
| `--accent`, `--accent-text`, `--accent-soft`, `--shadow` | | unchanged | |

`theme-color`, its script fallback and the manifest are hard-coded copies of the dark page
colour and follow it. The generated pages carry the same five token changes in both of
their dark blocks; they have no `--accent-on-ink` or `--past`.

### After

Measured on the page where the state was on screen, computed from the tokens and the
unchanged opacities otherwise. Before values in brackets where a pair moved the wrong way
or stayed below target.

| Pair as drawn | WCAG | Lc | Target | |
|---|---|---|---|---|
| calendar day out of range, `--muted` at .28 | 1.87 (1.82) | 9.5 | disabled 4.3, Lc 30 | **miss** |
| calendar arrow disabled, `--ink` at .3 | 2.22 (2.44) | 13.7 | disabled 4.3, Lc 30 | **miss** |
| past ticket time, `--past` at .45 | 2.72 (1.28) | 18.5 | disabled 4.3, Lc 30 | **miss** |
| past ticket details, `--muted` at .45 | 2.72 (2.59) | 18.5 | disabled 4.3, Lc 30 | **miss** |
| legend button off, `--muted` at .5 | 3.23 (3.13) | 22.3 | disabled 4.3, Lc 30 | **miss** |
| sold-out ticket time, `--ink` at .55 | 4.34 (5.07) | 32.8 | disabled 4.3, Lc 30 | |
| thin rating ring, `--ink` at .55 | 4.62 (5.48) | 33.5 | disabled 4.3, Lc 30 | |
| picker counts, `--muted` at .75 on `--bg` | 5.78 (5.66) | 41.7 | muted 7, Lc 60 | **miss** |
| picker count pressed, `--bg` at .75 on `--ink` | 6.77 (8.08) | 69.2 | muted 7, Lc 60 | **miss** |
| "Tänään", `--accent-on-ink` on `--ink` | 7.25 | 70.6 | label 7, Lc 60 | |
| `--muted` on `--accent-soft` | 7.83 | 61.6 | muted 7, Lc 60 | |
| `--muted` on `--chip-bg` | 8.36 | 62.4 | muted 7, Lc 60 | |
| `--muted` on `--surface` | 8.85 | 63.1 | muted 7, Lc 60 | |
| `--accent-text` on `--chip-bg` | 8.93 | 66.1 | link 7, Lc 60 | |
| `--muted` on `--bg` | 9.43 | 63.7 | muted 7, Lc 60 | |
| `--accent-text` on `--bg` | 10.08 | 67.4 | link 7, Lc 60 | |
| `--ink` on `--accent-soft` | 10.69 | 79.3 | body 9-13, Lc 75-90 | |
| `--ink` on `--chip-bg` | 11.41 | 80.2 | body 9-13, Lc 75-90 | |
| `--ink` on `--surface` | 12.08 | 80.9 | body 9-13, Lc 75-90 | |
| `--ink` on `--bg` | 12.88 | 81.5 | body 9-13, Lc 75-90 | |
| `--bg` on `--ink`, pressed chips | 12.88 | 81.7 | filled 7, Lc 60 | |
| `--line` on `--chip-bg`, `--surface`, `--bg` | 1.40, 1.49, 1.58 | | divider 1.4-1.7 | |
| `--accent` on each surface | 8.93 to 10.08 | | 3 | |
| chain markers, weakest, Bio Forum on `--chip-bg` | 3.00 | | 3 | |

### Where it deliberately misses the brief

- **Faded states, 4.3:1.** Past tickets, calendar days out of range, the disabled calendar
  arrow and an inactive legend button are drawn at opacity .28 to .5, and opacity is not
  a colour value. At .45 even white would bring a past time to 4.30:1, and the details and
  calendar days share `--muted` with every other secondary line. Colour alone lifts the
  past time from 1.28 to 2.72:1 and leaves the rest within 0.4 of where they were. The
  disabled arrow and the pressed picker count lost a little (2.44 to 2.22, 8.08 to 6.77,
  the latter still Lc 69) because the ink they are drawn from is dimmer. The fix is under
  "Proposals beyond colour values".
- **Headings, Lc 85 to 95.** `--ink` is both body and heading colour. On the page Lc 85
  needs 13.5:1, past the brief's body ceiling of 13, so one token cannot meet both. Body
  text was chosen: most of what a reader reads is body text, and headings are
  15 to 24 px at weight 700 to 900, where APCA's own minimum is Lc 45 to 60. They measure
  Lc 80 to 81.5. A separate heading token would close it, and is a design change of its own.
- **Surface steps, 1.1 to 1.2.** Page to panel 1.07, panel to ticket 1.06 (before: 1.09
  and 1.08). Bound by `--chip-bg`, explained above. Edges come from `--line` instead, now
  inside the divider range on every surface.
- **Dialogs one step lighter.** The film sheet stays on `--bg`. It sits over a .55 black
  overlay, and a lighter sheet would have no room left below `--chip-bg` for its tickets.
- **Borders of inputs and buttons, 3:1.** Controls carry `--line` borders at 1.4 to 1.6,
  the same treatment as the light theme. Each control is also a filled shape with a text
  label. Raising every control border to 3:1 is a visual change to both themes.

## Proposals beyond colour values

Built and measured on 2026-11-08, then taken out under the colour-only instruction. Each
keeps the light theme identical by giving the token the old literal in `:root`.

- Opacity tokens for the faded states, dark values in brackets: `--fade-past` .45 (.7),
  `--fade-off` .28 (.65), `--fade-nav` .3 (.55), `--fade-count` .75 (1), `--fade-legend`
  .5 (.65). Measured in Chromium: past ticket 4.76:1 Lc 36.5, calendar day 4.46:1, arrow
  4.38:1, legend 4.62:1, picker counts 9.43:1 Lc 63.7. All clear the brief.
- `color-scheme:dark` in the app's dark block, so scrollbars and form-control defaults are
  drawn dark. The generated pages already set it.
- A heading token brighter than body text, for the Lc 85 heading target.
- A sheet one step lighter than the page, if tickets get a ground that allows it.

## Open questions

- The light theme shows the same faded states at 1.37:1 (past ticket) and 1.49:1
  (calendar). It was kept byte-for-byte unchanged here by instruction.
- `status/index.html` and `tietosuoja/index.html` carry their own dark tokens, and the
  privacy page's already differ from the app's (`#101216`, `#EDEFF3`). Neither was in this
  change.

## Implementation status

Implemented, colour values only, in `index.html`, `sw.js` (CACHE v313),
`manifest.webmanifest`, `scripts/build_pages.py` and the regenerated pages, with
`accent_check.SURFACES` and the CLAUDE.md surface list moved to the new values.
`accent_check.py --theme dark` prints the same report before and after.

Verified 2026-11-08 under a pinned clock in Chromium and WebKit, the HEAD build and this
one served side by side. Light theme: 47,394 lines of computed colour, background,
borders, outline, shadow, opacity, filter and `color-scheme`, every element and
pseudo-element in the twelve views and both ways of choosing the theme, 0 differ. Dark
theme: opacity, filter, shadow and `color-scheme` unchanged; only colours and the colour
stops of gradients moved. The stored switch and the OS setting give identical records.
**Next step:** the maintainer's look at the screenshots and the release decision.
