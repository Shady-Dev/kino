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
          colourblind vision, and only there: four cities have more than one chain in
          them (measured after the eTiketti sweep, 2026-08-30) -- Helsinki with six,
          Vantaa, Lahti and Kouvola with two each. Everywhere else a chain is alone in
          its town and its accent is unconstrained, which is what makes 25 chains
          survivable at all. Hues therefore repeat across cities on purpose.
          Run `python3 scripts/accent_check.py` before changing one: it prints every
          same-city pair in CIEDE2000 under two deuteranope models, and
          `--search {id}` proposes a replacement. Do not eyeball it, and do not trust
          a number that no longer has a script behind it -- the figures that used to
          sit here were CIE76 mislabelled as ΔE, and were wrong by a factor of five.
          Current worst same-city pair: 14.4 ΔE00 deutan (Finnkino/Cinema Orion).
          That is where hand-picking landed, not a ceiling: a search over the same L*
          band reaches 19.5, and IDEAS says why it has not been applied. Where a city
          has only two chains and both are free, take the best pair going -- Kouvola
          sits at 73.5 for that reason
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
    # Moved off Vista on 2026-08-30: the /xml/ services 404 from every network and the
    # site now runs eTiketti. Accent, host and venue ids are unchanged on purpose -- the
    # ids key the saved home cinema and the /teatteri/ URLs.
    dict(id="savonkinot", label="Savon Kinot", host="savonkinot.fi", accent="#0C8FA8",
         book="buy", module="etiketti", where="cloud"),
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

    # The eTiketti sweep of 2026-08-30. Fourteen hosts, sixteen venues, all against the
    # parser that already served Kotka and Kokkola. Only three of them land in a city
    # that already had a chain, and those three accents are the only ones the 3 px rule
    # constrains -- see IDEAS. Every one publishes a per-show booking link, so `buy`.
    dict(id="kinopirtti", label="Kinopirtti", host="kinopirtti.fi", accent="#8E44AD",
         book="buy", module="etiketti", where="cloud"),
    dict(id="leffabuumi", label="Leffabuumi", host="leffabuumi.fi", accent="#1F7A8C",
         book="buy", module="etiketti", where="cloud"),
    dict(id="studio123jarvenpaa", label="Studio 123 Järvenpää", host="studiot123.com",
         accent="#B0308F", book="buy", module="etiketti", where="cloud"),
    # Kouvola is the one town this sweep puts two of its own chains in, so these two
    # accents are measured against each other and against nothing else -- and because
    # *both* are free, the pair is taken at the maximum the L* band allows rather than
    # merely far enough apart: 73.5 dE00 deutan, against the 35.2 they launched with.
    # Blue against orange is where that maximum lives, so both sit near an accent used
    # in another city (Kino Aurora's indigo, Finnkino's orange). Neither chain appears
    # outside Kouvola and the accent renders only inside a combined city view, so the
    # two are never on screen together.
    dict(id="studio123kouvola", label="Studio 123 Kouvola", host="studio123.fi",
         accent="#2040F0", book="buy", module="etiketti", where="cloud"),
    dict(id="kino123", label="Kino 123", host="kino123.fi", accent="#E07000",
         book="buy", module="etiketti", where="cloud"),
    dict(id="ihmekompleksi", label="Ihme Kompleksi", host="ihmekompleksi.fi",
         accent="#7A5CD0", book="buy", module="etiketti", where="cloud"),
    dict(id="kinotar", label="Kinotar 123", host="jamsankinotar.fi", accent="#2E7D5B",
         book="buy", module="etiketti", where="cloud"),
    dict(id="kinojuha", label="Kino Juha", host="kinojuha.fi", accent="#A6431F",
         book="buy", module="etiketti", where="cloud"),
    # Vantaa already has Finnkino Flamingo, so this one is measured against Finnkino's
    # orange. Green is what it must not be: 13.6 dE00 under the harsher deutan model.
    dict(id="biogrand", label="Bio Grand", host="biogrand.fi", accent="#7B4FB5",
         book="buy", module="etiketti", where="cloud"),
    dict(id="biovuoksi", label="Bio Vuoksi", host="biovuoksi.fi", accent="#3E6FA8",
         book="buy", module="etiketti", where="cloud"),
    # Lahti already has Finnkino Kuvapalatsi. Same constraint, same measurement.
    dict(id="kinoiiris", label="Kino Iiris", host="kinoiiris.com", accent="#2F6FD0",
         book="buy", module="etiketti", where="cloud"),
    # The only eTiketti site on the local half: its host 403s a datacenter IP the way
    # Finnkino and Engel do. It shares the etiketti module with fourteen cloud sites,
    # which is what site-level routing in run.py exists for.
    dict(id="joutsankino", label="Joutsan Kino", host="kino.joutsa.fi", accent="#96702A",
         book="buy", module="etiketti", where="local"),
    dict(id="kkino", label="K-Kino", host="k-kino.fi", accent="#4C6B1F",
         book="buy", module="etiketti", where="cloud"),
    dict(id="biograni", label="Bio Grani", host="biograni.fi", accent="#B03A55",
         book="buy", module="etiketti", where="cloud"),

    # The Nexxo sweep of 2026-08-30. Six cinemas on five hosts, against the adapter that
    # already served Kinoset. Only Kino Aurora lands in a city that already had a chain.
    # `book="reserve"` throughout: Nexxo publishes no per-show booking URL, so a showtime
    # opens the programme page filtered to that location, the same as Kinoset.
    #
    # Jyväskylä already has Finnkino Fantasia. Orange was the intuitive pick for a cinema
    # called Aurora and measures 4.7 dE00 against Finnkino's: indigo instead, at 63.7.
    dict(id="kinoaurora", label="Kino Aurora", host="kinoaurora.fi", accent="#5B4FD0",
         book="reserve", module="nexxo", where="cloud"),
    # Both read from kinohirvi.fi, which serves two cinemas in two towns on locationids
    # 2 and 4. Bio Säde's own domain, biosade.fi, answers with an empty programme, so the
    # host credited here is the one actually read.
    dict(id="kinohirvi", label="Kino Hirvi", host="kinohirvi.fi", accent="#0F7B9C",
         book="reserve", module="nexxo", where="cloud"),
    dict(id="biosade", label="Bio Säde", host="kinohirvi.fi", accent="#8C3B7A",
         book="reserve", module="nexxo", where="cloud"),
    dict(id="kinomarilyn", label="Kino Marilyn", host="kinomarilyn.fi", accent="#1A6E4A",
         book="reserve", module="nexxo", where="cloud"),
    dict(id="kinoolympia", label="Kino Olympia", host="kino-olympia.fi", accent="#9C5518",
         book="reserve", module="nexxo", where="cloud"),
    dict(id="jarvelankino", label="Järvelän Kino", host="jarvelankino.fi", accent="#7A6A1E",
         book="reserve", module="nexxo", where="cloud"),
    # KSEK's touring cinema, read from kinoaurora.fi (one deployment with ksek.fi);
    # the host credited is the one actually read, as with Bio Säde. Accent measured
    # 2026-08-31 against Muurame, Petäjävesi and Jyväskylä: worst same-city deutan
    # pair 26.9 dE00 (vs Finnkino and Kino Aurora in Jyväskylä), L* 46.9.
    dict(id="kinometso", label="Kino Metso", host="kinoaurora.fi", accent="#227D63",
         book="reserve", module="nexxo", where="cloud"),
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
