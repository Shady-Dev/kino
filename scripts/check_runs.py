#!/usr/bin/env python3
"""Fail if any committed run log ended badly. -> 0 clean, 1 something failed.

    python3 scripts/check_runs.py            # the repo's own logs
    python3 scripts/check_runs.py --dir DIR

The cloud half already announces its own failures: a provider that exits non-zero turns
the Actions run red and somebody sees it. That is how both of 2026-08-30's outages were
caught -- Joutsan Kino's 403 and Savon Kinot's 404 off Vista.

The local half has no such thing. It runs on a machine outside this repo, records
`exit=1` in the provider's log, pushes it, and carries on. Nothing is red anywhere, and
the first symptom is the health line going amber eight hours later -- if anyone is
looking at the site. Twenty of seventy venues ride on that half, seventeen of them
Finnkino, so "no signal" covers the largest provider in the app.

The commit is the transport. Both halves push their logs here, so reading them on push
gives the local half the signal the cloud half gets for free, without touching the
wrapper (which lives outside this repo and cannot be tested from inside it) or the
workflow that fetches (which has an unmerged branch against it).

A log with no `exit=` line at all is a failure too: every writer appends one, so its
absence means the run died before it could, or the file was truncated.

A stale log counts. `run-vista.log` sat at `exit=1` for hours on 2026-08-30 because the
module had been retired and nothing overwrote it -- exactly the state this is meant to
be loud about, and it was found by hand.
"""
import argparse
import pathlib
import re
import sys

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


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=".", help="directory holding the run logs")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.dir)
    logs = sorted(root.glob("run*.log"))
    if not logs:
        print(f"[check] no run logs in {root}/ -- nothing has been committed yet",
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
