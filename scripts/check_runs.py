#!/usr/bin/env python3
"""Fail if any committed run log ended badly. -> 0 clean, 1 something failed.

    python3 scripts/check_runs.py            # the repo's own logs, in logs/
    python3 scripts/check_runs.py --dir DIR

A failed cloud provider turns its Actions run red. The local half runs outside this repo,
writes `exit=1` into the provider's log, pushes it and carries on, and the first symptom
would be the health line going amber eight hours later. Both halves commit their logs, so
reading them on push is the local half's failure signal, without touching the wrapper or
the fetch workflow.

A log with no `exit=` line is a failure too: every writer appends one, so its absence
means the run died first or the file was truncated. A stale log counts: `run-vista.log`
sat at `exit=1` for hours on 2026-08-30 after the module was retired and nothing
overwrote it.

The logs moved from the repo root into `logs/` on 2026-09-15. Two things follow, and both
are here rather than in the caller. The default `--dir` is derived from this file's own
location, not from the working directory, so the documented command works from anywhere and
a caller cannot point it at an empty root by accident. And `strays()` fails on any
`run*.log` left at the repo root: the cloud half and the out-of-repo local wrapper each
write their own logs, so a writer that was not migrated would otherwise keep publishing to
the old place while this check read the moved copies and called them green. That is the one
failure this script may not have, and it is why a stray is an error rather than a warning.
"""
import argparse
import pathlib
import re
import sys

# Derived from this file, so the default is the repo's logs/ whatever the caller's cwd is.
REPO = pathlib.Path(__file__).resolve().parents[1]
LOGS = REPO / "logs"

EXIT_RE = re.compile(r"^exit=(-?\d+)\s*$", re.M)
# The line a failing adapter prints before it gives up, worth quoting so the report says
# what broke rather than only that something did.
CAUSE_RE = re.compile(r"^\[[^\]]+\] (?:FAILED|no programme published):.*$|^\[http\].*$", re.M)


def check(path):
    """-> (ok, exit_code_or_None, [cause lines]) for one log file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    causes = CAUSE_RE.findall(text)
    # The *last* one, not the first and not the final line of the file. Each writer
    # appends `exit=$?` when it finishes, so a later one supersedes an earlier one; and
    # reading the final line instead would call a log unreadable the moment anything is
    # printed after it.
    codes = EXIT_RE.findall(text)
    if not codes:
        return False, None, causes
    return int(codes[-1]) == 0, int(codes[-1]), causes


def strays(repo=REPO):
    """Run logs still sitting at the repo root. -> [Path], empty when the move is clean.

    A writer that still publishes to the old location is invisible to a check that reads
    only logs/, so it is named here and fails the run.
    """
    return sorted(repo.glob("run*.log"))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=str(LOGS), help="directory holding the run logs")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.dir)
    logs = sorted(root.glob("run*.log"))
    if not logs:
        print(f"[check] no run logs in {root}/ -- nothing has been committed yet",
              file=sys.stderr)
        return 1

    left = strays()
    if left:
        print("[check] run logs at the repo root, which nothing reads any more: "
              + ", ".join(p.name for p in left), file=sys.stderr)
        print("[check] a writer was not migrated to logs/; fix it before trusting this check",
              file=sys.stderr)
        return 1

    bad = []
    for p in logs:
        ok, code, causes = check(p)
        if not ok:
            bad.append((p.name, code, causes))

    for name, code, causes in bad:
        where = f"exit={code}" if code is not None else "no exit= line"
        print(f"[check] {name}: {where}", file=sys.stderr)
        for c in causes[:3]:
            print(f"    {c.strip()}", file=sys.stderr)

    print(f"[check] {len(logs)} run log(s), {len(bad)} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
