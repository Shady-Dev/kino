"""Shared HTTP fetch with retry for provider adapters.

Named common, not http: run.py and fetch_data.py put this directory first on
sys.path, and a local http.py would shadow the stdlib package urllib.request
itself imports (http.client), breaking every fetch in the pipeline.

One transient 502 or connection reset used to count as total site failure for
the adapters without their own retry loop, and the next cron is four hours
away. tries=3 with backoff*n sleeps means a worst case of 3*backoff seconds of
extra wait per request, so a dead upstream cannot stall the workflow.
"""
import json
import os
import time
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def fetch(url, headers=None, data=None, tries=3, backoff=5, timeout=30, opener=None):
    """GET (or POST when `data` is given) with retry. -> bytes.

    `opener` lets a cookie-session adapter (BioRex) retry a single request
    without redoing the whole session dance. Retries every exception the same
    way the per-adapter get() loops already do; an HTTP 4xx is rare enough
    here that distinguishing it is not worth the branch.
    """
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, data=data,
                                         headers=headers or {"user-agent": UA})
            op = opener.open if opener is not None else urllib.request.urlopen
            with op(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            if n + 1 < tries:
                time.sleep(backoff * (n + 1))
    raise last


def write_text_atomic(path, text):
    """Write via a sibling .tmp then os.replace, atomic on the same filesystem.

    On Actions a torn write is harmless (ephemeral runner), but localfetch.sh
    writes into the checked-out repo, so a run killed mid-write -- closed
    laptop, cancel-in-progress -- would leave truncated JSON that the next
    run's `git add data` commits. .tmp is gitignored for the same reason.
    """
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path, obj, **dumps_kw):
    write_text_atomic(path, json.dumps(obj, ensure_ascii=False, **dumps_kw))
