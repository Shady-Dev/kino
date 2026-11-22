"""Every pattern a pipeline module carries finishes in at most quadratic time on hostile input.

The review of 2026-11-22 found one exponential and about fifty cubic patterns in the
adapters (H1, M1). `re` holds the GIL for a whole match, so one such pattern on a crafted
page froze every site in the cloud pool. `test_regex_backtracking.py` pins the ones fixed
then. This file covers the ones not written yet: it reads every module under
`scripts/providers/` and `scripts/fetch_data.py`, so a new adapter is scanned without being
listed anywhere.

What is scanned: every compiled pattern at module level, every string literal passed to a
`re` function, and a module-level `*_RE` string template, filled in. What is thrown at each:
inputs built from the pattern's own parse tree, the literal text before each unbounded
repeat followed by that repeat's body, by whitespace, or by the opener repeated with no
closer. A pattern fails when doubling one input from SMALL to SIZE characters multiplies the
time more than GROWTH-fold, which a quadratic pattern (about 4) does not reach and a cubic
one (about 8) does, or when one call runs past HANG_S. The quadratic family, `<x class="y">(.*?)</x>`
with no closer, is accepted, as the review recorded.

Each module is checked in a child process, so a pattern that never returns costs a timeout
rather than the suite; the child prints the pattern it starts, and the timeout names it.
"""
import ast
import importlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

import _ctx                                                # noqa: F401

try:
    import re._constants as C
    import re._parser as P
except ImportError:                              # Python before 3.11
    import sre_constants as C
    import sre_parse as P

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = sorted((ROOT / "scripts" / "providers").glob("*.py")) + [ROOT / "scripts" / "fetch_data.py"]
SIZE = 8000
SMALL = SIZE // 2
FAST_S = 0.002        # under this at SMALL characters an input is skipped as linear enough
FLOOR_S = 0.01        # under this at SIZE growth is noise
GROWTH = 5.5          # time at SIZE over time at SMALL: about 4 quadratic, 8 cubic
HANG_S = 3.0          # one call; past this it is reported without waiting for it
CHILD_TIMEOUT_S = 120
# "file:name or line": the reason it may stay. Empty: every pattern passes today.
EXCEPTIONS = {}

FUNCS = {"compile", "search", "match", "fullmatch", "findall", "finditer", "sub", "subn", "split"}
CANDS = "a1 Z_<>/\"'=.-:,;\n\t\x00é!#&?(){}[]"


def _in(items, ch):
    neg = ok = False
    for op, av in items:
        if op is C.NEGATE:
            neg = True
        elif op is C.LITERAL:
            ok |= ord(ch) == av
        elif op is C.RANGE:
            ok |= av[0] <= ord(ch) <= av[1]
        elif op is C.CATEGORY:
            cls = {"DIGIT": r"\d", "SPACE": r"\s", "WORD": r"\w"}.get(str(av).split("_")[-1], r"\w")
            ok |= bool(re.match(cls, ch)) != ("NOT" in str(av))
    return ok != neg


def sample(seq):
    """The shortest text each node of a parsed pattern accepts, roughly."""
    out = []
    for op, av in seq:
        if op is C.LITERAL:
            out.append(chr(av))
        elif op is C.NOT_LITERAL:
            out.append("a" if av != ord("a") else "b")
        elif op is C.ANY:
            out.append("a")
        elif op is C.IN:
            out.append(next((ch for ch in CANDS if _in(av, ch)), "a"))
        elif op is C.BRANCH:
            out.append(sample(av[1][0]))
        elif op is C.SUBPATTERN:
            out.append(sample(av[-1]))
        elif op in (C.MAX_REPEAT, C.MIN_REPEAT) or str(op) == "POSSESSIVE_REPEAT":
            mn, _, sub = av
            out.append(sample(sub) * max(mn, 1))
        elif str(op) == "ATOMIC_GROUP":
            out.append(sample(av))
    return "".join(out)


def attacks(pattern, flags):
    """-> [(kind, prefix, pump)] for every unbounded repeat in the pattern."""
    try:
        tree = P.parse(pattern, flags)
    except Exception:
        return []
    found = []

    def walk(seq, prefix):
        items = list(seq)
        for i, (op, av) in enumerate(items):
            pre = prefix + sample(items[:i])
            if op in (C.MAX_REPEAT, C.MIN_REPEAT) or str(op) == "POSSESSIVE_REPEAT":
                _, mx, sub = av
                if mx is C.MAXREPEAT or mx > 50:
                    body = sample(sub) or "a"
                    found.extend([("pump", pre, body), ("pump", pre, " "), ("rep", pre + body, "")])
                walk(sub, pre)
            elif op is C.SUBPATTERN:
                walk(av[-1], pre)
            elif op is C.BRANCH:
                for b in av[1]:
                    walk(b, pre)
            elif str(op) == "ATOMIC_GROUP":
                walk(av, pre)
    walk(tree, "")
    found += [("pump", "", " "), ("pump", "", "a"), ("pump", "", "1")]
    return [a for a in dict.fromkeys(found) if a[1] or a[2]]


def build(kind, pre, pump, n):
    if kind == "pump":
        return pre + pump * max(1, (n - len(pre)) // len(pump)) + "\x00"
    return pre * max(1, n // max(1, len(pre))) + "\x00"


class _Hang(Exception):
    pass


def _alarm(*_):
    raise _Hang()


def timed(rx, text):
    """Seconds for a full scan, or None past HANG_S where the interpreter can interrupt it."""
    if hasattr(signal, "setitimer"):
        signal.setitimer(signal.ITIMER_REAL, HANG_S)
    t = time.perf_counter()
    try:
        rx.findall(text)
        return time.perf_counter() - t
    except _Hang:
        return None
    finally:
        if hasattr(signal, "setitimer"):
            signal.setitimer(signal.ITIMER_REAL, 0)


def best(rx, text, n):
    """The fastest of `n` timings, None if one hangs: one slow sample is the machine."""
    got = []
    for _ in range(n):
        t = timed(rx, text)
        if t is None:
            return None
        got.append(t)
    return min(got)


def grows(rx, small_text, big_text, n):
    small = best(rx, small_text, n)
    big = best(rx, big_text, n) if small is not None else None
    if small is None or big is None:
        return "over the hang limit"
    if small >= FAST_S and big > FLOOR_S and big > GROWTH * small:
        return f"{big:.3f} s at {SIZE}, {small:.4f} s at {SMALL}"
    return None


def verdict(rx):
    """-> None, or why the pattern fails."""
    tried = set()
    for kind, pre, pump in attacks(rx.pattern, rx.flags):
        small_text, big_text = build(kind, pre, pump, SMALL), build(kind, pre, pump, SIZE)
        if small_text in tried:
            continue
        tried.add(small_text)
        if grows(rx, small_text, big_text, 1) and (why := grows(rx, small_text, big_text, 3)):
            return f"{kind} {pre[:30]!r} + {pump[:10]!r}: {why}"
    return None


def patterns(path):
    """-> [(label, compiled)] that one module carries."""
    found = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in FUNCS
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "re" and n.args):
            try:
                pat = ast.literal_eval(n.args[0])
            except Exception:
                continue
            if not isinstance(pat, str):
                continue
            fexpr = next((kw.value for kw in n.keywords if kw.arg == "flags"), None)
            pos = {"compile": 1, "sub": 4, "subn": 4}.get(n.func.attr, 2)
            if fexpr is None and len(n.args) > pos:
                fexpr = n.args[pos]
            flags = 0
            if fexpr is not None:
                try:
                    flags = eval(compile(ast.Expression(fexpr), "<flags>", "eval"), {"re": re})
                except Exception:
                    flags = 0
            try:
                found.append((f"{path.name}:{n.lineno}", re.compile(pat, flags)))
            except (re.error, TypeError):
                pass
    sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts" / "providers")]
    mod = importlib.import_module(path.stem)
    for name, value in vars(mod).items():
        if isinstance(value, re.Pattern):
            found.append((f"{path.name}:{name}", value))
        elif name.endswith("_RE") and isinstance(value, str) and "%s" in value:
            found.append((f"{path.name}:{name}", re.compile(value % "x", re.S | re.I)))
    seen, out = set(), []
    for label, rx in found:
        if (rx.pattern, rx.flags) not in seen:
            seen.add((rx.pattern, rx.flags))
            out.append((label, rx))
    return out


def child(paths):
    if hasattr(signal, "setitimer"):
        signal.signal(signal.SIGALRM, _alarm)
    for p in paths:
        for label, rx in patterns(pathlib.Path(p)):
            print(json.dumps({"start": label}), flush=True)
            why = verdict(rx)
            if why:
                print(json.dumps({"fail": label, "why": why}), flush=True)
    print(json.dumps({"done": True}), flush=True)


def check(path):
    """-> [(label, why)] for one module, run in its own interpreter."""
    try:
        r = subprocess.run([sys.executable, __file__, "--child", str(path)], capture_output=True,
                           text=True, timeout=CHILD_TIMEOUT_S, cwd=ROOT)
        out, err, code = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err, code = f"no answer in {CHILD_TIMEOUT_S} s", None
    lines = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    fails = [(l["fail"], l["why"]) for l in lines if "fail" in l]
    if not any("done" in l for l in lines):
        last = next((l["start"] for l in reversed(lines) if "start" in l), path.name)
        fails.append((last, f"the check did not finish (exit {code}): {err.strip()[-300:]}"))
    return fails


class RegexSafetyTest(unittest.TestCase):
    def test_every_module_is_scanned(self):
        import registry
        scanned = {p.stem for p in SOURCES}
        self.assertLessEqual(set(registry.modules()), scanned)

    def test_the_exceptions_name_patterns_that_still_exist_with_a_reason(self):
        for label, reason in EXCEPTIONS.items():
            self.assertTrue(reason.strip(), label)

    def test_no_pattern_backtracks_worse_than_quadratically(self):
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
            results = list(pool.map(check, SOURCES))
        fails = [(label, why) for r in results for label, why in r if label not in EXCEPTIONS]
        self.assertEqual(fails, [], "\n".join(f"{l}: {w}" for l, w in fails))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--child"]:
        child(sys.argv[2:])
    else:
        unittest.main()
