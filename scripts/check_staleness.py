#!/usr/bin/env python3
"""Fail if the published data has stopped being refreshed.

-> 0 fresh, 1 stale or unreadable, 2 the invocation itself was wrong.

    python3 scripts/check_staleness.py                  # data/areas.json
    python3 scripts/check_staleness.py --file PATH
    python3 scripts/check_staleness.py --hours N

`check_runs.py` answers "did the last run fail". It does not answer "did a run happen",
and those are different questions: a committed log reading `exit=0` four days ago passes
it happily. Every failure this repo can see announces itself through a run that ran. A
run that never starts -- the laptop asleep, launchd unloaded, the wrapper edited into
silence -- announces nothing at all, and the first symptom is the health line going amber
for whoever happens to be looking at the site.

`data/areas.json` is the file to watch. It is written by the local half, which carries 17
of 74 venues and the largest chain in the app, and since 2026-09-01 it is written *with*
the schedule files rather than before them -- so its age now means "when did a complete
Finnkino publish last happen" rather than "when did a run last get as far as asking for
the site list". Watching it before that change would have measured the wrong thing.

**This script is only the verdict.** When to run it, where to read the file from, and who
to tell live in `kino-auth`, outside this repo -- a schedule and an endpoint are
machine-specific and this repo is public. Everything here is a pure function of a file and
a clock, which is why it can be tested.

Eight hours, because that is `STALE_H` in index.html and the health line already uses it:
a monitor that fired at a different age than the banner would be reporting a second,
invisible definition of stale. Strictly greater, for the same reason -- the client reads
`ageH > STALE_H`, so exactly eight hours is not yet late.

The verdict goes to stdout and every failure to stderr, which is a split the caller can
use -- `2>&1 >/dev/null` keeps the complaints and drops the routine line. It is not
silence by itself: cron mails whatever a job writes to either stream, so staying quiet on
a good run is the wrapper's decision to discard stdout, not something this script can
arrange on its own.

A timestamp in the future fails rather than reading as very fresh. The writer stamps
`datetime.now(timezone.utc)` and the reader is a different machine, so a couple of minutes
of drift is ordinary and tolerated; past that, one of the two clocks is wrong and the age
cannot be trusted. It is the dangerous direction as well: a badly future timestamp keeps
the file looking fresh for as long as the skew lasts, which is exactly the silence this
exists to break.
"""
import argparse
import datetime
import json
import math
import pathlib
import sys

DEFAULT_FILE = pathlib.Path("data/areas.json")
# Keep in step with STALE_H in index.html. The banner and this must not disagree about
# what "stale" means.
MAX_AGE_H = 8.0
# Ordinary clock drift between the machine that wrote the file and the one reading it.
FUTURE_SKEW_S = 300


class Unreadable(Exception):
    """The file cannot answer the question. Not the same as answering "old"."""


def validate_limit(hours):
    """-> the limit as a float. Raises ValueError if it could not be meant.

    `inf` and `nan` both make every comparison below false, so the check passes for ever:
    a monitor that cannot fail, which is worse than no monitor because it looks like one.
    `nan` is the quieter of the two -- it does not even read as suspicious in a log line.
    A negative limit is a typo, not an instruction that everything is stale, and
    reporting it as stale data would send someone looking at the pipeline. Zero is
    allowed and useful: it asks "was this written in the last instant", which is how the
    tests exercise the stale branch without waiting.
    """
    h = float(hours)
    if not math.isfinite(h):
        raise ValueError(f"limit must be a finite number of hours, not {hours!r} -- "
                         "a check that can never fail is not a check")
    if h < 0:
        raise ValueError(f"limit must not be negative, and {hours!r} is")
    return h


def read_generated(path):
    """-> the aware datetime in `generated`. Raises Unreadable with the reason."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Unreadable("no such file")
    except OSError as e:
        raise Unreadable(f"cannot read: {e}")

    try:
        doc = json.loads(raw)
    except ValueError as e:
        raise Unreadable(f"not JSON: {e}")
    if not isinstance(doc, dict):
        raise Unreadable(f"JSON is {type(doc).__name__}, expected an object")

    stamp = doc.get("generated")
    if stamp is None:
        raise Unreadable("no `generated` field")
    if not isinstance(stamp, str) or not stamp.strip():
        raise Unreadable(f"`generated` is {type(stamp).__name__}, expected a timestamp")

    try:
        when = datetime.datetime.fromisoformat(stamp.strip())
    except ValueError:
        raise Unreadable(f"`generated` is not an ISO 8601 timestamp: {stamp!r}")
    # A naive timestamp would be read in whatever zone the monitor happens to sit in,
    # which is three hours of error here and a silently different answer elsewhere.
    if when.tzinfo is None or when.utcoffset() is None:
        raise Unreadable(f"`generated` carries no UTC offset: {stamp!r}")
    return when


def check(path, max_age_h=MAX_AGE_H, now=None):
    """-> (ok, message).

    Nothing wrong with the *file* raises. Missing, unparseable, undated, dated in the
    future: each is a verdict with the reason in the message, because "I could not read
    it" is something a monitor has to report rather than crash on.

    A limit that could not have been meant does raise ValueError. That is the caller's
    bug and not a fact about the data, and returning it as a verdict would dress a typo
    up as an outage. See validate_limit.
    """
    max_age_h = validate_limit(max_age_h)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        when = read_generated(path)
    except Unreadable as e:
        return False, f"{path}: {e}"

    ahead = (when - now).total_seconds()
    if ahead > FUTURE_SKEW_S:
        return False, (f"{path}: generated {when.isoformat()}, "
                       f"{ahead / 3600:.1f} h in the future -- a clock is wrong, "
                       f"so the age cannot be trusted")

    age_h = max(0.0, -ahead / 3600)
    where = (f"{path}: generated {when.isoformat()}, "
             f"{age_h:.1f} h old, limit {max_age_h:g} h")
    if age_h > max_age_h:
        return False, f"{where} -- STALE, no run has published since"
    return True, f"{where} -- fresh"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", default=str(DEFAULT_FILE),
                    help="file to read (default: data/areas.json)")
    ap.add_argument("--hours", type=float, default=MAX_AGE_H,
                    help=f"age that counts as stale (default: {MAX_AGE_H:g}, "
                         "which is STALE_H in index.html)")
    args = ap.parse_args(argv)
    try:
        hours = validate_limit(args.hours)
    except ValueError as e:
        # argparse's own exit code, because this is a wrong invocation and not a verdict
        # about the data. A caller that cannot tell those apart would treat its own typo
        # as a pipeline outage.
        ap.error(str(e))
        return 2

    ok, message = check(pathlib.Path(args.file), hours)
    print(f"[stale] {message}", file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
