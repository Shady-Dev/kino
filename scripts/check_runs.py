#!/usr/bin/env python3
"""Fail if any committed run log ended badly. -> 0 clean, 1 something failed.

    python3 scripts/check_runs.py            # the repo's own logs
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
