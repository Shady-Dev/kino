"""The cinema ghost beside the wordmark, in a real engine (2026-11-02).

The ghost is its own button and shares one handler with #themeToggle: a press on either
toggles the theme once, stores it under `kino-theme` as before, and plays the ghost's
reaction, after which the ambient loop starts again from its first frame. The loop is a
CSS animation stepping through ghost.png, so these tests seek it with the Web Animations
API rather than wait on it. Served data is the fixture the other browser tests use.
"""
import shutil
import unittest

from playwright.sync_api import expect

import test_client_browser as base
import test_pages_layout as layout

# Each ambient frame's duration from the supplied timing file, in sheet order.
LOOP_MS = [1100, 350, 450, 180, 330, 180, 340, 330, 800, 210, 300, 240, 420, 1400, 1100, 750]
REACT_MS = [180, 350, 115, 220, 115, 220]

# The frame index the ghost is drawing, read off its background offset.
FRAME = """() => { const g = document.querySelector('#ghost'), s = getComputedStyle(g);
  return Math.round(-parseFloat(s.backgroundPositionX) / parseFloat(s.getPropertyValue('--gw'))); }"""
GHOST_ANIMS = """() => document.querySelector('#ghost').getAnimations().map(a => a.animationName)"""
SEEK = """([name, t]) => { const a = document.querySelector('#ghost').getAnimations()
  .find(a => a.animationName === name); a.pause(); a.currentTime = t; }"""
# Counts writes of data-theme from here on, so one press is shown to toggle exactly once.
COUNT_TOGGLES = """() => { window.__toggles = 0; new MutationObserver(m => window.__toggles += m.length)
  .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] }); }"""


class Ghost(base.Browser):

    def theme(self):
        return self.page.evaluate("document.documentElement.getAttribute('data-theme')")

    def stored(self):
        return self.page.evaluate("localStorage.getItem('kino-theme')")

    def setUp(self):
        super().setUp()
        self.ghost = self.page.locator("#ghost")
        expect(self.ghost).to_be_visible()
        self.page.evaluate(COUNT_TOGGLES)

    def test_the_loop_steps_through_the_supplied_frames_on_their_timing(self):
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), ["ghost-loop"])
        timing = self.page.evaluate("""() => { const t = document.querySelector('#ghost')
          .getAnimations()[0].effect.getComputedTiming(); return [t.duration, t.iterations]; }""")
        self.assertEqual(timing, [sum(LOOP_MS), float("inf")])
        start = 0
        for i, ms in enumerate(LOOP_MS):
            for t in (start + 20, start + ms - 20):
                self.page.evaluate(SEEK, ["ghost-loop", t])
                self.assertEqual(self.page.evaluate(FRAME), i, f"at {t} ms")
            start += ms

    def test_the_ghost_toggles_the_theme_once_and_reacts(self):
        self.assertEqual(self.theme(), "light")
        expect(self.ghost).to_have_attribute("aria-label", "Vaihda tummaan teemaan")
        self.ghost.click()
        self.assertEqual((self.theme(), self.stored()), ("dark", "dark"))
        self.assertEqual(self.page.evaluate("window.__toggles"), 1)
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), ["ghost-react"])
        expect(self.ghost).to_have_attribute("aria-label", "Vaihda vaaleaan teemaan")
        start = 0
        for i, ms in enumerate(REACT_MS):
            for t in (start + 10, start + ms - 10):
                self.page.evaluate(SEEK, ["ghost-react", t])
                self.assertEqual(self.page.evaluate(FRAME), 16 + i, f"at {t} ms")
            start += ms
        self.page.evaluate("document.querySelector('#ghost').getAnimations()[0].play()")
        # The reaction ends on its own clock and the loop starts over from its idle frame.
        expect(self.ghost).not_to_have_class("react", timeout=5000)
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), ["ghost-loop"])
        self.ghost.click()
        self.assertEqual((self.theme(), self.stored()), ("light", "light"))
        self.assertEqual(self.page.evaluate("window.__toggles"), 2)

    def test_the_theme_button_plays_the_same_reaction_and_toggles_once(self):
        btn = self.page.locator("#themeToggle")
        before = btn.evaluate("b => b.outerHTML")
        btn.click()
        self.assertEqual((self.theme(), self.stored()), ("dark", "dark"))
        self.assertEqual(self.page.evaluate("window.__toggles"), 1)
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), ["ghost-react"])
        self.assertEqual(btn.evaluate("b => b.outerHTML"), before, "the theme button is unchanged")
        expect(self.ghost).not_to_have_class("react", timeout=5000)
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), ["ghost-loop"])

    def test_rapid_presses_on_both_controls_toggle_once_each_with_one_animation(self):
        for sel in ["#ghost"] * 4 + ["#themeToggle"] * 3:
            self.page.locator(sel).click(delay=0)
        self.assertEqual(self.page.evaluate("window.__toggles"), 7)
        self.assertEqual((self.theme(), self.stored()), ("dark", "dark"))
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), ["ghost-react"])
        expect(self.ghost).not_to_have_class("react", timeout=5000)
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), ["ghost-loop"])

    def test_the_choice_persists_across_a_reload(self):
        self.ghost.click()
        self.page.reload()
        expect(self.page.locator("#ghost")).to_have_attribute("aria-label", "Vaihda vaaleaan teemaan")
        self.assertEqual((self.theme(), self.stored()), ("dark", "dark"))
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), ["ghost-loop"], "a reload plays no reaction")

    def test_enter_and_space_press_it(self):
        self.ghost.focus()
        self.page.keyboard.press("Enter")
        self.assertEqual(self.theme(), "dark")
        self.page.keyboard.press("Space")
        self.assertEqual(self.theme(), "light")
        self.assertEqual(self.page.evaluate("window.__toggles"), 2)

    def test_the_label_follows_the_language(self):
        self.page.locator('#langSeg button[data-lang="sv"]').click()
        expect(self.ghost).to_have_attribute("aria-label", "Byt till mörkt tema")
        self.page.locator('#langSeg button[data-lang="en"]').click()
        self.ghost.click()
        expect(self.ghost).to_have_attribute("aria-label", "Switch to light theme")

    def test_reduced_motion_still_toggles_with_a_still_ghost(self):
        self.page.emulate_media(reduced_motion="reduce")
        self.assertEqual(self.page.evaluate(GHOST_ANIMS), [])
        self.assertEqual(self.page.evaluate(FRAME), 0)
        for sel in ("#ghost", "#themeToggle"):
            self.page.locator(sel).click()
            self.assertEqual(self.page.evaluate(GHOST_ANIMS), [])
            expect(self.ghost).not_to_have_class("react")
            self.assertEqual(self.page.evaluate(FRAME), 0)
        self.assertEqual(self.page.evaluate("window.__toggles"), 2)
        self.assertEqual((self.theme(), self.stored()), ("light", "light"))


class GhostOnAPhone(Ghost):
    viewport = {"width": 375, "height": 812}; touch = True
    size = (40, 28)

    def test_it_reaches_the_tap_floor_and_leaves_the_row_alone(self):
        width = self.viewport["width"]
        box = self.ghost.bounding_box()
        self.assertEqual((box["width"], box["height"]), self.size)
        # 44 x 44 through the transparent extension, which ends 2 px past the picture's
        # right edge and covers the wordmark when the picture is narrower.
        right = box["x"] + box["width"] + 2
        left, cy = right - 44, box["y"] + box["height"] / 2
        at = "([x, y]) => document.elementFromPoint(x, y).id"
        for x, y in ((left + .5, cy), (right - .5, cy), (right - 22, cy - 21.5), (right - 22, cy + 21.5)):
            self.assertEqual(self.page.evaluate(at, [x, y]), "ghost", (x, y))
        lang = self.page.locator("#langSeg button").first.bounding_box()
        self.assertGreater(lang["x"], right, "the language segment keeps its own hit area")
        self.assertEqual(self.page.locator("header .bar").bounding_box()["height"], 66)
        self.assertEqual(self.page.evaluate("document.documentElement.scrollWidth"), width)
        theme = self.page.locator("#themeToggle").bounding_box()
        self.assertLessEqual(theme["x"] + theme["width"], width - 14, "inside the bar's padding")


class GhostBetweenTheBands(GhostOnAPhone):
    """361 to 370 px: the larger wordmark leaves room for a 30 px ghost."""
    viewport = {"width": 365, "height": 800}
    size = (30, 21)


class GhostOnANarrowPhone(GhostOnAPhone):
    viewport = {"width": 320, "height": 640}
    size = (20, 14)


class GhostOnEveryPage(unittest.TestCase):
    """The ghost on every other page that shows the wordmark: the generated city and
    theatre pages in each language, /status/ and /tietosuoja/. One build of the pages
    fixture, with the hand-written pages and the sprite copied beside it."""
    PAGES = [f"/teatteri/{layout.SLUG}/", "/kaupunki/testila/", f"/en/theatre/{layout.SLUG}/",
             "/sv/kaupunki/testila/", "/status/", "/tietosuoja/"]
    # Where each page's own sizes apply, and the bands where it leaves the ghost out rather
    # than add a row to the header.
    SIZES = {320: (20, 14), 375: (40, 28), 402: (40, 28), 1200: (50, 35)}
    HIDDEN = [("/status/?lang=fi", 450), ("/status/?lang=sv", 470), ("/status/?lang=en", 440),
              ("/tietosuoja/?lang=sv", 340)]

    @classmethod
    def setUpClass(cls):
        layout.PagesLayoutTest.setUpClass.__func__(cls)
        for f in ("ghost.png", "pageview.js", "data/venuelists-cloud.json",
                  "data/venuelists-local.json"):
            shutil.copy(layout.ROOT / f, cls.root / f)
        for d in ("status", "tietosuoja"):
            shutil.copytree(layout.ROOT / d, cls.root / d)

    @classmethod
    def tearDownClass(cls):
        layout.PagesLayoutTest.tearDownClass.__func__(cls)

    def open(self, path, width=1200, reduced=False):
        ctx = self.browser.new_context(viewport={"width": width, "height": 900},
                                       reduced_motion="reduce" if reduced else "no-preference",
                                       timezone_id="Europe/Helsinki", locale="fi-FI",
                                       service_workers="block")
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("response", lambda r: r.status >= 400 and errors.append(r.url))
        page.goto(self.origin + path)
        page.wait_for_function("document.fonts.ready.then(()=>true)")
        expect(page.locator("#ghost")).to_be_visible()
        page.evaluate(COUNT_TOGGLES)
        self.addCleanup(lambda: self.assertEqual(errors, [], path))
        return page

    def test_it_draws_the_sprite_and_loops(self):
        for path in self.PAGES:
            with self.subTest(path):
                page = self.open(path)
                self.assertEqual(page.evaluate(GHOST_ANIMS), ["ghost-loop"])
                self.assertEqual(page.evaluate("""() => document.querySelector('#ghost')
                  .getAnimations()[0].effect.getComputedTiming().duration"""), sum(LOOP_MS))
                self.assertEqual(page.evaluate("""async () => { const u = getComputedStyle(
                  document.querySelector('#ghost')).backgroundImage.slice(5, -2);
                  const i = new Image(); i.src = u; await i.decode(); return i.naturalWidth; }"""),
                  7040)
                start = 0
                for i, ms in enumerate(LOOP_MS):
                    page.evaluate(SEEK, ["ghost-loop", start + ms - 20])
                    self.assertEqual(page.evaluate(FRAME), i)
                    start += ms

    def test_either_control_toggles_once_and_the_ghost_reacts(self):
        for path in self.PAGES:
            with self.subTest(path):
                page = self.open(path)
                ghost = page.locator("#ghost")
                first = page.evaluate("document.documentElement.getAttribute('data-theme')")
                label = ghost.get_attribute("aria-label")
                ghost.click()
                theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
                self.assertNotEqual(theme, first)
                self.assertEqual(page.evaluate("localStorage.getItem('kino-theme')"), theme)
                self.assertEqual(page.evaluate("window.__toggles"), 1)
                self.assertEqual(page.evaluate(GHOST_ANIMS), ["ghost-react"])
                self.assertNotEqual(ghost.get_attribute("aria-label"), label)
                expect(ghost).not_to_have_class("react", timeout=5000)
                self.assertEqual(page.evaluate(GHOST_ANIMS), ["ghost-loop"])
                page.locator("#themeToggle").click()
                self.assertEqual(page.evaluate("window.__toggles"), 2)
                self.assertEqual(page.evaluate("localStorage.getItem('kino-theme')"), first)
                self.assertEqual(page.evaluate(GHOST_ANIMS), ["ghost-react"])
                self.assertEqual(ghost.get_attribute("aria-label"), label)

    def test_reduced_motion_keeps_a_still_ghost_that_still_toggles(self):
        for path in self.PAGES:
            with self.subTest(path):
                page = self.open(path, reduced=True)
                for sel in ("#ghost", "#themeToggle"):
                    page.locator(sel).click()
                    self.assertEqual(page.evaluate(GHOST_ANIMS), [])
                    expect(page.locator("#ghost")).not_to_have_class("react")
                    self.assertEqual(page.evaluate(FRAME), 0)
                self.assertEqual(page.evaluate("window.__toggles"), 2)

    def test_its_sizes_and_tap_floor_and_the_header_left_alone(self):
        at = "([x, y]) => document.elementFromPoint(x, y).id"
        # The header's height with the ghost and with it taken out, and any sideways scroll.
        probe = """() => { const g = document.querySelector('#ghost'), h = g.parentElement;
          const a = h.getBoundingClientRect().height; g.style.display = 'none';
          const b = h.getBoundingClientRect().height; g.style.display = '';
          return [a, b, document.documentElement.scrollWidth - innerWidth]; }"""
        for path in self.PAGES:
            for width, size in self.SIZES.items():
                with self.subTest(path, width=width):
                    page = self.open(path, width)
                    box = page.locator("#ghost").bounding_box()
                    self.assertEqual((box["width"], box["height"]), size)
                    logo = page.locator("a.logo, a.wordmark").bounding_box()
                    self.assertTrue(4 <= box["x"] - logo["x"] - logo["width"] <= 12,
                                    "beside the wordmark")
                    with_ghost, without, over = page.evaluate(probe)
                    self.assertEqual((with_ghost, over), (without, 0))
                    if width > 560:
                        continue
                    right = box["x"] + box["width"] + 2
                    cy = box["y"] + box["height"] / 2
                    for x, y in ((right - 43.5, cy), (right - .5, cy), (right - 22, cy - 21.5),
                                 (right - 22, cy + 21.5)):
                        self.assertEqual(page.evaluate(at, [x, y]), "ghost", (x, y))

    def test_it_is_left_out_where_it_would_add_a_row(self):
        for path, width in self.HIDDEN:
            with self.subTest(path, width=width):
                ctx = self.browser.new_context(viewport={"width": width, "height": 900},
                                               service_workers="block")
                self.addCleanup(ctx.close)
                page = ctx.new_page()
                page.goto(self.origin + path)
                page.wait_for_function("document.fonts.ready.then(()=>true)")
                expect(page.locator("#ghost")).to_be_hidden()
                page.set_viewport_size({"width": width + 50, "height": 900})
                expect(page.locator("#ghost")).to_be_visible()


if __name__ == "__main__":
    unittest.main()
