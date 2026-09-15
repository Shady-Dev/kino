"""Kino Kilta and Kino Laika: the policy, the two templates, and the overrides.

The fixtures are the markup as read on 2026-09-15, reduced to the smallest shape that
still exercises each rule. Two screenings minimum everywhere there is a loop or an index.

What the fixtures exist to prove, each one a rule that reads plausible and is wrong:

- **A runtime and an age classification are not film evidence.** Laika's billed live acts
  carry both: *Arppa* reads "130 min K-18" with no director and no genre. A classifier
  that counted either would publish every gig in Karkkila.
- **A word is never the classifier.** A film whose synopsis says konsertti publishes, and
  a concert film publishes; only the absence of a labelled director or genre withholds.
- **An override decides before the classifier**, in both directions. The exclude direction
  exists precisely because the default can include wrongly, so the redundancy guard must
  not reject an override whose page already classifies as a film.
- **A sold-out row keeps its screening.** Every sold-out row on the live listing that day
  was a live act, so only a fixture can show a sold-out *film* surviving.
"""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest

import _ctx                                                # noqa: F401
import common
import kinola as K
import registry
import run

KILTA = next(s for s in K.SITES if s["provider"] == "kinokilta")
LAIKA = next(s for s in K.SITES if s["provider"] == "kinolaika")


# ---------------------------------------------------------------- listing fixtures

def kilta_row(slug, title, date="TI 15.9.2026", time="20:00", subtitle="Kahvikino",
              dur="106 min", checkout="ee317571-a29e-4a11-bdc0-61dadd74822f",
              sold=False):
    ticket = (f'<div class="wp-block-button"><span '
              f'class="kinola-event-tickets-link-sold-out">Loppuunmyyty</span></div>'
              if sold else
              f'<div class="wp-block-button"><a class="kinola-event-tickets-link '
              f'wp-block-button__link" href="https://www.kinokilta.fi/checkout/{checkout}">'
              f'Osta lippu</a></div>')
    return (f'<li class="kinola-event"><div class="movie-info"><div class="time">{time}</div>'
            f'<div class="date-movie"><div class="date">{date}</div>'
            f'<h3><a class="kinola-event-title" '
            f'href="https://www.kinokilta.fi/film/{slug}/">{title}</a></h3>'
            f'<div class="movie-subtitle">{subtitle}</div></div>'
            f'<div class="duration-info">{dur}</div></div>{ticket}</li>')


def laika_row(slug, title, date="16/09/2026 14:00", sold=False,
              checkout="a5e4ff5b-d55b-4c84-bafe-aba007a971fb", poster=True):
    img = (f'<img src="https://media.kinola.ee/storage/laika.kinola.ee/2569/{slug}'
           f'_poster.jpg?width=1000" class="kinola-event-poster"/>' if poster else "")
    ticket = ('<p><span class="kinola-event-tickets-link-sold-out">Loppuunmyyty</span></p>'
              if sold else
              f'<p><a class="kinola-event-tickets-link" '
              f'href="https://www.kinolaika.fi/checkout/{checkout}">Osta lippu</a></p>')
    return (f'<div class="kinola-event" style="padding: 10px 20px;">{img}'
            f'<div class="kinola-event-details"><p>'
            f'<a class="kinola-event-title" href="https://www.kinolaika.fi/film/{slug}/">'
            f'<strong>{title}</strong></a><br>'
            f'<span class="kinola-event-venue">Kino Laika</span><br>'
            f'<span class="kinola-event-date">{date}</span></p>{ticket}</div></div>')


def kilta_row_sold_out_anchor(slug, title):
    """The defensive shape: the sold-out class on the anchor rather than on a span. Not
    observed on either site, which is why only a fixture reaches the guard that refuses to
    publish a checkout href from such a row."""
    return (f'<li class="kinola-event"><div class="movie-info"><div class="time">18:00</div>'
            f'<div class="date-movie"><div class="date">TI 15.9.2026</div>'
            f'<h3><a class="kinola-event-title" '
            f'href="https://www.kinokilta.fi/film/{slug}/">{title}</a></h3>'
            f'<div class="movie-subtitle"></div></div>'
            f'<div class="duration-info">90 min</div></div>'
            f'<div class="wp-block-button"><a class="kinola-event-tickets-link '
            f'kinola-event-tickets-link-sold-out" '
            f'href="https://www.kinokilta.fi/checkout/dead">Loppuunmyyty</a></div></li>')


def listing(*rows):
    return ('<html><body><div class="kinola-filters"><select '
            'class="js-kinola-film-filter kinola-film-filter"><option value="all">'
            'Kaikki elokuvat</option></select></div>'
            '<div class="kinola-events">' + "".join(rows) + "</div></body></html>")


# ---------------------------------------------------------------- film-page fixtures

def kilta_film(director="Klaus Härö", genre="Draama", lang="suomi", subs="englanti",
               dur="87 min", rating="K-12", syn=None, year="2026"):
    """Kilta's <dl class='info'> shape, with the rating in an alt attribute."""
    syn = syn or ("Erikoissairaanhoitaja Inka kohtaa vastasyntyneen vanhemmat keskellä "
                  "hoitoalan kriisiä, ja kahden naisen tiet risteytyvät sairaalassa "
                  "tavalla jota kumpikaan ei osannut odottaa etukäteen lainkaan.")
    rows = [("Valmistumisvuosi", year), ("Maat", "Suomi, Liettua")]
    if director:
        rows.append(("Ohjaaja", director))
    if genre:
        rows.append(("Lajityyppi", genre))
    rows += [("Kieli", lang), ("Tekstitys", subs), ("Kesto", dur)]
    info = "".join(f"<div class='info-wrapper'><dt>{k}</dt><dd>{v}</dd></div>"
                   for k, v in rows)
    # The file name disagrees with the alt on purpose: the site serves age-7.svg beside a
    # K-12 alt, so a parser reading the file name publishes the wrong limit.
    badge = (f"<ul class='badges'><li><img data-src='/assets/images/age-7.svg' "
             f"alt='Ikäraja: {rating}' /></li></ul>" if rating else "")
    return (f"<html><head><meta property='og:image' "
            f"content='https://media.kinola.ee/storage/kilta.kinola.ee/1086/poster.jpg'>"
            f"</head><body><main><h1>Elokuva</h1>{badge}"
            f"<dl class='info'>{info}</dl><p>{syn}</p></main></body></html>")


def laika_film(director="Klaus Härö", lang="suomi", subs="", head="87 min <br><br> K-7",
               syn=None):
    """Laika's loose `<strong>Label</strong> <br> value` shape, with the runtime and the
    classification as bare text above the first paragraph."""
    syn = syn or ("Klaus Härön uutuuselokuva kertoo kahden naisen kohtaamisesta keskellä "
                  "hoitoalan kriisiä ja siitä mitä siitä seuraa heille molemmille.")
    parts = [f"<strong>Hetki ennen valoa</strong> <br> Suomi, Liettua <br> {head} <br><br>"]
    if director:
        parts.append(f"<strong>Ohjaus</strong> <br> {director} <br><br>")
    if lang:
        parts.append(f"<strong>Kieli</strong> <br> {lang} <br><br>")
    if subs:
        parts.append(f"<strong>Tekstitys</strong> <br> {subs} <br><br>")
    return ("<html><body><div class='film'>" + "".join(parts) +
            f"<p>{syn}</p></div></body></html>")


LIVE_ACT = laika_film(director="", lang="", head="130 min <br><br> K-18",
                      syn=("Arppa - Akustisesti saleissa. Arppa lähtee syksyllä "
                           "konserttisalikiertueelle ennen keväälle ajoittuvaa "
                           "keikkataukoaan, ja lavalla kuullaan tuotantoa kaikilta "
                           "levyiltä."))
SPARSE_FILM = laika_film(director="", lang="", head="76 min <br><br> K-16",
                         syn=("Esitettävänä elokuvana on Mehrdad Oskouen "
                              "dokumenttielokuva A Fox Under A Pink Moon, joka kertoo "
                              "nuoresta afganistanilaisesta kuvanveistäjästä."))
CONCERT_FILM = kilta_film(director="Various", genre="Dokumentti, Musiikki",
                          syn=("Oasis palaa valkokankaalle: konserttielokuva bändin "
                               "vuoden 1996 Knebworth-keikoista ja siitä mitä niiden "
                               "ympärillä tapahtui kaikkien näiden vuosien jälkeen."))
# Conflicting metadata: a page that fills the runtime field and nothing else. A runtime
# is not film evidence, and the labelled shape is the only place a classifier could
# mistake it for some, since Laika writes its runtimes as bare text.
LABELLED_RUNTIME_ONLY = kilta_film(director="", genre="", lang="", subs="",
                                   dur="130 min", rating="K-18",
                                   syn=("Arppa yhtyeineen nousee lavalle akustisella "
                                        "kokoonpanolla, ja illan aikana kuullaan "
                                        "tuotantoa kaikilta levyiltä."))
# A Laika page whose header states no classification, with a decoy inside the synopsis.
RATING_ONLY_IN_THE_SYNOPSIS = laika_film(
    head="87 min", syn=("Elokuva esitettiin aikoinaan K-12 ikärajalla ja se on sittemmin "
                        "luokiteltu uudelleen, mistä kertoo tämä pitkä kuvausteksti."))
SYNOPSIS_MENTIONS_CONCERT = kilta_film(
    director="Klaus Härö", genre="Draama",
    syn=("Elokuvan käännekohta on konsertti jossa päähenkilöt kohtaavat, ja siitä "
         "kasvaa tarina kahdesta ihmisestä joiden tiet eivät enää eroa toisistaan."))


# ---------------------------------------------------------------- the templates

class BlocksTest(unittest.TestCase):
    def test_the_class_token_is_matched_exactly_not_as_a_prefix(self):
        """Every block contains `kinola-event-title`, `-date`, `-venue` and
        `-tickets-link`. A substring match would cut each block at its own children."""
        page = listing(laika_row("a", "A"), laika_row("b", "B"))
        self.assertEqual(len(K.blocks(page)), 2)
        page = listing(kilta_row("a", "A"), kilta_row("b", "B"))
        self.assertEqual(len(K.blocks(page)), 2)

    def test_a_listing_with_no_event_block_yields_none(self):
        self.assertEqual(K.blocks(listing()), [])


class KiltaListingTest(unittest.TestCase):
    def setUp(self):
        self.rows = K.events_kilta(listing(
            kilta_row("teenage-sex", "Teenage Sex and Death at Camp Miasma",
                      subtitle="Anniskelunäytös K18", dur="106 min"),
            kilta_row("hetki", "Hetki ennen valoa", date="KE 16.9.2026", time="12:30",
                      subtitle="Kahvikino - Leffa&Lounas", dur="87 min")), KILTA)

    def test_both_rows_are_read(self):
        self.assertEqual([r["slug"] for r in self.rows], ["teenage-sex", "hetki"])

    def test_the_date_carries_its_own_year_so_nothing_is_inferred(self):
        self.assertEqual(self.rows[0]["start"], "2026-09-15T20:00:00+03:00")
        self.assertEqual(self.rows[1]["start"], "2026-09-16T12:30:00+03:00")

    def test_a_winter_date_takes_the_winter_offset(self):
        rows = K.events_kilta(listing(kilta_row("x", "X", date="TI 1.12.2026",
                                                time="18:30")), KILTA)
        self.assertEqual(rows[0]["start"], "2026-12-01T18:30:00+02:00")

    def test_the_movie_subtitle_is_the_strand_and_goes_to_method(self):
        self.assertEqual(self.rows[0]["method"], "Anniskelunäytös K18")
        self.assertEqual(self.rows[1]["method"], "Kahvikino - Leffa&Lounas")

    def test_the_duration_comes_from_the_row(self):
        self.assertEqual([r["len"] for r in self.rows], ["106", "87"])

    def test_the_destination_is_the_checkout_anchor_the_row_emits(self):
        self.assertTrue(self.rows[0]["url"].startswith(
            "https://www.kinokilta.fi/checkout/"), self.rows[0]["url"])
        self.assertFalse(self.rows[0]["soldOut"])

    def test_a_row_with_an_unparseable_date_is_skipped_not_fatal(self):
        rows = K.events_kilta(listing(kilta_row("a", "A", date="TI 31.2.2026"),
                                      kilta_row("b", "B")), KILTA)
        self.assertEqual([r["slug"] for r in rows], ["b"])


class LaikaListingTest(unittest.TestCase):
    def setUp(self):
        self.rows = K.events_laika(listing(
            laika_row("hetki", "Hetki ennen valoa"),
            laika_row("arppa", "Arppa", date="30/10/2026 19:00", sold=True)), LAIKA)

    def test_both_rows_are_read_and_the_date_format_differs_from_kilta(self):
        self.assertEqual([r["slug"] for r in self.rows], ["hetki", "arppa"])
        self.assertEqual(self.rows[0]["start"], "2026-09-16T14:00:00+03:00")
        self.assertEqual(self.rows[1]["start"], "2026-10-30T19:00:00+02:00")

    def test_a_sold_out_row_has_no_anchor_and_falls_back_to_the_film_page(self):
        r = self.rows[1]
        self.assertTrue(r["soldOut"])
        self.assertEqual(r["url"], "https://www.kinolaika.fi/film/arppa/")
        self.assertNotIn("/checkout/", r["url"])

    def test_a_sold_out_marker_on_the_anchor_also_refuses_that_href(self):
        """Defensive: the sold-out class sits on a span on both sites today, so nothing
        live reaches this branch. If the markup ever moves it onto the anchor, the href
        beside it is a dead checkout and must not be published."""
        rows = K.events_kilta(listing(kilta_row_sold_out_anchor("x", "X")), KILTA)
        self.assertIs(rows[0]["soldOut"], True)
        self.assertEqual(rows[0]["url"], "https://www.kinokilta.fi/film/x/")
        self.assertNotIn("/checkout/", rows[0]["url"])

    def test_a_row_on_sale_keeps_its_checkout_link(self):
        self.assertIn("/checkout/", self.rows[0]["url"])
        self.assertFalse(self.rows[0]["soldOut"])

    def test_the_poster_comes_from_the_listing_row(self):
        self.assertTrue(self.rows[0]["img"].startswith("https://media.kinola.ee/"))

    def test_a_row_with_no_poster_publishes_no_image_from_the_listing(self):
        rows = K.events_laika(listing(laika_row("a", "A", poster=False)), LAIKA)
        self.assertEqual(rows[0]["img"], "")


# ---------------------------------------------------------------- the classifier

class LabelsTest(unittest.TestCase):
    def test_kiltas_dt_dd_pairs_are_read(self):
        f = K.labels(kilta_film())
        self.assertEqual(f["ohjaaja"], "Klaus Härö")
        self.assertEqual(f["lajityyppi"], "Draama")
        self.assertEqual(f["kesto"], "87 min")

    def test_laikas_strong_pairs_are_read_by_the_same_reader(self):
        """The classifier must not have to know which site it is reading."""
        f = K.labels(laika_film())
        self.assertEqual(f["ohjaus"], "Klaus Härö")
        self.assertEqual(f["kieli"], "suomi")

    def test_a_page_with_no_labels_reads_empty(self):
        self.assertEqual(K.labels("<html><body><p>Arppa</p></body></html>"), {})


class ClassifyTest(unittest.TestCase):
    def one(self, page):
        return K.classify("kinolaika", "s", K.film_facts(page), {})

    def test_a_labelled_director_is_film_evidence(self):
        self.assertEqual(self.one(laika_film(director="Klaus Härö")), (True, "film"))

    def test_a_labelled_genre_is_film_evidence(self):
        self.assertEqual(self.one(kilta_film(director="", genre="Draama")),
                         (True, "film"))

    def test_a_runtime_and_a_classification_are_not_film_evidence(self):
        """The trap the policy was corrected for. Arppa is 130 min and K-18 with no
        director: counted as evidence, every gig in Karkkila would publish."""
        facts = K.film_facts(LIVE_ACT)
        self.assertEqual(facts["len"], "130")
        self.assertEqual(facts["rating"], "K-18")
        self.assertEqual(K.classify("kinolaika", "arppa", facts, {}),
                         (False, "unresolved"))

    def test_a_film_whose_page_fills_no_field_is_unresolved_not_a_non_film(self):
        self.assertEqual(self.one(SPARSE_FILM), (False, "unresolved"))

    def test_a_labelled_runtime_on_its_own_is_still_not_film_evidence(self):
        """Conflicting metadata, and the shape a classifier could most easily get wrong:
        the runtime in a real `<dt>Kesto</dt>` field with no director and no genre beside
        it. Laika writes its runtimes as bare text, so only this fixture reaches the
        case."""
        facts = K.film_facts(LABELLED_RUNTIME_ONLY)
        self.assertEqual(facts["labels"].get("kesto"), "130 min")
        self.assertEqual(facts["rating"], "K-18")
        self.assertEqual(K.classify("kinokilta", "x", facts, {}), (False, "unresolved"))

    def test_a_concert_film_publishes(self):
        self.assertEqual(self.one(CONCERT_FILM), (True, "film"))

    def test_a_synopsis_mentioning_a_concert_does_not_withhold_the_film(self):
        self.assertEqual(self.one(SYNOPSIS_MENTIONS_CONCERT), (True, "film"))

    def test_the_word_konsertti_in_a_live_acts_page_is_not_what_withholds_it(self):
        """Proof that no keyword is doing the work: strip every mention and the verdict
        is unchanged, because the absence of a labelled field is the whole rule."""
        page = LIVE_ACT.replace("konserttisalikiertueelle", "kiertueelle")
        self.assertEqual(self.one(page), (False, "unresolved"))


class FilmFactsTest(unittest.TestCase):
    def test_kiltas_rating_comes_from_the_alt_and_not_the_file_name(self):
        """The site serves age-7.svg beside a K-12 alt."""
        page = kilta_film(rating="K-12")
        self.assertIn("age-7.svg", page)
        self.assertEqual(K.film_facts(page)["rating"], "K-12")

    def test_sallittu_kaikille_is_s(self):
        self.assertEqual(K.film_facts(kilta_film(rating="sallittu kaikille"))["rating"],
                         "S")

    def test_a_page_with_no_classification_publishes_no_rating(self):
        """Blank is filled by the shared classification pass from another chain."""
        self.assertEqual(K.film_facts(kilta_film(rating=""))["rating"], "")

    def test_laikas_rating_is_read_from_the_header_and_not_from_the_synopsis(self):
        """A K-12 inside a blurb is not this film's own limit. The header states no
        classification at all here, so an unbounded search would publish the decoy: a
        fixture whose header also carries a rating proves nothing, because the header's
        value comes first either way."""
        f = K.film_facts(RATING_ONLY_IN_THE_SYNOPSIS)
        self.assertIn("K-12", RATING_ONLY_IN_THE_SYNOPSIS)
        self.assertEqual(f["rating"], "")
        self.assertEqual(f["len"], "87")

    def test_the_header_region_stops_at_the_first_paragraph(self):
        self.assertNotIn("K-12", K._head(RATING_ONLY_IN_THE_SYNOPSIS))
        self.assertIn("87 min", K._head(RATING_ONLY_IN_THE_SYNOPSIS))

    def test_a_header_rating_is_still_read_when_there_is_one(self):
        self.assertEqual(K.film_facts(laika_film(head="87 min <br><br> K-7"))["rating"],
                         "K-7")

    def test_the_language_tags_come_from_the_finnish_names(self):
        f = K.film_facts(kilta_film(lang="suomi", subs="englanti"))
        self.assertEqual(f["lang"], "FI-A, EN-S")

    def test_two_subtitle_languages_split_on_the_conjunction(self):
        f = K.film_facts(kilta_film(lang="englanti", subs="suomi ja ruotsi"))
        self.assertEqual(f["lang"], "EN-A, FI-S, SV-S")

    def test_the_tables_are_shared_with_the_other_reader_of_this_vocabulary(self):
        import gilda
        self.assertIs(K.LANG, gilda.LANG)

    def test_the_genre_is_published_and_the_synopsis_is_the_long_paragraph(self):
        f = K.film_facts(kilta_film(genre="Draama"))
        self.assertEqual(f["genres"], "Draama")
        self.assertGreater(len(f["syn"]), 120)


# ---------------------------------------------------------------- overrides

class OverrideTest(unittest.TestCase):
    def facts(self, page):
        return K.film_facts(page)

    def test_an_include_override_publishes_a_film_the_classifier_leaves_unresolved(self):
        o = {("kinolaika", "fox"): {"action": "include"}}
        self.assertEqual(K.classify("kinolaika", "fox", self.facts(SPARSE_FILM), o),
                         (True, "override:include"))

    def test_an_exclude_override_withholds_an_event_the_classifier_would_publish(self):
        """The direction the proposed guard would have forbidden: an override is needed
        precisely because the default includes wrongly."""
        o = {("kinokilta", "gig"): {"action": "exclude"}}
        self.assertEqual(K.classify("kinokilta", "gig", self.facts(kilta_film()), o),
                         (False, "override:exclude"))

    def test_the_override_is_consulted_before_the_classifier(self):
        """Both directions disagree with the default, so neither verdict can come from
        the classifier having run first."""
        o = {("kinolaika", "a"): {"action": "include"},
             ("kinolaika", "b"): {"action": "exclude"}}
        self.assertTrue(K.classify("kinolaika", "a", self.facts(LIVE_ACT), o)[0])
        self.assertFalse(K.classify("kinolaika", "b", self.facts(kilta_film()), o)[0])

    def test_an_override_is_scoped_to_its_provider(self):
        o = {("kinolaika", "fox"): {"action": "include"}}
        self.assertFalse(K.classify("kinokilta", "fox", self.facts(SPARSE_FILM), o)[0])

    def test_an_unknown_action_is_not_loaded(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"overrides": [
                {"provider": "kinolaika", "slug": "a", "action": "maybe"},
                {"provider": "kinolaika", "slug": "b", "action": "include"}]}, fh)
        self.addCleanup(lambda: pathlib.Path(fh.name).unlink())
        self.assertEqual(sorted(K.load_overrides(fh.name)),
                         [("kinolaika", "b")])

    def test_a_missing_file_is_no_overrides_rather_than_an_error(self):
        self.assertEqual(K.load_overrides("/nonexistent/kinola-overrides.json"), {})


class ShippedOverridesTest(unittest.TestCase):
    """The committed file, held to the shape the policy requires."""

    def setUp(self):
        self.doc = json.loads(K.OVERRIDE_FILE.read_text(encoding="utf-8"))

    def test_every_entry_carries_its_action_reason_evidence_and_verification_date(self):
        for row in self.doc["overrides"]:
            with self.subTest(slug=row.get("slug")):
                for key in ("provider", "slug", "action", "reason", "evidence",
                            "verified"):
                    self.assertTrue(str(row.get(key, "")).strip(), key)
                self.assertIn(row["action"], ("include", "exclude"))
                self.assertRegex(row["verified"], r"^\d{4}-\d{2}-\d{2}$")

    def test_every_entry_names_a_provider_this_module_serves(self):
        served = {s["provider"] for s in K.SITES}
        for row in self.doc["overrides"]:
            self.assertIn(row["provider"], served)

    def test_no_entry_is_a_title_keyword(self):
        """Scoped to the site's own /film/{slug}/ identifier. A keyword would put the
        classification rule the policy forbids back in through the override file."""
        for row in self.doc["overrides"]:
            self.assertRegex(row["slug"], r"^[a-z0-9][a-z0-9-]*$")
            self.assertNotIn(" ", row["slug"])

    def test_the_fox_entry_is_the_recorded_inclusion_candidate(self):
        entry = next(r for r in self.doc["overrides"]
                     if r["slug"] == "a-fox-under-a-pink-moon")
        self.assertEqual((entry["provider"], entry["action"]),
                         ("kinolaika", "include"))
        self.assertIn("dokumenttielokuva", entry["evidence"])


class RedundantOverrideTest(unittest.TestCase):
    """The guard the policy asks for: an override that does not change the default.

    Aimed at the decision and not at the page. An `include` whose page already classifies
    as a film is redundant; an `exclude` whose page classifies as a film is **not**, which
    is the case the first version of this guard would have rejected.
    """

    @staticmethod
    def redundant(action, publishes_by_default):
        return (action == "include" and publishes_by_default) or \
               (action == "exclude" and not publishes_by_default)

    def test_an_include_for_a_page_that_already_classifies_is_redundant(self):
        self.assertTrue(self.redundant("include", True))

    def test_an_exclude_for_a_page_that_classifies_is_not_redundant(self):
        self.assertFalse(self.redundant("exclude", True))

    def test_an_include_for_an_unresolved_page_is_not_redundant(self):
        self.assertFalse(self.redundant("include", False))

    def test_an_exclude_for_an_unresolved_page_is_redundant(self):
        self.assertTrue(self.redundant("exclude", False))

    def test_the_shipped_entry_changes_the_default_decision(self):
        """Measured against the fixture that stands in for its page: no labelled field,
        so the classifier leaves it unresolved and the include is doing work."""
        default = K.classify("kinolaika", "a-fox-under-a-pink-moon",
                             K.film_facts(SPARSE_FILM), {})[0]
        self.assertFalse(default)
        self.assertFalse(self.redundant("include", default))


# ---------------------------------------------------------------- parse and omissions

class ParseTest(unittest.TestCase):
    def run_parse(self, overrides=None):
        page = listing(
            laika_row("hetki", "Hetki ennen valoa"),
            laika_row("hetki", "Hetki ennen valoa", date="17/09/2026 16:00"),
            laika_row("fox", "A Fox Under a Pink Moon", date="24/09/2026 18:00"),
            laika_row("arppa", "Arppa", date="30/10/2026 19:00", sold=True),
            laika_row("arppa", "Arppa", date="31/10/2026 19:00"),
            laika_row("oasis", "Oasis: Don't Look Back in Anger",
                      date="18/09/2026 20:00", sold=True))
        pages = {"hetki": laika_film(), "fox": SPARSE_FILM, "arppa": LIVE_ACT,
                 "oasis": CONCERT_FILM}
        return K.parse(LAIKA, page, pages,
                       {("kinolaika", "fox"): {"action": "include"}}
                       if overrides is None else overrides)

    def test_films_publish_and_the_live_act_does_not(self):
        per, om = self.run_parse()
        titles = sorted({s["title"] for s in per["laika-karkkila"]})
        self.assertEqual(titles, ["A Fox Under a Pink Moon", "Hetki ennen valoa",
                                  "Oasis: Don't Look Back in Anger"])
        self.assertNotIn("Arppa", titles)

    def test_a_sold_out_film_is_preserved_with_the_film_page_as_its_destination(self):
        """No sold-out film was on the live listing that day; only a fixture shows it."""
        per, _ = self.run_parse()
        oasis = [s for s in per["laika-karkkila"] if s["title"].startswith("Oasis")]
        self.assertEqual(len(oasis), 1)
        self.assertIs(oasis[0]["soldOut"], True)
        self.assertEqual(oasis[0]["url"], "https://www.kinolaika.fi/film/oasis/")

    def test_the_omission_count_is_unique_films_and_screenings_split_by_reason(self):
        _, om = self.run_parse()
        self.assertEqual(om["unresolved_films"], {"Arppa"})
        self.assertEqual(om["unresolved_shows"], 2)
        self.assertEqual(om["excluded_films"], set())
        self.assertEqual(om["excluded_shows"], 0)

    def test_a_force_exclude_is_counted_apart_from_an_unresolved_entry(self):
        _, om = self.run_parse({("kinolaika", "oasis"): {"action": "exclude"}})
        self.assertEqual(om["excluded_films"], {"Oasis: Don't Look Back in Anger"})
        self.assertEqual(om["excluded_shows"], 1)
        self.assertEqual(om["unresolved_films"], {"Arppa", "A Fox Under a Pink Moon"})
        self.assertEqual(om["unresolved_shows"], 3)

    def test_the_same_film_at_the_same_minute_twice_is_one_row(self):
        """The listing has repeated a row before; the screening is the film and the
        minute, not the block."""
        row = laika_row("hetki", "Hetki ennen valoa")
        per, _ = K.parse(LAIKA, listing(row, row), {"hetki": laika_film()})
        self.assertEqual(len(per["laika-karkkila"]), 1)

    def test_two_screenings_of_one_film_are_two_rows(self):
        per, _ = self.run_parse()
        hetki = [s for s in per["laika-karkkila"] if s["title"] == "Hetki ennen valoa"]
        self.assertEqual(len(hetki), 2)
        self.assertEqual(sorted(s["start"][:10] for s in hetki),
                         ["2026-09-16", "2026-09-17"])

    def test_rows_are_sorted_by_start(self):
        per, _ = self.run_parse()
        starts = [s["start"] for s in per["laika-karkkila"]]
        self.assertEqual(starts, sorted(starts))

    def test_every_show_meets_the_contract(self):
        per, _ = self.run_parse()
        common.check_shows(per, "kinolaika", {"laika-karkkila"})

    def test_a_kilta_parse_carries_the_row_duration_and_the_page_metadata(self):
        page = listing(kilta_row("hetki", "Hetki ennen valoa"),
                       kilta_row("oasis", "Oasis", date="KE 16.9.2026", time="19:00"))
        per, om = K.parse(KILTA, page, {"hetki": kilta_film(), "oasis": CONCERT_FILM})
        rows = per["kilta-turku"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["len"], "106")          # the row, not the page's 87
        self.assertEqual(rows[0]["rating"], "K-12")
        self.assertEqual(rows[0]["genres"], "Draama")
        self.assertEqual(rows[0]["method"], "Kahvikino")
        self.assertEqual(om["unresolved_shows"], 0)
        common.check_shows(per, "kinokilta", {"kilta-turku"})


# ---------------------------------------------------------------- the runner

class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._out = run.OUT
        run.OUT = pathlib.Path(self.tmp.name)
        self.addCleanup(lambda: setattr(run, "OUT", self._out))
        self._fetch, self._sleep = K.fetch, K.time.sleep
        self.addCleanup(lambda: setattr(K, "fetch", self._fetch))
        self.addCleanup(lambda: setattr(K.time, "sleep", self._sleep))
        K.time.sleep = lambda s: None
        self.calls = []

    def serve(self, pages):
        def fetch(url, **kw):
            self.calls.append(url)
            body = pages.get(url)
            if isinstance(body, Exception):
                raise body
            if body is None:
                raise RuntimeError(f"unexpected fetch {url}")
            return body.encode("utf-8")
        K.fetch = fetch

    def main(self, which="kinola"):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main([which])
        return code, out.getvalue() + err.getvalue()

    def both(self, **over):
        pages = {
            "https://www.kinokilta.fi/naytokset/": listing(
                kilta_row("hetki", "Hetki ennen valoa"),
                kilta_row("oasis", "Oasis", date="KE 16.9.2026", time="19:00")),
            "https://www.kinokilta.fi/film/hetki/": kilta_film(),
            "https://www.kinokilta.fi/film/oasis/": CONCERT_FILM,
            "https://www.kinolaika.fi/ohjelmisto/": listing(
                laika_row("hetki", "Hetki ennen valoa"),
                laika_row("arppa", "Arppa", date="30/10/2026 19:00", sold=True)),
            "https://www.kinolaika.fi/film/hetki/": laika_film(),
            "https://www.kinolaika.fi/film/arppa/": LIVE_ACT,
        }
        pages.update(over)
        return pages

    def test_a_full_run_publishes_both_venues_and_omits_the_live_act(self):
        self.serve(self.both())
        code, log = self.main()
        self.assertEqual(code, 0, log)
        kilta = json.loads((run.OUT / "area-kilta-turku.json").read_text())["shows"]
        laika = json.loads((run.OUT / "area-laika-karkkila.json").read_text())["shows"]
        self.assertEqual(len(kilta), 2)
        self.assertEqual([s["title"] for s in laika], ["Hetki ennen valoa"])
        self.assertIn("omitted 1 unresolved film(s) over 1 screening(s)", log)
        self.assertIn("unresolved: Arppa", log)
        self.assertIn("0 failures", log)
        for pid in ("kinokilta", "kinolaika"):
            v = json.loads((run.OUT / f"venues-{pid}.json").read_text())
            self.assertEqual((v["status"], v["stale"], v["pending"]), ("ok", [], []))

    def test_one_film_page_is_read_per_distinct_film(self):
        self.serve(self.both())
        self.assertEqual(self.main()[0], 0)
        films = [c for c in self.calls if "/film/" in c]
        self.assertEqual(sorted(films), sorted(set(films)))
        self.assertEqual(len(films), 4)

    def test_a_listing_with_no_screening_keeps_the_previous_file_and_stays_green(self):
        prev = {"generated": "2026-09-01T00:00:00+00:00", "dates": ["2026-09-01"],
                "horizon": "2026-09-01",
                "shows": [{"title": "Old", "start": "2026-09-01T12:00:00+03:00"}]}
        (run.OUT / "area-laika-karkkila.json").write_text(json.dumps(prev))
        self.serve(self.both(**{"https://www.kinolaika.fi/ohjelmisto/": listing()}))
        code, log = self.main()
        self.assertEqual(code, 0, log)
        self.assertEqual(json.loads((run.OUT / "area-laika-karkkila.json").read_text()),
                         prev)
        self.assertIn("no programme published", log)
        self.assertTrue((run.OUT / "area-kilta-turku.json").exists())

    def test_a_listing_whose_rows_all_fail_to_classify_fails_the_site(self):
        """Blocks present and nothing published is a template or classification failure,
        not a cinema with nothing on."""
        self.serve(self.both(**{
            "https://www.kinolaika.fi/ohjelmisto/": listing(
                laika_row("arppa", "Arppa"),
                laika_row("arppa", "Arppa", date="31/10/2026 19:00"))}))
        code, log = self.main()
        self.assertEqual(code, 1)
        self.assertIn("FAILED", log)
        self.assertFalse((run.OUT / "area-laika-karkkila.json").exists())
        self.assertTrue((run.OUT / "area-kilta-turku.json").exists())

    def test_a_film_page_that_cannot_be_read_fails_that_site_only(self):
        """The page carries the classification, so a missing one would omit its
        screenings silently. A second film publishes from the same listing, so swallowing
        the failure would exit 0 with a partial schedule rather than fail: that is what
        this asserts against, not merely a non-zero exit."""
        self.serve(self.both(**{
            "https://www.kinolaika.fi/ohjelmisto/": listing(
                laika_row("hetki", "Hetki ennen valoa"),
                laika_row("oasis", "Oasis", date="18/09/2026 20:00")),
            "https://www.kinolaika.fi/film/hetki/": RuntimeError("HTTP Error 503"),
            "https://www.kinolaika.fi/film/oasis/": CONCERT_FILM}))
        code, log = self.main()
        self.assertEqual(code, 1)
        self.assertIn("FAILED", log)
        self.assertIn("classification", log)
        self.assertFalse((run.OUT / "area-laika-karkkila.json").exists())
        self.assertTrue((run.OUT / "area-kilta-turku.json").exists())

    def test_a_refused_listing_fails_that_site_only(self):
        self.serve(self.both(**{
            "https://www.kinokilta.fi/naytokset/": RuntimeError("HTTP Error 403")}))
        code, log = self.main()
        self.assertEqual(code, 1)
        self.assertIn("FAILED", log)
        self.assertFalse((run.OUT / "area-kilta-turku.json").exists())
        self.assertTrue((run.OUT / "area-laika-karkkila.json").exists())

    def test_a_listing_over_the_film_page_budget_is_refused(self):
        rows = [laika_row(f"f{n}", f"Film {n}", date=f"{(n % 28) + 1:02d}/09/2026 14:00")
                for n in range(common.PAGE_BUDGET + 2)]
        self.serve(self.both(**{
            "https://www.kinolaika.fi/ohjelmisto/": listing(*rows)}))
        code, log = self.main()
        self.assertEqual(code, 1)
        self.assertIn("over the", log)
        self.assertIn("partial schedule", log)
        # Refused before the loop, not trimmed inside it: a cap would fetch the first
        # 120 pages and publish what they classified.
        self.assertEqual([c for c in self.calls if "kinolaika.fi/film/" in c], [])
        self.assertFalse((run.OUT / "area-laika-karkkila.json").exists())


# ---------------------------------------------------------------- registry and sites

class RegistryTest(unittest.TestCase):
    def test_the_two_registry_entries(self):
        for pid, label, host, accent, venue, city in (
                ("kinokilta", "Kino Kilta", "kinokilta.fi", "#1D6F8B", "kilta-turku",
                 "Turku"),
                ("kinolaika", "Kino Laika", "kinolaika.fi", "#9A3412", "laika-karkkila",
                 "Karkkila")):
            with self.subTest(provider=pid):
                p = registry.by_id(pid)
                self.assertEqual((p["label"], p["host"], p["accent"], p["book"],
                                  p["module"], p["where"]),
                                 (label, host, accent, "buy", "kinola", "cloud"))
                self.assertEqual(sum(1 for q in registry.PROVIDERS
                                     if q["accent"] == p["accent"]), 1)
                site = next(s for s in K.SITES if s["provider"] == pid)
                v = site["venues"][0]
                self.assertEqual((v["id"], v["name"], v["short"], v["city"]),
                                 (venue, label, label, city))

    def test_konepaja_has_no_entry_until_it_lists_a_screening(self):
        """Re-read 2026-09-15: its event list still says "Ei tulevia tapahtumia."."""
        self.assertIsNone(registry.by_id("kinokonepaja"))
        self.assertNotIn("konepaja", {s["provider"] for s in K.SITES})
        self.assertNotIn("kinokonepaja.fi", {s["base"] for s in K.SITES})

    def test_each_site_names_the_host_it_reads_and_they_are_paced_apart(self):
        self.assertEqual([s["base"] for s in K.SITES],
                         ["https://www.kinokilta.fi", "https://www.kinolaika.fi"])
        self.assertEqual(len(run.host_groups(K.SITES)), 2)

    def test_orion_still_reads_the_third_template_and_is_untouched(self):
        """One platform, two modules. Orion's own table is not this module's business."""
        import orion
        self.assertEqual(registry.by_id("orion")["module"], "orion")
        self.assertEqual(orion.parse(listing(kilta_row("a", "A"))), [])

    def test_both_providers_share_the_one_module(self):
        mods = {registry.by_id(p)["module"] for p in ("kinokilta", "kinolaika")}
        self.assertEqual(mods, {"kinola"})


if __name__ == "__main__":
    unittest.main()
