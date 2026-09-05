"""Event strand prefixes, and splitting them off a published title.

A cinema sells the same film under a strand: "Seniorikino: Hetki Ennen Valoa",
"Pieni elokuvakerho: Kummisetä osa II", "Vauvakino: ...". The strand belongs in `method`,
where the client renders it as a pill, and the bare film title belongs in `title`. Left
in place a strand prefix does three kinds of damage:

  * the film fragments — "Seniorikino: Hetki Ennen Valoa" never merges with the plain
    title at the same or another chain;
  * TMDB cannot match it, so no rating, poster, trailer or genre ids;
  * the poster fallback tile takes the first letters of the first two words, so every
    film in a strand renders the same initials.

**The list is exact, never a `^\\w+:` pattern.** Most colons in this data are franchise
titles, not strands: across one day's showtimes, "Spider-Man:" appears 443 times,
"Ryhmä Hau:" 272, "Insidious:" 159, against 4 for "Seniorikino:". A pattern would
decapitate all of them.

Adding a strand here fixes it everywhere at once: `enrich_tmdb.clean()` for the TMDB
search, and `run.py` / `fetch_data.py` for every provider's titles.
"""

EVENT_PREFIXES = (
    "kesäkino", "kesakino", "vauvakino", "barnsöndagar", "barnsondagar",
    "klassikko", "klassikkosarja", "elokuvakerho", "filmiklubi", "seniorikino",
    "perhekino", "lastenkino", "sunnuntaikino", "ennakkonäytös", "ennakko",
    # Added 2026-08-27 from the first Orion run's no-match list. Festival and strand
    # names, not film titles. "pitchblack playback" and "hopeacine" will still miss
    # TMDB (a music playback night has no entry), but they belong in `method`.
    "espoo ciné", "espoo cine", "pieni elokuvakerho", "pitchblack playback",
    "hopeacine",
    # A format, not a strand, but it sits in the same position and breaks the search
    # the same way: "70mm: The Odyssey" matched a Pinocchio short.
    "70mm",
    # A festival *section*, one level below the festival itself: Orion published
    # "Espoo Ciné: Artist in Focus: Mare's Nest". Two prefixes on one title, and split()
    # takes one per call, so the outer one came off in the adapter and this one stayed
    # in the title and cost the film its TMDB match. It comes off in run.py's central
    # pass, which is the second call. A provider that does not also split in its own
    # adapter would still need two passes for a title shaped like this.
    "artist in focus",
    # Kino Engel, 2026-08-29. "barnsöndagar" was already here; "barnfestival" is a
    # separate Swedish-language children's strand the first pass missed
    # (barnfestival-nord, barnfestival-skurkarnas-skurk). Note "kesäkino" is in this
    # list for enrich_tmdb.clean() only: engel.py takes it off the title itself and puts
    # it in `aud`, because the Kesäkino is Engel's outdoor screen rather than a strand,
    # so nothing is left here for the central pass to split.
    "barnfestival",
    # Korjaamo Kino, 2026-09-05. The Helsinki African Film Festival publishes its films
    # as "HelAFF: Fez Summer 55" and its short programmes as "HelAFF Short Films 1",
    # without a colon, so only the features are split. Vista already puts the festival
    # in `method` through EventSeries, and apply() does not add it twice.
    "helaff",
)


def split(title):
    """"Seniorikino: Hetki Ennen Valoa" -> ("Hetki Ennen Valoa", "Seniorikino").

    Returns the title unchanged and an empty strand when nothing in the exact list
    matches, and never strips a prefix that would leave nothing behind.
    """
    t = (title or "").strip()
    low = t.lower()
    for pre in EVENT_PREFIXES:
        if low.startswith(pre + ":"):
            rest = t[len(pre) + 1:].strip(" -–:")
            if rest:
                return rest, t[:len(pre)].strip()
    return t, ""


def apply(show):
    """Split a show's title in place, folding the strand into `method`."""
    title, strand = split(show.get("title"))
    if not strand:
        return False
    show["title"] = title
    tags = [x for x in (show.get("method") or "").split(" · ") if x]
    if strand not in tags:
        tags.insert(0, strand)
    show["method"] = " · ".join(tags)
    return True
