#!/usr/bin/env python3
"""Single source of truth for providers.

Everything provider-specific that is not parsing lives here. data/providers.json is
generated from this by scripts/build_providers.py, so the frontend carries no provider
list of its own: adding a provider is an entry here plus an adapter.

Fields:
  id      matches the `provider` field on every show and data/venues-{id}.json
  label   chain name, used in the venue picker, the chain legend and the footer
  host    the cinema's own domain, credited in the footer
  accent  3 px left border in combined views. Never the sole signal, see IDEAS.md.
          Chains that share a city must be far apart in normal and in red-green
          colourblind vision; elsewhere the accent is unconstrained, so hues repeat
          across cities on purpose. Six cities have more than one chain (measured
          2026-09-05): Helsinki with eight, Jyväskylä with three, Vantaa, Lahti, Kouvola
          and Tampere with two each. Run `python3 scripts/accent_check.py` before
          changing one: it prints every same-city pair in CIEDE2000 under two
          deuteranope models, and `--search {id}` proposes a replacement. Do not quote a
          figure no script produced; the numbers that used to sit here were CIE76
          mislabelled as ΔE. Current worst same-city pair: 14.4 ΔE00 deutan
          (Finnkino/Cinema Orion); Jyväskylä's worst is 26.9 (Finnkino/Kino Metso).
          A search over the same L* band reaches 19.5; IDEAS says why it is not applied.
  book    buy | reserve | door | list | admission -> footer call to action. "list" is
          for a provider with no per-show booking URL, so a showtime opens the programme
          page (Gilda). "admission" is for a venue whose screenings are included in a
          general admission ticket (Heureka): the showtime links to the ticket shop and
          the price compartment stays blank
  module  scripts/providers/{module}.py. One module can serve several providers
          (nexxo -> kinoset, etiketti -> kotkanleffat). None = Finnkino, which has
          its own fetcher at scripts/fetch_data.py and the legacy areas.json shape
  where   local | cloud. Finnkino, Kino Engel, Kino Akseli, Joutsan Kino, Savon
          Kinot and Kino Regina block or challenge datacenter IPs, so they can only be
          fetched from an ordinary connection; everything else runs on Actions
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
    # Local since 2026-09-04: savonkinot.fi sits behind Cloudflare, which answers a
    # datacenter address 403 at the edge (CF-Ray present, no Retry-After) while the same
    # request from an ordinary connection gets 200. See IDEAS "Savon Kinot moves to the
    # local half".
    dict(id="savonkinot", label="Savon Kinot", host="savonkinot.fi", accent="#0C8FA8",
         book="buy", module="etiketti", where="local"),
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
    # Finnkino and Engel do. It shares the etiketti module with sixteen cloud sites,
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
    # host credited here is the one read.
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
    # the host credited is the one read, as with Bio Säde. Accent measured
    # 2026-08-31 against Muurame, Petäjävesi and Jyväskylä: worst same-city deutan
    # pair 26.9 dE00 (vs Finnkino and Kino Aurora in Jyväskylä), L* 46.9.
    dict(id="kinometso", label="Kino Metso", host="kinoaurora.fi", accent="#227D63",
         book="reserve", module="nexxo", where="cloud"),
    # Cinema Niagara, Tampere (2026-09-02): the eTiketti host the sweep left behind,
    # because its screenings render in a second template that etiketti.py now reads.
    # Tampere becomes the sixth two-chain city, so the accent is measured against
    # Finnkino's orange: #6A4FBF is 47.0 / 68.1 / 60.6 dE00 (normal / Viénot / Machado),
    # greens failed the deutan columns at 17-19, and no other chain uses this hex. The
    # cinema sells per-show tickets on its own /salikartta page, so `buy`. `where` is
    # provisional until a cloud run has succeeded: cinemaniagara.fi answered an ordinary
    # connection with no challenge and no Cloudflare header, which is how the other
    # cloud eTiketti hosts look, and one field flips it if a runner is refused.
    dict(id="niagara", label="Cinema Niagara", host="cinemaniagara.fi", accent="#6A4FBF",
         book="buy", module="etiketti", where="cloud"),
    # Heurekan planetaario, Vantaa (2026-09-05). Screenings are included in the day
    # admission and there is no planetarium ticket, so `admission`. Vantaa already holds
    # Finnkino and Bio Grand: #0B8468 measures 26.5 / 26.0 dE00 (Viénot / Machado) from
    # Finnkino's orange and 30.3 / 27.9 from Bio Grand's violet, L* 49.0; Heureka's own
    # lime green scores 6.9 against the orange. `where` is provisional as Niagara's was:
    # 200 from an ordinary connection and from a non-residential fetcher, Cloudflare in
    # front, no challenge. The first cloud run decides.
    dict(id="heureka", label="Heureka", host="heureka.fi", accent="#0B8468",
         book="admission", module="heureka", where="cloud"),
    # Korjaamo Kino, Helsinki (2026-09-05): the Vista module's first site since Savon
    # Kinot left it. korjaamokino.fi answers the public /xml/ services to anyone, a
    # non-residential fetcher included, so `cloud`. Per-show ticket links to
    # /websales/show/{id}, so `buy`. Helsinki has six chains already, so the accent is
    # the search's best: #C07E7E measures 19.7 / 18.5 / 17.7 dE00 (normal / Viénot /
    # Machado) from Finnkino's orange and 21.3 / 20.1 / 17.9 from Gilda's magenta, its
    # two nearest; the other four sit above 23. L* 59.6, the top of the search band:
    # every darker rose tried (L* 49 to 55) fell to 13.8 to 14.4 deutan against Gilda.
    # Helsinki's worst pair stays Finnkino/Cinema Orion at 14.4.
    dict(id="korjaamo", label="Korjaamo Kino", host="korjaamokino.fi", accent="#C07E7E",
         book="buy", module="vista", where="cloud"),
    # Kino Tapiola, Espoo (2026-09-05): its own WordPress theme renders the programme
    # server-side, Johku sells the tickets through client-side embeds, so a showtime
    # opens the film page and `buy` is the verb. `where` is provisional as Korjaamo's
    # was: 200 from an ordinary connection and from a non-residential fetcher, nginx in
    # front, no challenge header; the first cloud run decides. Espoo holds Finnkino
    # Sello and Omena and nothing else, so the accent is measured against one orange
    # and the search's best is taken, as Kouvola's pair was: #003CFC is 52.7 / 80.4 /
    # 71.6 dE00 (normal / Viénot / Machado) from Finnkino, L* 38.3, the same blue band
    # as Studio 123 Kouvola, which never shares a screen with it.
    dict(id="tapiola", label="Kino Tapiola", host="kinotapiola.fi", accent="#003CFC",
         book="buy", module="tapiola", where="cloud"),
    # Kino Regina, Helsinki (2026-09-05): KAVI's cinema at Oodi. The theme's own POST
    # endpoint renders the schedule, each row with its ticket link into kauppa.kavi.fi,
    # so `buy`. `cloud` was read from a runner before the adapter was written, and two
    # of the first day's three runs published; the third got SiteGround's reputation
    # challenge, the 202 shell that keeps Kino Engel local, and now fails the venue
    # instead of emptying it. A repeat in the logs moves this entry to `local`.
    # Helsinki has seven chains already, so the accent is the search's best:
    # #8A4854 measures 18.4 / 19.9 / 18.4 dE00 (normal / Viénot / Machado) from Gilda's
    # magenta, 47.8 / 18.4 / 16.3 from Riviera's teal and 50.7 / 16.9 / 16.3 from Cinema
    # Orion's green, its three nearest; the other four sit above 20. L* 39.0. An eighth
    # chain in one city leaves only muted tones this far from everything; the greens the
    # search ranked higher on deutan fell to 12.5 to 14.1 in normal vision. Helsinki's
    # worst pair stays Finnkino/Cinema Orion at 14.4.
    dict(id="regina", label="Kino Regina", host="kinoregina.fi", accent="#8A4854",
         book="buy", module="regina", where="local"),
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
