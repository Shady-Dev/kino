# Counts

Generated. Run `python3 scripts/build_counts.py` to rewrite the block below and sync the
four figures README states in prose; `--check` reports without writing.

Do not edit the block by hand. These numbers were kept by hand in `IDEAS.md` and
re-measured twenty-two times, and five of those passes shipped a wrong one. Every figure
here is derived from `data/`, `scripts/providers/registry.py`, `sitemap.xml` and `sw.js`.
The city rule is `build_pages.city_of`, reused rather than reimplemented, because
Finnkino's areas carry no `city` field and the city sits in the venue name.

`tests/test_build_counts.py` pins the registry, venue, city, page, sitemap and CACHE rows
against the data. It deliberately does not pin the poster rows: those move on every data
run, and a data run does not re-run this script.

Earlier hand-measured passes, and what each of them measured, are in
[archive/2026-09-ops.md](archive/2026-09-ops.md).

<!-- counts:start -->
| | |
|---|---:|
| providers | 83 |
| venues | 134 |
| cities | 96 |
| cities with more than one venue | 17 |
| local providers (venues) | 12 (34) |
| venues per adapter, largest 5 | `etiketti` 30, `Finnkino` 17, `nexxo` 13, `biorex` 12, `johku` 7 |
| generated pages per language | 151 |
| sitemap URLs | 303 |
| off-origin poster references | 0 |
| `sw.js` CACHE | `leffavuoro-v216` |
<!-- counts:end -->
