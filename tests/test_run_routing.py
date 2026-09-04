"""run.py routes individual sites, not whole adapter modules.

Routing used to be per module. One site that can only be fetched from an ordinary
connection therefore dragged its entire adapter with it: marking a single eTiketti
provider local would have put all sixteen sites in both halves, with two writers racing
on the same files. The cost was real -- Joutsan Kino parses fine at home, answers a
runner with a Cloudflare 403, and was deleted to keep the cloud run green.

Two properties are load-bearing here and are asserted against the live registry rather
than a fixture, because a fixture cannot go stale in the way that matters:

  * the halves are disjoint -- no provider is fetched by both, so every
    data/venues-{provider}.json has exactly one writer
  * the halves are complete -- every site belongs to one, so routing cannot silently
    drop a cinema the way the old module-level scheme did
"""
import importlib
import os
import unittest

import _ctx                                                # noqa: F401
import registry
import run


class FakeMod:
    SITES = [
        {"provider": "kotkanleffat", "venues": []},        # cloud in the registry
        {"provider": "joutsankino", "venues": []},         # local in the registry
        {"provider": "nosuchprovider", "venues": []},      # no registry entry at all
    ]


def ids(sites):
    return [s["provider"] for s in sites]


class SitesForTest(unittest.TestCase):
    def test_cloud_excludes_a_local_site(self):
        self.assertNotIn("joutsankino", ids(run.sites_for(FakeMod, "cloud")))
        self.assertIn("kotkanleffat", ids(run.sites_for(FakeMod, "cloud")))

    def test_local_takes_the_local_site_and_not_the_cloud_one(self):
        got = ids(run.sites_for(FakeMod, "local"))
        self.assertIn("joutsankino", got)
        self.assertNotIn("kotkanleffat", got)

    def test_all_keeps_every_site(self):
        self.assertEqual(len(run.sites_for(FakeMod, "all")), 3)

    def test_an_unregistered_provider_is_kept_not_dropped(self):
        """Dropping it would turn a misconfiguration into a cinema that silently stops
        being fetched. test_registry_sites.py is what reports it."""
        for half in ("cloud", "local"):
            with self.subTest(half=half):
                self.assertIn("nosuchprovider", ids(run.sites_for(FakeMod, half)))


class HalfOfTest(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("GITHUB_ACTIONS", None)

    def tearDown(self):
        if self._saved is not None:
            os.environ["GITHUB_ACTIONS"] = self._saved

    def test_actions_means_cloud_without_the_workflow_saying_so(self):
        """The cloud workflow calls run.py per module with a bare name. If the half had
        to be passed, this could not have been fixed without editing that file."""
        os.environ["GITHUB_ACTIONS"] = "true"
        self.assertEqual(run.half_of(["etiketti"]), "cloud")

    def test_off_actions_a_bare_module_still_fetches_everything(self):
        """`run.py etiketti` on a laptop is how an adapter gets exercised. Defaulting to
        "local" would quietly fetch one site of sixteen and look like a broken parser."""
        self.assertEqual(run.half_of(["etiketti"]), "all")

    def test_where_selects_the_half_as_well_as_the_modules(self):
        self.assertEqual(run.half_of(["--where", "local"]), "local")

    def test_an_explicit_half_wins_over_the_environment(self):
        os.environ["GITHUB_ACTIONS"] = "true"
        self.assertEqual(run.half_of(["etiketti", "--half", "local"]), "local")


class ArgvTest(unittest.TestCase):
    """A flag's value is not a module name. It was: `run.py etiketti --half local` tried
    to `import local`, logged "[local] unusable", counted a failure and printed the word
    in the run summary -- caught by running it, not by reading it."""

    def test_a_flag_value_is_not_taken_as_a_module(self):
        self.assertEqual(run.module_names(["etiketti", "--half", "local"]), ["etiketti"])

    def test_several_modules_still_come_through(self):
        self.assertEqual(run.module_names(["etiketti", "nexxo"]), ["etiketti", "nexxo"])


class LiveRegistryTest(unittest.TestCase):
    def test_the_halves_are_disjoint_and_complete(self):
        for name in registry.modules():
            mod = importlib.import_module(name)
            cloud, local = ids(run.sites_for(mod, "cloud")), ids(run.sites_for(mod, "local"))
            with self.subTest(module=name):
                self.assertEqual(set(cloud) & set(local), set(),
                                 "a provider fetched by both halves has two writers "
                                 "on its venues file")
                self.assertEqual(sorted(cloud + local), sorted(ids(mod.SITES)),
                                 "a site in neither half is never fetched")

    def test_joutsan_kino_is_routed_local_and_shares_its_module(self):
        """The case this exists for: a local site inside an otherwise cloud module."""
        p = registry.by_id("joutsankino")
        self.assertIsNotNone(p)
        self.assertEqual(p["where"], "local")
        self.assertEqual(p["module"], "etiketti")
        etiketti = importlib.import_module("etiketti")
        self.assertIn("joutsankino", ids(run.sites_for(etiketti, "local")))
        self.assertGreater(len(run.sites_for(etiketti, "cloud")), 1)

    def test_the_local_etiketti_sites_are_exactly_savon_kinot_and_joutsan_kino(self):
        """Savon Kinot joined the local half on 2026-09-04: savonkinot.fi sits behind
        Cloudflare, which answers a datacenter address 403 at the edge while an ordinary
        connection gets 200. The list is explicit so a site drifting between halves is a
        failing test and a decision, never a side effect of a registry edit."""
        etiketti = importlib.import_module("etiketti")
        self.assertEqual(ids(run.sites_for(etiketti, "local")), ["savonkinot", "joutsankino"])
        self.assertEqual(registry.by_id("savonkinot")["where"], "local")
        self.assertNotIn("savonkinot", ids(run.sites_for(etiketti, "cloud")))


if __name__ == "__main__":
    unittest.main()
