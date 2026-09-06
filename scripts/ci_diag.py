"""Diagnostics for a failed cloud run, written for a short-lived workflow artifact.

Temporary, disarmed by --until. Runs against the Nexxo and Regina hosts fail from some
runner addresses and pass from others, and the committed logs do not record the address.
When a run-*.log ends non-zero this probes the failing modules' hosts from the same
runner and records the runner's region and egress address, then per host the DNS answer,
HTTP status, timing, a fixed set of response headers and the body length.

Never the body: a third party's page is whatever they ship, and one probe dump once put
someone else's API key in this repo. Never the environment. The report goes to an
artifact kept two days, not to the repo.
"""
import argparse
import datetime as dt
import glob
import importlib
import os
import pathlib
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "providers"))
import registry  # noqa: E402
import run  # noqa: E402

UA = "Leffavuoro/1.0 (+https://leffavuoro.fi)"
HEADERS = ("Server", "Date", "Content-Type", "Content-Length", "CF-Ray", "CF-Cache-Status",
           "Retry-After", "Via", "X-Cache", "X-Powered-By", "Location")
IMDS = ("http://169.254.169.254/metadata/instance/compute/location"
        "?api-version=2021-02-01&format=text")
EGRESS = "https://checkip.amazonaws.com"


def failed_logs(paths, modules=None):
    """{module: [lines]} for every log whose last exit= is not 0.

    `modules` limits it to the logs this run wrote: the repo root also holds the local
    half's committed logs, and an old local failure must not start probes here. Kept lines
    are the pipeline's own `[http]` and `FAILED` lines, which name a host and a reason and
    nothing from a response body.
    """
    out = {}
    for p in sorted(paths):
        module = re.sub(r"^run-|\.log$", "", pathlib.Path(p).name)
        if modules is not None and module not in modules:
            continue
        text = pathlib.Path(p).read_text(encoding="utf-8", errors="replace")
        exits = re.findall(r"^exit=(\d+)$", text, re.M)
        if not exits or exits[-1] == "0":
            continue
        out[module] = [l for l in text.splitlines() if l.startswith("[http]") or "FAILED" in l]
    return out


def hosts_for(module, lines):
    """Hosts named by the log's `[http]` lines plus the bases of the module's cloud sites.

    Only the cloud half: etiketti also carries two local-only sites that a runner is not
    meant to read at all.
    """
    hosts = set(re.findall(r"^\[http\] \d+ from ([^,\s]+)", "\n".join(lines), re.M))
    try:
        sites = run.sites_for(importlib.import_module(module), "cloud")
    except Exception:
        sites = ()
    for s in sites:
        host = urlsplit(s.get("base") or "").netloc
        if host:
            hosts.add(host)
    return sorted(hosts)


def _get(url, timeout, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            n = len(r.read())
            return r.status, r.headers, n, int((time.monotonic() - t0) * 1000), None
    except urllib.error.HTTPError as e:
        # An HTTPError is also the response; unread or half-read it leaks a socket.
        try:
            n = len(e.read())
        except Exception:
            n = -1
        finally:
            e.close()
        return e.code, e.headers, n, int((time.monotonic() - t0) * 1000), None
    except Exception as e:  # URLError, socket.timeout, ssl errors
        return None, {}, 0, int((time.monotonic() - t0) * 1000), f"{type(e).__name__}: {e}"


def probe(url, timeout=15):
    host = urlsplit(url).hostname or url
    try:
        dns = sorted({a[4][0] for a in socket.getaddrinfo(host, None)})
    except OSError as e:
        dns = [f"dns failed: {e}"]
    status, hdrs, n, ms, err = _get(url, timeout)
    return {"url": url, "dns": dns, "status": status, "ms": ms, "body_len": n,
            "headers": {h: hdrs[h].strip() for h in HEADERS if hdrs.get(h)}, "error": err}


def _get_text(url, timeout, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(200).decode("ascii", "replace").strip() or "unknown"
    except Exception:
        return "unknown"


def runner_facts():
    return {"region": _get_text(IMDS, 3, {"Metadata": "true"}),
            "egress": _get_text(EGRESS, 5),
            "run_id": os.environ.get("GITHUB_RUN_ID", "?"),
            "event": os.environ.get("GITHUB_EVENT_NAME", "?")}


def render(failed, facts, probes):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [f"provider diagnostics {now}"]
    out += [f"{k}: {v}" for k, v in facts.items()]
    for module, lines in failed.items():
        out.append(f"\n== {module}")
        out += ["  " + l for l in lines]
    out.append("\n== probes from this runner")
    for p in probes:
        out.append(f"{p['url']}  dns={','.join(p['dns'])}")
        if p["error"]:
            out.append(f"  error after {p['ms']} ms: {p['error']}")
        else:
            out.append(f"  {p['status']} in {p['ms']} ms, body {p['body_len']} bytes")
        out += [f"  {h}: {v}" for h, v in p["headers"].items()]
    return "\n".join(out) + "\n"


def main(argv):
    """Never fails the job: the workflow also marks the step continue-on-error, and a
    diagnostics bug must not cost the schedule its publication."""
    try:
        return _main(argv)
    except Exception as e:
        print(f"[diag] failed: {type(e).__name__}: {e}")
        return 0


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="directory for diag.txt")
    ap.add_argument("--until", required=True, help="YYYY-MM-DD; after this day do nothing")
    ap.add_argument("--logs", default="run-*.log", help="glob of run logs")
    ap.add_argument("--probe", default="https://{host}/", help="URL template per host")
    ap.add_argument("--offline", action="store_true", help="skip region and egress lookups")
    a = ap.parse_args(argv)

    if dt.date.today() > dt.date.fromisoformat(a.until):
        print(f"[diag] expired {a.until}, nothing done")
        return 0
    failed = failed_logs(glob.glob(a.logs), registry.modules("cloud"))
    if not failed:
        print("[diag] every cloud log ends exit=0, no report")
        return 0
    facts = ({"region": "skipped", "egress": "skipped", "run_id": "?", "event": "?"}
             if a.offline else runner_facts())
    probes = [probe(a.probe.format(host=h))
              for m, lines in failed.items() for h in hosts_for(m, lines)]
    text = render(failed, facts, probes)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "diag.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("report=true\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
