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
  accent  3 px left border in combined views. Never the sole signal, see IDEAS.md.
          Chains that share a city have to be far apart in *both* normal and red-green
          colourblind vision. Helsinki is the only city with more than one chain in it
          (measured, 2026-08-30), so it is the only place this rule binds.
          Run `python3 scripts/accent_check.py` before changing one: it prints every
          same-city pair in CIEDE2000 under two deuteranope models, and
          `--search {id}` proposes a replacement. Do not eyeball it, and do not trust
          a number that no longer has a script behind it -- the figures that used to
          sit here were CIE76 mislabelled as ΔE, and were wrong by a factor of five.
          Current worst same-city pair: 14.4 ΔE00 deutan (Finnkino/Cinema Orion),
          which is about the ceiling for six chains in one city
  book    buy | reserve | door | list -> footer call to action. "list" is for a
          provider that publishes no per-show booking URL, so a showtime can only
          open the programme page (Gilda: seat choice lives in React state, and the
          bundle exposes no shareable showtime route)
  module  scripts/providers/{module}.py. One module can serve several providers
          (nexxo -> kinoset, etiketti -> kotkanleffat). None = Finnkino, which has
          its own fetcher at scripts/fetch_data.py and the legacy areas.json shape
  where   local | cloud. Finnkino, Kino Engel and Kino Akseli block datacenter IPs, so
          they can only be fetched from an ordinary connection; everything else runs on
          Actions
"""

PROVIDERS = [
    dict(id="finnkino", label="Finnkino", host="finnkino.fi", accent="#E4551F",
         book="buy", module=None, where="local"),
    dict(id="biorex", label="BioRex", host="biorex.fi", accent="#1273D4",
         book="buy", module="biorex", where="cloud"),
    dict(id="kinoset", label="Kinoset", host="kinoset.fi", accent="#0E9B63",
         book="reserve", module="nexxo", where="cloud"),
    dict(id="kotkanleffat", label="Kotkan Leffat", host="kotkanleffat.fi",
         accent="#C42749", book="buy", module="etiketti", where="cloud"),
    # Teal, not the violet it launched with. Violet and BioRex's blue differ almost
    # entirely in the red-green channel a deuteranope does not have -- 3.9 dE00 apart,
    # in the one city where the two appear side by side. Riviera moved rather than
    # BioRex because both its venues are in Helsinki, so its accent only ever matters
    # there, while BioRex's blue is unconstrained in eleven other towns.
    dict(id="riviera", label="Riviera", host="rivieracinemas.fi", accent="#0C6464",
         book="buy", module="riviera", where="cloud"),
    dict(id="gilda", label="Gilda", host="gilda.fi", accent="#D62D8F",
         book="buy", module="gilda", where="cloud"),
    dict(id="savonkinot", label="Savon Kinot", host="savonkinot.fi", accent="#0C8FA8",
         book="buy", module="vista", where="cloud"),
    dict(id="orion", label="Cinema Orion", host="cinemaorion.fi", accent="#4E7A16",
         book="buy", module="orion", where="cloud"),
    dict(id="engel", label="Kino Engel", host="kinoengel.fi", accent="#B47ACC",
         book="buy", module="engel", where="local"),
    # Not the BioRex chain above: an independent cinema in Kokkola that shares the
    # name, on biorex.org rather than biorex.fi. Same trap as Gilda's Bio Rex
    # Lasipalatsi, so the label spells the city out and the accent sits far from
    # BioRex blue instead of near it.
    dict(id="biorexkokkola", label="Bio Rex Kokkola", host="biorex.org", accent="#006655",
         book="buy", module="etiketti", where="cloud"),
    dict(id="kinoakseli", label="Kino Akseli", host="kinoakseli.fi", accent="#B8801A",
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
