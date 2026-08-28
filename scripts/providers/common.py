"""Shared HTTP fetch with retry for provider adapters.

Named common, not http: run.py and fetch_data.py put this directory first on
sys.path, and a local http.py would shadow the stdlib package urllib.request
itself imports (http.client), breaking every fetch in the pipeline.

One transient 502 or connection reset used to count as total site failure for
the adapters without their own retry loop, and the next cron is four hours
away. tries=3 with backoff*n sleeps means a worst case of 3*backoff seconds of
extra wait per request, so a dead upstream cannot stall the workflow.
"""
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
