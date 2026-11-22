"""Published links only to hosts the registry or the site entry declares.

A compromised cinema site could publish a ticket link to any https host, and this site
would serve it to readers. run.py blanks such a link and logs it, the row stays, and the
committed data is held to the same rule so a new provider cannot ship one unnoticed.
"""
import contextlib
import glob
import importlib
import io
import json
import pathlib
import re
import unittest

import _ctx                                                # noqa: F401
import check_runs
import common
import fetch_data
import registry
import run
import test_finnkino_partial as tfp
import test_check_runs
from test_run_partial import RunSiteHarness, show

REPO = pathlib.Path(__file__).resolve().parent.parent

HELIOS_SITE = {"provider": "helios", "base": "https://api.hel.fi"}


class LinkAllowedTest(unittest.TestCase):
    def setUp(self):
        self.domains = common.link_domains("helios", HELIOS_SITE)

    def test_the_registry_host_the_site_hosts_and_links_are_declared(self):
        self.assertEqual(self.domains, {"hel.fi", "api.hel.fi", "lippu.fi", "kanneltalo.fi"})

    def test_declared_hosts_and_their_subdomains_pass(self):
        for url in ("https://hel.fi/x", "https://www.hel.fi/tapahtumat/1",
                    "https://www.lippu.fi/event/1", "https://lippu.fi/event/1",
                    "https://tickets.kanneltalo.fi/a?b=1", "HTTPS://WWW.LIPPU.FI/x"):
            self.assertTrue(common.link_allowed(url, self.domains), url)

    def test_lookalikes_and_undeclared_vendors_fail(self):
        for url in ("https://hel.fi.evil.example/x", "https://evilhel.fi/x",
                    "https://lippu.fi.evil.example/x", "https://evillippu.fi/x",
                    "https://helios.fi.evil.example/x", "https://evilhelios.fi/x",
                    "https://hel.fi" + "@" + "evil.example/x", "https://tickets.vendor.example/x",
                    "https://", "not a url"):
            self.assertFalse(common.link_allowed(url, self.domains), url)

    def test_an_unknown_provider_with_no_site_declares_nothing(self):
        self.assertEqual(common.link_domains("no-such-provider"), set())

    def test_reads_and_site_are_declared_with_www_dropped(self):
        site = {"base": "https://biosalo.fi", "site": "https://www.biostara.fi",
                "reads": ("tickets.example.fi",)}
        self.assertEqual(common.link_domains("biostara", site),
                         {"biostara.fi", "biosalo.fi", "tickets.example.fi"})


class DropTest(unittest.TestCase):
    def test_two_undeclared_rows_are_blanked_and_counted_and_the_others_kept(self):
        per_venue = {
            "a": [{"url": "https://www.lippu.fi/1", "tr": ""},
                  {"url": "https://evil.example/1", "tr": "https://www.youtube.com/watch?v=x"}],
            "b": [{"url": "https://evil.example/2", "tr": "https://evil.example/t"},
                  {"url": "", "tr": ""}],
        }
        dropped = common.drop_undeclared_links(per_venue, common.link_domains("helios", HELIOS_SITE))
        self.assertEqual(dropped, {"evil.example": 3})
        self.assertEqual([s["url"] for s in per_venue["a"] + per_venue["b"]],
                         ["https://www.lippu.fi/1", "", "", ""])
        self.assertEqual(per_venue["a"][1]["tr"], "https://www.youtube.com/watch?v=x")
        self.assertEqual(per_venue["b"][0]["tr"], "")

    def test_the_log_line_is_the_one_check_runs_lists(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            common.report_dropped_links("helios", {"evil.example": 2, "b.example": 1})
        self.assertEqual(check_runs.dropped_links(err.getvalue()),
                         {("helios", "b.example"): 1, ("helios", "evil.example"): 2})


class FakeHelios:
    __name__ = "helios"

    def __init__(self, per_venue):
        self.per_venue = per_venue

    def fetch_site(self, site):
        return {vid: [dict(s, venue=vid, provider="helios") for s in shows]
                for vid, shows in self.per_venue.items()}


class PublishTest(RunSiteHarness):
    SITE = {"provider": "helios", "base": "https://api.hel.fi", "venues": [
        {"id": "hx-a", "name": "Alpha", "short": "Alpha", "city": "Helsinki"},
        {"id": "hx-b", "name": "Beta", "short": "Beta", "city": "Helsinki"}]}

    @staticmethod
    def row(title, url):
        return dict(show(title, "2026-08-30T18:00:00+03:00"), url=url)

    def test_an_undeclared_link_is_published_blank_and_named_in_the_log(self):
        mod = FakeHelios({
            "hx-a": [self.row("A", "https://www.lippu.fi/a"), self.row("B", "https://evil.example/b")],
            "hx-b": [self.row("C", "https://evilhel.fi/c")],
        })
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            live, total, *_ = run.run_site(mod, self.SITE, "2026-08-30T12:00:00+00:00")
        self.assertEqual((live, total), (2, 3), "dropping a link must not drop the row")
        urls = {s["title"]: s["url"] for v in ("hx-a", "hx-b") for s in self.area(v)["shows"]}
        self.assertEqual(urls, {"A": "https://www.lippu.fi/a", "B": "", "C": ""})
        self.assertEqual(check_runs.dropped_links(err.getvalue()),
                         {("helios", "evil.example"): 1, ("helios", "evilhel.fi"): 1})


class CheckRunsReportTest(unittest.TestCase):
    setUp = test_check_runs.FailingSiteHistoryTest.setUp
    commit = test_check_runs.FailingSiteHistoryTest.commit

    def test_a_dropped_link_is_listed_and_the_log_stays_green(self):
        self.commit("[helios] 3 showtimes\nexit=0\n")
        self.commit("[helios] undeclared link host evil.example: 2 link(s) dropped\n"
                    "[helios] 3 showtimes\nexit=0\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = check_runs.main(["--dir", str(self.logs)])
        self.assertEqual(code, 0)
        self.assertIn("[check] undeclared link hosts: 1 in 1 log(s), 1 new", out.getvalue())
        self.assertIn("    run-mod.log: [helios] evil.example: 2 link(s): new", out.getvalue())


class FinnkinoTrailerTest(unittest.TestCase):
    """The OCAPI trailer link is the one provider URL fetch_data publishes as written."""
    setUp = tfp.SevenDayPublishTest.setUp
    restore_env = tfp.SevenDayPublishTest.restore_env
    stub = tfp.SevenDayPublishTest.stub

    def test_an_undeclared_trailer_host_is_blanked_and_logged(self):
        self.stub()
        orig = tfp.showtimes_for
        trailers = {10: "https://film-cdn.moviexchange.com/t/a.mp4",
                    11: "https://moviexchange.com.evil.example/b.mp4"}

        def with_trailers(date):
            doc = orig(date)
            for f in doc["relatedData"]["films"]:
                f["trailers"] = [{"uri": trailers[f["id"]]}]
            return doc
        tfp.showtimes_for = with_trailers
        self.addCleanup(lambda: setattr(tfp, "showtimes_for", orig))
        self.assertEqual(fetch_data.main(), 0, self.err.getvalue())
        films = json.loads((self.root / "data" / "films.json").read_text(encoding="utf-8"))
        self.assertEqual({k: f["tr"] for k, f in films["films"].items()},
                         {"10": trailers[10], "11": ""})
        self.assertEqual(check_runs.dropped_links(self.err.getvalue()),
                         {("finnkino", "moviexchange.com.evil.example"): 1})


HOST_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")


def committed_strays(data=REPO / "data"):
    """Every committed link no declaration covers. -> [(provider, field, url)]."""
    sites = {}
    for p in registry.PROVIDERS:
        if p["module"]:
            mod = importlib.import_module(p["module"])
            for s in mod.SITES:
                for v in s["venues"]:
                    sites[(s.get("provider") or mod.__name__, v["id"])] = s
    out = []
    for f in sorted(glob.glob(str(data / "area-*.json"))):
        for s in json.loads(pathlib.Path(f).read_text(encoding="utf-8"))["shows"]:
            pid = s.get("provider") or "finnkino"
            domains = common.link_domains(pid, sites.get((pid, s.get("venue"))))
            for field, extra in common.LINK_FIELDS.items():
                if s.get(field) and not common.link_allowed(s[field], domains | set(extra)):
                    out.append((pid, field, s[field]))
    films = json.loads((data / "films.json").read_text(encoding="utf-8"))["films"]
    domains = common.link_domains("finnkino") | set(common.LINK_FIELDS["tr"])
    for f in films.values():
        if isinstance(f, dict) and f.get("tr") and not common.link_allowed(f["tr"], domains):
            out.append(("finnkino", "films.json tr", f["tr"]))
    return out


class RegistryTest(unittest.TestCase):
    def test_links_are_bare_lowercase_hostnames(self):
        for p in registry.PROVIDERS:
            links = p.get("links", ())
            self.assertIsInstance(links, tuple, p["id"])
            for h in links:
                self.assertTrue(HOST_RE.fullmatch(h), f"{p['id']}: {h!r} is not a bare hostname")
                self.assertFalse(h.startswith("www."), f"{p['id']}: declare {h[4:]!r}")

    def test_links_stay_out_of_the_frontend(self):
        self.assertNotIn("links", registry.FRONTEND_KEYS + registry.FRONTEND_OPTIONAL)

    def test_every_committed_link_is_on_a_declared_host(self):
        """Fails when a provider publishes a link host nobody declared. Declare it in the
        registry's `links` if it is the cinema's own ticket shop, or find out why not."""
        self.assertEqual(committed_strays(), [])


if __name__ == "__main__":
    unittest.main()
