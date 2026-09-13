#!/usr/bin/env python3
"""A push that touches DESIGN.md or tests/test_design_contract.py carries an IDEAS.md change.

    python3 scripts/check_design_push.py BEFORE AFTER [--base origin/main] [--repo DIR]

Run by ci.yml with `github.event.before` and `github.sha`. The range is the push's own,
never the tip's parent alone: a push is not one commit, and a design change in an
earlier commit of the same push would slip past `HEAD^..HEAD`.

`before` is not always usable. After a force-push it names the tip the push replaced: a
full clone does not carry it and `git diff` fails with exit 128 (2026-09-13, run
34773073208), and when it *is* readable -- GitHub serves a rewritten SHA for a while --
`before..after` is the difference between two branches rather than the push, so it reports
the files of the commits the push dropped. A branch created by the push reports an
all-zero `before`. The range is recovered in this order:

1. `before` itself, fetched by SHA from origin when the checkout lacks it, and used only
   when it is an ancestor of `after`: that range is exactly the push;
2. otherwise the merge base of the base branch and `after`, which is every commit the
   push put on the branch that main does not have: a superset of the push, never less;
3. otherwise exit 2 and say so. A push to the base branch itself with an unreachable
   `before` has no range to recover, and guessing one would hide a contract change.

The entry has to be in the same commit as the contract change, not merely somewhere in
the range. The merge-base fallback is a superset of the push, and read as one range an
`IDEAS.md` edit in an unrelated earlier commit answers for a later contract-only commit.
Per commit it cannot, and CLAUDE.md asks for the same commit anyway. The net diff still
gates: a push that changes a contract file and takes it back has nothing to explain.

Exit 0 when the contract is untouched or the IDEAS entry is present, 1 on a violation,
2 when the range cannot be determined.
"""
import argparse
import pathlib
import subprocess
import sys

CONTRACT = ("DESIGN.md", "tests/test_design_contract.py")
ENTRY = "IDEAS.md"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)


def has_commit(repo, rev):
    return _git(repo, "cat-file", "-e", f"{rev}^{{commit}}").returncode == 0


def is_ancestor(repo, rev, tip):
    return _git(repo, "merge-base", "--is-ancestor", rev, tip).returncode == 0


def push_base(before, after, base_ref, repo, log=print):
    """The commit to diff `after` against -> sha, or None when no range can be found."""
    if before and set(before) != {"0"}:
        readable = has_commit(repo, before)
        if not readable and _git(repo, "remote", "get-url", "origin").returncode == 0:
            _git(repo, "fetch", "--quiet", "origin", before)
            readable = has_commit(repo, before)
            if readable:
                log(f"[design] before {before[:10]} fetched by sha")
        if readable:
            if is_ancestor(repo, before, after):
                return before
            # Readable but replaced: the range would carry whatever the dropped commits
            # touched, in either direction. It reports a contract change the push does not
            # make, and it accepts an IDEAS entry that only the dropped tip had.
            log(f"[design] before {before[:10]} is not an ancestor of {after[:10]} "
                f"(force-pushed branch)")
        else:
            log(f"[design] before {before[:10]} is not reachable (rewritten branch)")
    else:
        log("[design] before is all zeros (created ref)")
    mb = _git(repo, "merge-base", base_ref, after)
    if mb.returncode == 0:
        base = mb.stdout.strip()
        if base and not _git(repo, "rev-parse", "--verify", "--quiet",
                             f"{base}^{{commit}}").returncode and base != _resolve(repo, after):
            log(f"[design] comparing against merge base {base[:10]} with {base_ref}")
            return base
    return None


def _resolve(repo, rev):
    r = _git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    return r.stdout.strip() if r.returncode == 0 else None


def entryless_commits(base, after, repo):
    """Commits in base..after that change a contract file and not IDEAS.md. -> [sha]"""
    with_entry = set(_log(base, after, repo, (ENTRY,)))
    return [c for c in _log(base, after, repo, CONTRACT) if c not in with_entry]


def _log(base, after, repo, paths):
    r = _git(repo, "log", "--format=%H", f"{base}..{after}", "--", *paths)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return [line for line in r.stdout.splitlines() if line]


def changed_files(base, after, repo):
    r = _git(repo, "diff", "--name-only", base, after)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return [line for line in r.stdout.splitlines() if line]


def verdict(files, entryless=()):
    """(ok, message) for a push: the files it changed, and the commits in it that changed
    a contract file without touching IDEAS.md."""
    touched = sorted(f for f in files if f in CONTRACT)
    if not touched:
        return True, "design contract untouched"
    if entryless:
        return False, (f"{' and '.join(touched)} changed without an IDEAS.md entry in the "
                       f"same commit ({', '.join(c[:10] for c in entryless)})")
    return True, "design contract change carries an IDEAS entry"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--base", default="origin/main", help="the base branch ref (default origin/main)")
    ap.add_argument("--repo", default=str(ROOT), help="the repository to read (default: this one)")
    args = ap.parse_args(argv)
    repo = pathlib.Path(args.repo)
    base = push_base(args.before, args.after, args.base, repo)
    if base is None:
        print(f"::error::cannot determine the push range for {args.after[:10]}: "
              f"before {args.before[:10]} is unreachable and {args.base} gives no merge base")
        return 2
    ok, message = verdict(changed_files(base, args.after, repo),
                          entryless_commits(base, args.after, repo))
    if not ok:
        print(f"::error::{message}")
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
