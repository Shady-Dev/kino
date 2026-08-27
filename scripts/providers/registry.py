#!/usr/bin/env python3
"""Single source of truth for providers.

Everything provider-specific that is not parsing lives here. data/providers.json is
generated from this by scripts/build_providers.py, so the frontend carries no provider
list of its own: adding a provider is an entry here plus an adapter, with no edit to
index.html.

Fields:
  id      matches the `provider` field on every show and data/venues-{id}.json
  label   chain name, used in the venue picker, the chain legend and the footer
  host    the cinema's own domain, credited in the footer
  accent  3 px left border in combined views. Never the sole signal, see IDEAS.md
  book    buy | reserve | door | list -> footer call to action. "list" is for a
          provider that publishes no per-show booking URL, so a showtime can only
          open the programme page (Gilda: seat choice lives in React state, and the
          bundle exposes no shareable showtime route)
  module  scripts/providers/{module}.py. One module can serve several providers
          (nexxo -> kinoset, etiketti -> kotkanleffat). None = Finnkino, which has
          its own fetcher at scripts/fetch_data.py and the legacy areas.json shape
  where   local | cloud. Finnkino and Kino Akseli block datacenter IPs, so they can only
          be fetched from an ordinary connection; everything else runs on Actions
"""

PROVIDERS = [
    dict(id="finnkino", label="Finnkino", host="finnkino.fi", accent="#D85A30",
         book="buy", module=None, where="local"),
    dict(id="biorex", label="BioRex", host="biorex.fi", accent="#BA7517",
         book="buy", module="biorex", where="cloud"),
    dict(id="kinoset", label="Kinoset", host="kinoset.fi", accent="#2F7D5B",
         book="reserve", module="nexxo", where="cloud"),
    dict(id="kotkanleffat", label="Kotkan Leffat", host="kotkanleffat.fi",
         accent="#C0356B", book="buy", module="etiketti", where="cloud"),
    dict(id="riviera", label="Riviera", host="rivieracinemas.fi", accent="#7A4FA3",
         book="buy", module="riviera", where="cloud"),
    dict(id="gilda", label="Gilda", host="gilda.fi", accent="#A8433C",
         book="buy", module="gilda", where="cloud"),
    dict(id="savonkinot", label="Savon Kinot", host="savonkinot.fi", accent="#2A7B8C",
         book="buy", module="vista", where="cloud"),
    dict(id="kinoakseli", label="Kino Akseli", host="kinoakseli.fi", accent="#4A6FA5",
         book="door", module="kinoakseli", where="local"),
]

FRONTEND_KEYS = ("id", "label", "host", "accent", "book")


def frontend():
    """The subset the client needs. Nothing about where a provider runs leaks out."""
    return [{k: p[k] for k in FRONTEND_KEYS} for p in PROVIDERS]


def by_id(pid):
    return next((p for p in PROVIDERS if p["id"] == pid), None)


def modules(where=None):
    """Adapter modules to run, in order, deduplicated (one module, several providers)."""
    out = []
    for p in PROVIDERS:
        if not p["module"]:
            continue
        if where and p["where"] != where:
            continue
        if p["module"] not in out:
            out.append(p["module"])
    return out


if __name__ == "__main__":
    import sys
    if "--cloud" in sys.argv:
        print("\n".join(modules("cloud")))
    elif "--local" in sys.argv:
        print("\n".join(modules("local")))
    else:
        print("\n".join(f"{p['id']}\t{p['where']}\t{p['module'] or '-'}" for p in PROVIDERS))
