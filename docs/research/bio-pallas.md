# Bio Pallas: lines beside a row's title

`pallas.py` reads a row's title block for runtime, age limit (`META_RE`) and an audio marker
(`LANGS`). This file records what else the block carries. Decision record:
[2026-09-providers.md](../archive/2026-09-providers.md).

## Findings

- **Read 2026-10-29 at `https://www.biopallas.com/`, once, as a visitor.** The 5.11 17.00 row
  of Järki ja tunteet prints `Neulontanäytös`, `Stikningvisning`, `Puolivalot päällä`,
  `Halvjus på`, `Martat tarjoavat glögiä` and `Marttorna bjuder på glög` under its runtime.
  Main at 007258793 published it with an empty `method`.
- Savon Kinot publishes the same evening with `method: "Neulekino"`.
- In 18 Wayback captures from 2024-03 to 2026-07 the block also carried subtitle notes,
  `OSCAR EHDOKAS`, a registration note, `FRUKOSTBIO/ AAMUPALAELOKUVA` once and
  `F-Keks leffakerhonäytös` once. No type line repeats in the same wording.

## Inferences

- The first pair names the screening type. The other pairs describe the evening, and the
  show contract has no field for them.
- These lines are free text per event, and a pattern would publish notes as types. An exact
  list fits the evidence.

## Open questions

- `FRUKOSTBIO/ AAMUPALAELOKUVA` and `F-Keks leffakerhonäytös` are not in `KINDS`. Neither is
  on the current programme.

## Implementation status

Done 2026-10-29: `KINDS` maps both spellings to `Neulontanäytös` in `method`. Affects
`pallas-karjaa`, one row (2026-11-05 17.00).
