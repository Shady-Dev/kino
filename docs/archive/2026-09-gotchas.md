# Archive: notes and gotchas, to 2026-09-14

Moved out of `IDEAS.md` on 2026-09-15. Traps found the hard way, kept because each one
cost a debugging session. The ones that became rules are in
[CLAUDE.md](../../CLAUDE.md) and are not repeated here; this list is the rest.

Active and deferred work is in [IDEAS.md](../../IDEAS.md). The accepted working rules are
in [CLAUDE.md](../../CLAUDE.md), the visual contract in [DESIGN.md](../../DESIGN.md), and
the investigations these decisions rest on under [docs/research/](../research/).

---

## Notes / gotchas
- Read the committed `run.log`, not Actions logs.
- An adapter binds `EmptyProgramme` at import time and `test_common_fetch` reloads `common`
  for its counters, which rebinds that class. `reload()` puts the original class back on the
  reloaded module, because an adapter imported earlier in the run keeps the one it bound. Four
  etiketti tests went red when `test_ci_diag.py` was deleted: it had been dropping adapters
  from `sys.modules` for its own reasons and healing the order by accident.
- A break-and-restore test pass can report the state before the restore. Writing the file
  again with the same byte count inside the same mtime second makes Python reuse the
  `__pycache__` bytecode compiled from the broken source. Clear `__pycache__` between the
  break and the restore, and re-read the final green on a cleared cache.
- `raw.githubusercontent.com` served a two-commit-stale `index.html` minutes after a push,
  and using it as the base for the next edit reverted the previous fix. Read repo files
  through the Contents API with `Accept: application/vnd.github.raw`.
- Splitting the removal of one block across two edits leaves everything between them
  behind; that produced valid syntax referencing a deleted variable and the app died at
  runtime. Delete a block as one contiguous match.
- Anything the language toggle can reach must be redrawn by `applyLang()`.
- Actions run 32985593686 (2026-08-26) failed with "The job was not acquired by Runner":
  GitHub-side runner allocation, nothing to fix.
- Triggering `workflow_dispatch` via the API needs the token's Actions permission; the
  Workflows permission covers editing workflow files only.
- Probing endpoints the sandbox cannot reach: push a throwaway workflow that curls and
  commits the response, read it, delete both. Does not work for sites that block datacenter
  IPs.
- BeautifulSoup re-serialises attributes with single quotes; never write regexes against
  bs4's rendering of a page.
- `workflow_dispatch` runs the workflow file at the ref, but a run already queued uses the
  older file. Check `head_sha` when a change seems not to apply.
- Two writers on one branch (local + Actions), so both push paths need the pull-rebase
  retry.
- The cloud workflow is cron + dispatch only. It used to trigger on pushes to
  `scripts/providers/**`, so an adapter commit spawned a run that raced a manual dispatch.
- A retry loop whose last command is `sleep` exits 0 even when every attempt failed. Set an
  explicit flag and `exit 1`.
- Small hosts rate-limit: Kinoset answered 403 after repeated hits in one hour.
- Every frontend bug on the day multi-provider landed came from a field only Finnkino
  populated: `soldOut`, `s.fi`, and a hash regex `m=([\w-]+)` that truncated ids with
  spaces. Check field-presence assumptions in the client as well as the parser.
- `location.hash = ''` counts as navigating to the top of the document and scrolled the
  list up when the sheet closed. Use `history.replaceState`.
- A helper that raises before the file write, followed by a push, commits the file
  unchanged. Write the file before pushing and check the edit count.
- The Contents API commits one path per call; for a multi-file commit use the Git trees
  API (`git/trees` with `base_tree`, `git/commits`, `PATCH git/refs/heads/main`).
- Pushing through the API means the local clone learns nothing until it pulls. To identify
  the clone that publishes, read the author of the commits touching its data.
- The local wrapper's shell mechanics are in private notes. One general lesson: a final step
  that runs after the push can fail without making the run look failed, so anything that
  matters needs its own check.
- An unmapped language code renders as itself (2026-08-29): `LN` held five languages and
  the data carried twelve, so 133 Spanish showtimes said "ES". A real language code missing
  from `LN` is a client gap; a code that is not a language (SE for Sweden) is an adapter
  bug. `LN` carries every code in the data plus everything the adapters' name maps can emit.
- The Swedish tag is `SV`, migrated from `SE` on 2026-08-29 (SV is the ISO 639-1 language
  code, SE the country). Done in three commits: the client learned both codes, then the
  six adapters that publish Swedish, then `fetch_data.py`; the temporary alias came out
  once no area file carried `SE-`. The shape of a data-format migration with no build step
  and two writers: teach the reader both, change the writers, remove the old spelling once
  the data has turned over, gated on a measurement.
- BioRex published `SV` where the client's map keyed on `SE`, so 644 showtimes said
  "tekstit SV". Normalised at the source; the tag set is Finnkino's, and a provider's own
  spelling is not evidence of anything.
- Adapters carry a referer, three retries with backoff, and a pause between venues.
- The film-list sort (`localeCompare` per comparison) measured identical to a cached
  `Intl.Collator`, about 0.01 ms per 45-title sort. Not worth touching.
